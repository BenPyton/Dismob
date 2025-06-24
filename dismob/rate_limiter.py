# modules/rate_limiter.py
import asyncio
import aiohttp
import discord
from discord.ext import commands
import time
import json
import logging
from typing import Dict, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
import hashlib
import os
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

@dataclass
class RateLimitBucket:
    """Represents a Discord rate limit bucket"""
    limit: int = 0
    remaining: int = 0
    reset_after: float = 0.0
    reset_at: float = 0.0
    bucket_hash: Optional[str] = None
    locked_until: float = 0.0
    
    @property
    def is_rate_limited(self) -> bool:
        return time.time() < self.locked_until
    
    @property
    def retry_after(self) -> float:
        return max(0, self.locked_until - time.time())

@dataclass 
class GlobalRateLimit:
    """Global rate limit state"""
    locked_until: float = 0.0
    retry_after: float = 0.0
    
    @property
    def is_rate_limited(self) -> bool:
        return time.time() < self.locked_until

@dataclass
class RequestMetrics:
    """Track request metrics"""
    total_requests: int = 0
    rate_limited_requests: int = 0
    failed_requests: int = 0
    retry_attempts: int = 0
    last_reset: float = field(default_factory=time.time)
    request_times: deque = field(default_factory=lambda: deque(maxlen=100))

