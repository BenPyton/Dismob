# Discord Modular Bot (Dismob)

This is a base discord modular bot using discord.py

Every features must be done in bot extensions placed in `plugins/<module>/main.py`.

An example extension `ping` is available which adds only one command `ping` to the bot.

## Installation

Make sure you've installed python.

open a command-line terminal in your project cloned/downloaded project folder.

Create a virtual environment for python.

```cmd
python -m venv venv
```

Activate it or enable it in your IDE.

Install dependencies.

```cmd
python -m pip install -r requirements.txt
```

Add a `.env` file at the root directory (alongside `main.py`) and add those lines:

```txt
BOT_TOKEN="your bot token here"
OWNER="your discord ID here"
CONFIG_DIR="config"
BOT_PREFIX="bot."
LOG_NAME="devbot"
LOG_CONSOLE_LEVEL="WARNING"
LOG_FILE_LEVEL="INFO"
```

> [!NOTE]
> The `CONFIG_DIR` is optional and will default to `config` if not set.  
> The `BOT_PREFIX` is optional and will default to `!` if not set.
> The `LOG_NAME` is optional and will default to `dismob` if not set.
> The `LOG_CONSOLE_LEVEL` is optional and will default to `INFO` if not set.
> The `LOG_FILE_LEVEL` is optional and will default to `INFO` if not set.

Then to start the bot run:

```cmd
python main.py
```

## Commands

There are some commands built into the bot itself, they help manage the modules and other crucial features.  
All of them are only available to the bot owner, as they have impact on all guilds the bot is added.

Command | Aliases | Description
--- | --- | ---
`shutdown` | | Stop the bot.
`sync` | | Sync the slash commands of the bot. This command is also available as standard bot command, useful when syncing for the first time.
`nick` | `name` | Change the nickname of the bot in the current server, if no name is passed, then it will reset it to the default one.
`modules <subcommand> [<args> ...]` | `mod` `plugins` | Manage the modules available to the bot. (see below for list of subcommands)

Below is the list of subcommands related to the module managements.  

Subcommand | Aliases | Description
--- | --- | ---
`status [<module> ...]` | `s` | Display the loaded status of provided module names (or all available modules if no module name provided).
`load <module> ...` | `l` `enable` `activate` | Load provided module names (at least one). For example `/module load ping` will load the `plugins/ping/main.py` extension.
`unload <module> ...` | `u` `disable` `deactivate` | Unload provided module names (at least one). For example `unload ping` will unload the `plugins/ping/main.py` extension.
`reload <module> ...` | `rl` `r` | Reload provided module names (at least one). For example `reload ping` will reload the `plugins/ping/main.py` extension.
