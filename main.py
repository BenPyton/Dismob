# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from dismob import log, filehelper, predicate
from dismob.helpcommand import MyHelpCommand

load_dotenv()

prefix: str = os.getenv('BOT_PREFIX', '!')

config = filehelper.openConfig()
if not config.get("modules"):
    config["modules"] = list()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True
bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=MyHelpCommand())

@bot.event
async def on_ready() -> None:
    log.info(f"Discord.py version: `{discord.__version__}`")
    log.info(f"Logged in as `{bot.user}`")
    for module in config["modules"]:
        try:
            await bot.load_extension(f"plugins.{module}.main")
            log.info(f"Module `{module}` successfully loaded.")
        except Exception as e:
            log.error(f"Failed to load module `{module}`: {e}")
    log.info(f"Bot is ready.")

def cleanup() -> None:
    log.info(f"Final cleanup")
    filehelper.saveConfig(config)

# Handles errors that occur during command execution.
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.MissingPermissions):
        # Handle user missing permissions
        await log.failure(ctx, "You do not have the required permissions to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        # Handle bot missing permissions
        await log.failure(ctx, "The bot does not have the required permissions to execute this command.")
    elif isinstance(error, commands.CheckFailure):
        # Handle check failures (e.g., user doesn't meet the requirements)
        await log.failure(ctx, "A check failed in the command.")
    elif isinstance(error, commands.CommandNotFound):
        # Handle unknown commands
        await log.failure(ctx, "This command does not exist.")
    else:
        # Handle other errors
        await log.failure(ctx, f"An unexpected error occurred while executing the command.\n```\n{error}\n```")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.MissingPermissions):
        # Handle user missing permissions
        await log.failure(interaction, "You do not have the required permissions to use this command.")
    if isinstance(error, discord.app_commands.BotMissingPermissions):
        # Handle bot missing permissions
        await log.failure(interaction, "The bot does not have the required permissions to execute this command.")
    elif isinstance(error, discord.app_commands.CheckFailure):
        # Handle check failures (e.g., user doesn't meet the requirements)
        await log.failure(interaction, "A check failed in the command.")
    elif isinstance(error, discord.app_commands.CommandNotFound):
        # Handle unknown commands
        await log.failure(interaction, "This command does not exist.")
    else:
        # Handle other errors
        await log.failure(interaction, f"An unexpected error occurred while executing the command.\n```\n{error}\n```")

####                       ####
#       General Commands      #
####                       ####

@bot.command(description="Sync the slash commands added/removed by modules")
@predicate.bot_is_bot_owner()
async def sync(ctx: commands.Context) -> None:
    if isinstance(ctx, commands.Context):
        await ctx.message.delete()
    log.info("Syncing slash commands")
    await bot.tree.sync()
    await log.success(ctx, "Slash commands synced successfully!\n*It may take some times to propagate to all guilds...*")
    
@bot.command(description="Shutdown gracefully the bot")
@predicate.bot_is_bot_owner()
async def shutdown(interaction: discord.Interaction) -> None:
    log.info("Shutting down bot...")
    await log.client(interaction, "Shutting down bot...")
    await bot.close()
    log.info("Bot has been shut off.")

####                        ####
#       Module Management      #
####                        ####

def getAllModules() -> list[str]:
    """
    Get all available modules in the `plugins` directory
    """
    available_modules: list[str] = []
    for dir in os.listdir("plugins"):
        available_modules.append(dir)
    return available_modules

def isModuleActive(module: str) -> bool:
    return True if bot.extensions.get(f"plugins.{module}.main") else False

def getModuleStatus(module: str) -> str:
    return "active :white_check_mark:" if isModuleActive(module) else "inactive :x:"

@bot.group(name="modules", aliases=["mod", "plugins"], invoke_without_command=True)
async def modules(ctx: commands.Context) -> None:
    await log.client(ctx, f"Manages modules of the bots. Use `{prefix}help modules` to get all available subcommands.")

