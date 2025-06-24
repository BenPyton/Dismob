# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path
import json
from dismob import log
import os

config_dir: str = None

def getConfigDir() -> str:
    global config_dir
    if not config_dir:
        config_dir = os.getenv('CONFIG_DIR') or "config"
        log.info(f"Config directory has been set to `{config_dir}`")
    return config_dir

def ensure_directory(dir_path: str) -> None:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

def openJson(dirpath: str, filename: str):
    ensure_directory(dirpath)
    data = None
    try:
        with open(f"{dirpath}/{filename}", "r") as file:
            data = json.load(file)
    except Exception as e:
        log.error(f"Failed to load json file '{dirpath}/{filename}': {e}")
    return data

def saveJson(dirpath: str, filename: str, data) -> None:
    ensure_directory(dirpath)
    try:
        with open(f"{dirpath}/{filename}", "w+") as file:
            json.dump(data, file, indent = 4)
    except Exception as e:
        log.error(f"Failed to save json file '{dirpath}/{filename}': {e}")

def getConfigFilename(module: str = None) -> str:
    return f"config{f'.{module}' if module else ''}.json"

def openConfig(module: str = None) -> dict:
    return openJson(getConfigDir(), getConfigFilename(module)) or dict()

def saveConfig(data, module: str = None) -> None:
    saveJson(getConfigDir(), getConfigFilename(module), data)
