# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from discord.ext import commands
import discord
import os

OWNER: int = None

def is_guild_owner():
    async def pred(ctx: commands.Context):
        if ctx.guild is None:
            return False
        return ctx.guild.owner_id == ctx.author.id
    return commands.check(pred)

def admin_only():
    return commands.check_any(is_guild_owner(), commands.has_permissions(administrator=True))

def app_admin_only():
    return discord.app_commands.check(is_guild_owner(), commands.has_permissions(administrator=True))

def is_bot_owner(user_id: int) -> bool:
    """
    Shared logic to check if the user is the bot owner.
    """
    global OWNER
    if OWNER is None:
        OWNER = int(os.getenv('OWNER'))  # Load the bot owner ID from environment variables
    return user_id == OWNER

def bot_is_bot_owner():
    """
    Check for text commands (commands.check).
    """
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author is None or ctx.author.bot:
            return False
        return is_bot_owner(ctx.author.id)
    return commands.check(predicate)

def app_is_bot_owner():
    """
    Check for slash commands (app_commands.check).
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user is None or interaction.user.bot:
            return False
        return is_bot_owner(interaction.user.id)
    return discord.app_commands.check(predicate)
