# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import discord
from discord.ext import commands
from dismob.rate_limiter import get_rate_limiter
import logging
import os

logger: logging.Logger = None

# --- Logging configuration ---

def setup_logger(
    logger_name: str = "DungeonBot",
    file_level: str = "INFO",
    console_level: str = "INFO"
) -> None:
    """
    Set up and return a logger with the given name and logging levels.
    Levels should be strings like 'INFO', 'DEBUG', etc.
    """
    LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.log"))
    logLevels = logging.getLevelNamesMapping()
    file_logLevel = logLevels.get(file_level.upper(), logging.INFO)
    console_logLevel = logLevels.get(console_level.upper(), logging.INFO)

    global logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(min(file_logLevel, console_logLevel))

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(file_logLevel)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler

    class ColorFormatter(logging.Formatter):
        COLORS = {
            "DEBUG": "\033[36m",    # CYAN
            "INFO": "\033[34m",     # Blue
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
            "CRITICAL": "\033[41m", # Red background
        }
        BOLD = "\033[1m"
        PURPLE = "\033[35m"
        RESET = "\033[0m"
        def format(self, record):
            levelname = record.levelname
            # Pad the level name before applying color codes
            padded_levelname = f"{levelname:<8}"
            color = self.COLORS.get(levelname, "")
            record.levelname = f"{self.BOLD}{color}{padded_levelname}{self.RESET}"

            record.name = f"{self.PURPLE}{record.name}{self.RESET}"

            return super().format(record)

        def formatTime(self, record, datefmt=None):
            asctime = super().formatTime(record, datefmt)
            GRAY = "\033[90m"
            return f"{self.BOLD}{GRAY}{asctime}{self.RESET}"

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_logLevel)
    console_formatter = ColorFormatter(
        "%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)

    # Add handlers if not already present
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

# --- Client message helpers ---

async def client(ctx: commands.Context | discord.Interaction, msg: str, title: str = None, color: discord.Colour = discord.Color.blurple(), delete_after: int = 5):
    e = discord.Embed(title=title, color=color, description=msg)
    if isinstance(ctx, commands.Context):
        e.set_footer(text=f"Commande faites par {ctx.author.display_name}", icon_url=ctx.author.display_avatar)
        return await ctx.send(embed=e, delete_after=delete_after)
    elif isinstance(ctx, discord.Interaction):
        return await safe_respond(ctx, embed=e, ephemeral=True)

async def success(ctx: commands.Context | discord.Interaction, msg: str, delete_after: int = 5):
    info(msg)
    return await client(ctx, f"{msg}", title=":white_check_mark: Success", color=discord.Color.green(), delete_after=delete_after)
    
async def failure(ctx: commands.Context | discord.Interaction, msg: str, delete_after: int = 5):
    error(msg)
    return await client(ctx, f"{msg}", title=":x: Error", color=discord.Color.red(), delete_after=delete_after)

# --- Logging functions ---
def require_logger(func):
    def wrapper(msg: str, *args, **kwargs):
        if logger is None:
            raise RuntimeError("Logger has not been set up. Call setup_logger() first.")
        return func(msg, *args, **kwargs)
    return wrapper

@require_logger
def debug(msg: str) -> None:
    logger.debug(msg)

@require_logger
def info(msg: str) -> None:
    logger.info(msg)

@require_logger
def warning(msg: str) -> None:
    logger.warning(msg)

@require_logger
def error(msg: str) -> None:
    logger.error(msg, stack_info=True, stacklevel=3)

# --- Discord helpers ---

async def safe_send_message(channel: discord.TextChannel, content: str = None, embed: discord.Embed = None):
    """Sends a message to a channel with rate limiting"""
    try:
        result = await get_rate_limiter().safe_send(channel, content, embed=embed)
        info(f"Message sent in {channel.name}")
        return result
    except discord.Forbidden:
        error(f"Bot has not the permission to send messages in {channel.name}")
        return None
    except discord.NotFound:
        error(f"Channel {channel.name} not found")
        return None
    except Exception as e:
        error(f"Error when sending message: {e}")
        return None

async def safe_respond(interaction: discord.Interaction, content: str = None, embed: discord.Embed = None, ephemeral: bool = False):
    """Responds to an interaction with rate limiting"""
    try:
        return await get_rate_limiter().execute_request(
            interaction.response.send_message(content, embed=embed, ephemeral=ephemeral),
            route='POST /interactions/{interaction_id}/{interaction_token}/callback',
            major_params={'interaction_id': interaction.id}
        )
    except discord.InteractionResponded:
        # Use followup if already responded
        try:
            return await get_rate_limiter().execute_request(
                interaction.followup.send(content, embed=embed, ephemeral=ephemeral),
                route='POST /webhooks/{application_id}/{interaction_token}',
                major_params={'application_id': interaction.application_id}
            )
        except Exception as e:
            error(f"Error in the followup: {e}")
    except Exception as e:
        error(f"Error when responding to the interaction: {e}")

async def safe_followup(interaction: discord.Interaction, content: str = None, embed: discord.Embed = None, ephemeral: bool = False):
    """Sends a followup message to an interaction with rate limiting"""
    try:
        return await get_rate_limiter().execute_request(
            interaction.followup.send(content, embed=embed, ephemeral=ephemeral),
            route='POST /webhooks/{application_id}/{interaction_token}',
            major_params={'application_id': interaction.application_id}
        )
    except Exception as e:
        error(f"Error during the followup: {e}")