class DiscordRateLimiter:
    """
    Advanced Discord rate limiter that properly handles Discord's rate limiting
    with headers, buckets, global limits, and sharding support.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.global_limit = GlobalRateLimit()
        self.metrics = RequestMetrics()
        
        # Route-specific configurations
        self.route_configs = {
            'channels': {'default_limit': 5, 'window': 5.0},
            'guilds': {'default_limit': 5, 'window': 5.0},
            'users': {'default_limit': 5, 'window': 5.0},
            'messages': {'default_limit': 5, 'window': 5.0},
            'reactions': {'default_limit': 1, 'window': 1.0},
        }
        
        # Thread-safe locks
        self._bucket_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._global_lock = asyncio.Lock()
        
        # Shard-specific handling
        self.shard_buckets: Dict[int, Dict[str, RateLimitBucket]] = defaultdict(dict)
        
    def _get_bucket_key(self, route: str, major_params: Dict[str, Any] = None, shard_id: int = None) -> str:
        """Generate bucket key from route and major parameters"""
        if major_params:
            # Sort for consistent hashing
            param_str = ''.join(f"{k}:{v}" for k, v in sorted(major_params.items()))
            route_hash = hashlib.md5(f"{route}:{param_str}".encode()).hexdigest()[:16]
        else:
            route_hash = hashlib.md5(route.encode()).hexdigest()[:16]
            
        if shard_id is not None:
            return f"shard_{shard_id}:{route_hash}"
        return route_hash
    
    def _parse_rate_limit_headers(self, headers: dict) -> Tuple[Optional[RateLimitBucket], bool]:
        """Parse Discord rate limit headers"""
        bucket = None
        is_global = False
        
        if 'x-ratelimit-global' in headers:
            is_global = True
            retry_after = float(headers.get('retry-after', 0))
            self.global_limit.locked_until = time.time() + retry_after
            self.global_limit.retry_after = retry_after
            return bucket, is_global
            
        if 'x-ratelimit-limit' in headers:
            bucket = RateLimitBucket(
                limit=int(headers.get('x-ratelimit-limit', 0)),
                remaining=int(headers.get('x-ratelimit-remaining', 0)),
                reset_after=float(headers.get('x-ratelimit-reset-after', 0)),
                reset_at=float(headers.get('x-ratelimit-reset', 0)),
                bucket_hash=headers.get('x-ratelimit-bucket')
            )
            
            if bucket.remaining == 0:
                bucket.locked_until = time.time() + bucket.reset_after
                
        return bucket, is_global
    
    async def _wait_for_rate_limit(self, bucket_key: str, shard_id: int = None) -> None:
        """Wait for rate limit to expire"""
        bucket = self.buckets.get(bucket_key)
        
        if self.global_limit.is_rate_limited:
            wait_time = self.global_limit.retry_after
            logger.warning(f"Global rate limit hit, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
        if bucket and bucket.is_rate_limited:
            wait_time = bucket.retry_after
            logger.warning(f"Bucket {bucket_key} rate limited, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
    
    async def execute_request(
        self,
        coro: Callable,
        route: str,
        major_params: Dict[str, Any] = None,
        max_retries: int = 5,
        shard_id: int = None,
        **kwargs
    ) -> Any:
        """Execute a Discord API request with proper rate limiting"""
        bucket_key = self._get_bucket_key(route, major_params, shard_id)
        
        for attempt in range(max_retries + 1):
            try:
                # Wait for rate limits
                await self._wait_for_rate_limit(bucket_key, shard_id)
                
                async with self._bucket_locks[bucket_key]:
                    start_time = time.time()
                    self.metrics.total_requests += 1
                    
                    try:
                        if attempt > 0:
                            self.metrics.retry_attempts += 1
                            
                        result = await coro
                        
                        # Record successful request time
                        request_time = time.time() - start_time
                        self.metrics.request_times.append(request_time)
                        
                        return result
                        
                    except discord.HTTPException as e:
                        request_time = time.time() - start_time
                        self.metrics.request_times.append(request_time)
                        
                        if e.status == 429:  # Rate limited
                            self.metrics.rate_limited_requests += 1
                            
                            # Parse rate limit headers from the exception
                            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                                bucket, is_global = self._parse_rate_limit_headers(e.response.headers)
                                
                                if is_global:
                                    retry_after = self.global_limit.retry_after
                                elif bucket:
                                    self.buckets[bucket_key] = bucket
                                    retry_after = bucket.reset_after
                                else:
                                    retry_after = 5.0  # Fallback
                                    
                                if attempt < max_retries:
                                    wait_time = retry_after + (attempt * 0.5)  # Exponential backoff
                                    logger.warning(f"Rate limited on {route}, waiting {wait_time:.2f}s (attempt {attempt + 1})")
                                    await asyncio.sleep(wait_time)
                                    continue
                                    
                        elif e.status == 502 or e.status == 503 or e.status == 504:  # Server errors
                            if attempt < max_retries:
                                wait_time = (2 ** attempt) + (attempt * 0.1)  # Exponential backoff
                                logger.warning(f"Server error {e.status} on {route}, retrying in {wait_time:.2f}s")
                                await asyncio.sleep(wait_time)
                                continue
                                
                        # Re-raise if not retryable or max retries reached
                        self.metrics.failed_requests += 1
                        raise
                        
            except Exception as e:
                if attempt == max_retries:
                    self.metrics.failed_requests += 1
                    logger.error(f"Max retries reached for {route}: {e}")
                    raise
                    
                # Exponential backoff for unexpected errors
                wait_time = (2 ** attempt) + (attempt * 0.1)
                logger.warning(f"Unexpected error on {route}, retrying in {wait_time:.2f}s: {e}")
                await asyncio.sleep(wait_time)
                
        raise RuntimeError(f"Failed to execute request after {max_retries} retries")
    
    async def safe_send(self, channel: discord.TextChannel, *args, **kwargs) -> Optional[discord.Message]:
        """Safe channel.send() with rate limiting"""
        return await self.execute_request(
            channel.send(*args, **kwargs),
            route=f'POST /channels/{channel.id}/messages',
            major_params={'channel_id': channel.id}
        )
    
    async def safe_edit(self, message: discord.Message, *args, **kwargs) -> Optional[discord.Message]:
        """Safe message.edit() with rate limiting"""
        return await self.execute_request(
            message.edit(*args, **kwargs),
            route=f'PATCH /channels/{message.channel.id}/messages/{message.id}',
            major_params={'channel_id': message.channel.id}
        )
    
    async def safe_delete(self, message: discord.Message) -> None:
        """Safe message.delete() with rate limiting"""
        return await self.execute_request(
            message.delete(),
            route=f'DELETE /channels/{message.channel.id}/messages/{message.id}',
            major_params={'channel_id': message.channel.id}
        )
    
    async def safe_channel_create(self, guild: discord.Guild, *args, **kwargs) -> Optional[discord.TextChannel]:
        """Safe guild.create_text_channel() with rate limiting"""
        return await self.execute_request(
            guild.create_text_channel(*args, **kwargs),
            route=f'POST /guilds/{guild.id}/channels',
            major_params={'guild_id': guild.id}
        )
    
    async def safe_channel_delete(self, channel: Union[discord.TextChannel, discord.VoiceChannel]) -> None:
        """Safe channel.delete() with rate limiting"""
        return await self.execute_request(
            channel.delete(),
            route=f'DELETE /channels/{channel.id}',
            major_params={'channel_id': channel.id}
        )
    
    async def safe_channel_edit(self, channel: Union[discord.TextChannel, discord.VoiceChannel], *args, **kwargs) -> Optional[Union[discord.TextChannel, discord.VoiceChannel]]:
        """Safe channel.edit() with rate limiting"""
        return await self.execute_request(
            channel.edit(*args, **kwargs),
            route=f'PATCH /channels/{channel.id}',
            major_params={'channel_id': channel.id}
        )
    
    async def safe_add_reaction(self, message: discord.Message, emoji: Union[str, discord.Emoji]) -> None:
        """Safe message.add_reaction() with rate limiting"""
        return await self.execute_request(
            message.add_reaction(emoji),
            route=f'PUT /channels/{message.channel.id}/messages/{message.id}/reactions',
            major_params={'channel_id': message.channel.id}
        )
    
    async def safe_member_edit(self, member: discord.Member, *args, **kwargs) -> None:
        """Safe member.edit() with rate limiting"""
        return await self.execute_request(
            member.edit(*args, **kwargs),
            route=f'PATCH /guilds/{member.guild.id}/members/{member.id}',
            major_params={'guild_id': member.guild.id}
        )
    
    async def safe_ban(self, guild: discord.Guild, user: Union[discord.User, discord.Member], *args, **kwargs) -> None:
        """Safe guild.ban() with rate limiting"""
        return await self.execute_request(
            guild.ban(user, *args, **kwargs),
            route=f'PUT /guilds/{guild.id}/bans/{user.id}',
            major_params={'guild_id': guild.id}
        )
    
    async def safe_unban(self, guild: discord.Guild, user: discord.User) -> None:
        """Safe guild.unban() with rate limiting"""
        return await self.execute_request(
            guild.unban(user),
            route=f'DELETE /guilds/{guild.id}/bans/{user.id}',
            major_params={'guild_id': guild.id}
        )
    
    async def safe_kick(self, member: discord.Member, *args, **kwargs) -> None:
        """Safe member.kick() with rate limiting"""
        return await self.execute_request(
            member.kick(*args, **kwargs),
            route=f'DELETE /guilds/{member.guild.id}/members/{member.id}',
            major_params={'guild_id': member.guild.id}
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        current_time = time.time()
        uptime = current_time - self.metrics.last_reset
        
        avg_request_time = 0
        if self.metrics.request_times:
            avg_request_time = sum(self.metrics.request_times) / len(self.metrics.request_times)
        
        rate_limit_percentage = 0
        if self.metrics.total_requests > 0:
            rate_limit_percentage = (self.metrics.rate_limited_requests / self.metrics.total_requests) * 100
        
        return {
            'total_requests': self.metrics.total_requests,
            'rate_limited_requests': self.metrics.rate_limited_requests,
            'failed_requests': self.metrics.failed_requests,
            'retry_attempts': self.metrics.retry_attempts,
            'rate_limit_percentage': round(rate_limit_percentage, 2),
            'average_request_time': round(avg_request_time, 3),
            'uptime_seconds': round(uptime, 2),
            'requests_per_minute': round((self.metrics.total_requests / uptime) * 60, 2) if uptime > 0 else 0,
            'active_buckets': len(self.buckets),
            'global_rate_limited': self.global_limit.is_rate_limited
        }
    
    def reset_metrics(self):
        """Reset metrics"""
        self.metrics = RequestMetrics()
    
    async def cleanup_expired_buckets(self):
        """Clean up expired rate limit buckets"""
        current_time = time.time()
        expired_buckets = [
            key for key, bucket in self.buckets.items()
            if not bucket.is_rate_limited and (current_time - bucket.reset_at) > 300  # 5 minutes
        ]
        
        for key in expired_buckets:
            del self.buckets[key]
            if key in self._bucket_locks:
                del self._bucket_locks[key]
        
        logger.debug(f"Cleaned up {len(expired_buckets)} expired buckets")

# Global rate limiter instance
_global_rate_limiter = None

def get_rate_limiter() -> DiscordRateLimiter:
    """Get the global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = DiscordRateLimiter()
    return _global_rate_limiter

