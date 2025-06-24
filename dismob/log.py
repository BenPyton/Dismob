# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import discord
from discord.ext import commands
from colorama import Fore, Style
from dismob.rate_limiter import get_rate_limiter
import traceback

###   Send messages to the client   ###

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

###   Print in the standard output   ###

def log(msg: str) -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Style.BRIGHT}{Fore.LIGHTBLACK_EX}{now} {Style.RESET_ALL}{msg}")

def info(msg: str) -> None:
    log(f"{Style.BRIGHT}{Fore.BLUE}INFO     {Style.RESET_ALL}{msg}")

def warning(msg: str) -> None:
    log(f"{Style.BRIGHT}{Fore.YELLOW}WARNING  {Style.RESET_ALL}{msg}")

def error(msg: str) -> None:
    log(f"{Style.BRIGHT}{Fore.RED}ERROR    {Style.RESET_ALL}{msg}")
    traceback.print_stack()

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