@modules.command(name="list", aliases=["ls"])
async def listModules(ctx: commands.Context) -> None:
    """
    List all available modules in the `plugins` directory
    """
    allModules: list[str] = getAllModules()
    count: int = len(allModules)
    available_modules: str = f"There are {count if count > 0 else 'no'} available module{'s' if count > 1 else ''}:\n"
    for i, dir in enumerate(allModules):
        available_modules += f"{dir}{', ' if i < count - 1 else ''}"

    await log.client(ctx, available_modules)

@modules.command(name="status", aliases=["s"])
async def modulesStatus(ctx: commands.Context, *args: str) -> None:
    """
    Display the loaded status of provided modules
    """
    if len(args) <= 0:
        allModules: list[str] = getAllModules()
        result: str = f"All modules ({len(allModules)}):\n"
        for mod in allModules:
            result += f"- `{mod}` (status: {getModuleStatus(mod)})\n"
        await log.client(ctx, result)

    elif len(args) == 1:
        await log.client(ctx, f"`{args[0]}` module status: {getModuleStatus(args[0])}")

    else:
        module_status: str = f"Modules status:\n"
        for arg in args:
            module_status += f"- `{arg}` module status: {getModuleStatus(arg)}\n"
        await log.client(module_status)

@modules.command(name="load", aliases=["l", "enable", "activate"])
async def loadModules(ctx: commands.Context, *args: str) -> None:
    """
    Try to load the provided modules
    """
    if len(args) <= 0:
        await log.error(ctx, "You must provide at least one module name to load.")

    result = ""
    for arg in args:
        try:
            await bot.load_extension(f"plugins.{arg}.main")
            config["modules"].append(arg)
            result += f":white_check_mark: Module `{arg}` successfully loaded.\n"
        except commands.errors.ExtensionAlreadyLoaded:
            result += f":white_check_mark: Module `{arg}` is already loaded\n"
        except commands.errors.ExtensionNotFound:
            result += f":x: Module `{arg}` does not exists\n"
        except Exception as e:
            result += f":x: Failed to load module `{arg}`: `{e}`\n"
    await log.client(ctx, result)

@modules.command(name="unload", aliases=["u", "disable", "deactivate"])
async def unloadModules(ctx: commands.Context, *args: str) -> None:
    """
    Try to unload the provided modules
    """
    if len(args) <= 0:
        await log.error(ctx, "You must provide at least one module name to unload.")

    result = ""
    for arg in args:
        try:
            await bot.unload_extension(f"plugins.{arg}.main")
            config["modules"].remove(arg)
            result += f":white_check_mark: Module `{arg}` successfully unloaded.\n"
        except commands.errors.ExtensionNotLoaded:
            result += f":white_check_mark: Module `{arg}` is already unloaded\n"
        except commands.errors.ExtensionNotFound:
            result += f":x: Module `{arg}` does not exists\n"
        except Exception as e:
            result += f":x: Failed to unload module `{arg}`: `{e}`\n"
    await log.client(ctx, result)

@modules.command(name="reload", aliases=["rl", "r"])
async def reloadModules(ctx: commands.Context, *args: str) -> None:
    """
    Try to reload the provided modules
    """
    if len(args) <= 0:
        await log.error(ctx, "You must provide at least one module name to reload.")

    result = ""
    for arg in args:
        try:
            await bot.reload_extension(f"plugins.{arg}.main")
            result += f":white_check_mark: Module `{arg}` successfully reloaded.\n"
        except commands.errors.ExtensionNotLoaded:
            result += f":x: Module `{arg}` is not loaded\n"
        except commands.errors.ExtensionNotFound:
            result += f":x: Module `{arg}` does not exists\n"
        except Exception as e:
            result += f":x: Failed to reload module `{arg}`: `{e}`\n"
    await log.client(ctx, result)

# Check if the bot token is provided in the environment variables.
TOKEN: str = os.getenv('BOT_TOKEN')
if not TOKEN:
    log.error("No bot token provided. Please set the BOT_TOKEN environment variable.")
    exit(1)

# Start the bot and loop until it is shutdown.
bot.run(TOKEN)

# Do any potential cleanup after the bot stopped.
cleanup()