def set_rate_limiter(rate_limiter: DiscordRateLimiter):
    """Set a custom rate limiter instance"""
    global _global_rate_limiter
    _global_rate_limiter = rate_limiter

# Convenience functions for easy integration
async def safe_api_call(coro, route: str = None, major_params: Dict[str, Any] = None, **kwargs):
    """
    Convenience function for backward compatibility and easy integration
    
    Usage:
    await safe_api_call(channel.send("Hello"), route="POST /channels/{channel_id}/messages")
    """
    limiter = get_rate_limiter()
    
    if route:
        return await limiter.execute_request(coro, route, major_params, **kwargs)
    else:
        # Fallback to simple execution with basic retry logic
        return await limiter.execute_request(coro, "unknown", **kwargs)

# Decorators for easy integration
def rate_limited(route: str = None, major_params: Dict[str, Any] = None):
    """Decorator to add rate limiting to async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            coro = func(*args, **kwargs)
            return await safe_api_call(coro, route, major_params)
        return wrapper
    return decorator

class RateLimitContext:
    """Context manager for rate limiting"""
    def __init__(self, route: str, major_params: Dict[str, Any] = None):
        self.route = route
        self.major_params = major_params
        self.limiter = get_rate_limiter()
    
    async def __aenter__(self):
        bucket_key = self.limiter._get_bucket_key(self.route, self.major_params)
        await self.limiter._wait_for_rate_limit(bucket_key)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def execute(self, coro):
        """Execute a coroutine within the rate limit context"""
        return await self.limiter.execute_request(coro, self.route, self.major_params)

class RateLimiterCog(commands.Cog):
    """Cog for rate limiter management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rate_limiter = get_rate_limiter()
    
    @commands.command(name='rate_stats')
    @commands.has_permissions(administrator=True)
    async def rate_stats(self, ctx):
        """Show rate limiter statistics"""
        try:
            metrics = self.rate_limiter.get_metrics()
            embed = discord.Embed(
                title="📊 Statistiques Rate Limiter",
                color=discord.Color.blue()
            )
            embed.add_field(name="Requêtes totales", value=metrics['total_requests'], inline=True)
            embed.add_field(name="Rate limited", value=f"{metrics['rate_limited_requests']} ({metrics['rate_limit_percentage']}%)", inline=True)
            embed.add_field(name="Échecs", value=metrics['failed_requests'], inline=True)
            embed.add_field(name="Tentatives retry", value=metrics['retry_attempts'], inline=True)
            embed.add_field(name="Req/min moyenne", value=metrics['requests_per_minute'], inline=True)
            embed.add_field(name="Buckets actifs", value=metrics['active_buckets'], inline=True)
            embed.add_field(name="Temps moyen", value=f"{metrics['average_request_time']}s", inline=True)
            embed.add_field(name="Global rate limited", value="✅" if metrics['global_rate_limited'] else "❌", inline=True)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la récupération des stats: {e}")
    
    @commands.command(name='rate_reset')
    @commands.has_permissions(administrator=True)
    async def rate_reset(self, ctx):
        """Reset rate limiter metrics"""
        self.rate_limiter.reset_metrics()
        await ctx.send("✅ Métriques du rate limiter réinitialisées")
    
    @commands.command(name='rate_cleanup')
    @commands.has_permissions(administrator=True)
    async def rate_cleanup(self, ctx):
        """Clean up expired rate limit buckets"""
        await self.rate_limiter.cleanup_expired_buckets()
        await ctx.send("✅ Nettoyage des buckets expiré effectué")

async def setup(bot):
    """Setup function required for discord.py extensions"""
    await bot.add_cog(RateLimiterCog(bot))
