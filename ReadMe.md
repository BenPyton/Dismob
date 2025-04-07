# Discord Modular Bot (Dismob)

This is a base discord modular bot using discord.py

Every features must be done in bot extensions placed in `plugins/<module>/main.py`.

An example extension `ping` is available which adds only one command `ping` to the bot.

## Installation

Make sure you've installed python.

Add a `.env` file at the root directory (alongside `main.py`) and add those lines:

```txt
BOT_TOKEN="your bot token here"
OWNER="your discord ID here"
CONFIG_DIR="config"
```

> [!NOTE]
> The `CONFIG_DIR` is optional and will default to `config` if not set.

Run this command:

```cmd
py -3 -m pip install requirements. txt
```

> [!NOTE]
> The `py -3` at the start is used to differentiate multiple versions of python installed on your computer.

Then to start the bot run:

```cmd
py -3 main.py
```

## Commands

There are some slash commands built into the bot itself, they help manage the modules and other crucial features.  
All of them are only available to the bot owner, as they have impact on all guilds the bot is added.

Command | Description
--- | ---
`/shutdown` | Stop the bot.
`/setprefix <prefix>` | Set the command prefix of the bot.
`/sync` | Sync the slash commands of the bot. This command is also available as standard bot command, useful when syncing for the first time.
`/module <command> [<args> ...]` | Manage the modules available to the bot. (see below for list of commands)

Below is the list of commands available to the `/module` command.

Command | Description
--- | ---
`list` | Display a list of all available modules (loaded or unloaded)
`status [<module> ...]` | Display the loaded status of provided module names (or all available modules if no module name provided).
`load <module> ...` | Load provided module names (at least one). For example `/module load ping` will load the `plugins/ping/main.py` extension.
`unload <module> ...` | Unload provided module names (at least one). For example `load ping` will unload the `plugins/ping/main.py` extension.
`reload <module> ...` | Reload provided module names (at least one). For example `load ping` will reload the `plugins/ping/main.py` extension.
