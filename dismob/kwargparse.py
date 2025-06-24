# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Any
from dismob import log

class UnexpectedToken(Exception):
    def __init__(self, message: str):
        super().__init__(message)

def show_index(string: str, index: int) -> str:
    cursor: str = '-' * index
    cursor += '^'
    cursor += '-' * ((len(string) - 1) - index)
    return f"```\n{string}\n{cursor}\n```"

def parse_kwargs(kwargs: str) -> dict[str, str]:
    result: dict[str, str] = dict()
    key: str = ""
    value: str = ""
    str_ctx: bool = False # tells if we are in a quoted string or not
    write_value: bool = False # tells if we are writing into key or value
    escaping: bool = False # tells if the next character is escaped
    for i, c in enumerate(kwargs):
        #log.info(f"Character found: {c} (str_ctx: {str_ctx} | write_value: {write_value} | escaping: {escaping})")
        if not str_ctx:
            # save key,value into the result and get back to key writing
            if c == ' ':
                if not write_value:
                    raise UnexpectedToken(f"Found a space token when token `=` was expected.\n{show_index(kwargs, i)}")
                elif len(value) <= 0:
                    raise UnexpectedToken(f"Found a space token while value is empty.\n{show_index(kwargs, i)}")
                else:
                    write_value = False
                    result[key] = value
                    key = ""
                    value = ""
                    continue # do not add this character
            # switch from key writing to value writing
            elif not write_value and c == '=':
                if write_value:
                    raise UnexpectedToken(f"Found token `=` while already writing value. If it's part of the value consider using quotes.\n{show_index(kwargs, i)}")
                elif len(key) <= 0:
                    raise UnexpectedToken(f"Found token `=` but key is empty.\n{show_index(kwargs, i)}")
                else:
                    write_value = True
                    continue # do not add this character
            # start a string context if first character of value
            elif c == '"':
                if not write_value:
                    raise UnexpectedToken(f"Found token `\"` in key. This is not supported.\n{show_index(kwargs, i)}")
                elif write_value and len(value) > 0:
                    raise UnexpectedToken(f"Found token `\"` in middle of the value. This is not supported. Consider escaping it `\\\"` if it's part of the value.\n{show_index(kwargs, i)}")
                else:
                    str_ctx = True
                continue # do not add this character
        # We are in a string context, so only an unescaped quote closes the context   
        else:
            if not escaping:
                if c == '\\':
                    escaping = True
                elif c == '"':
                    str_ctx = False
                    continue # do not add this character
            else:
                escaping = False
        
        # Finally append the character to either the key or the value
        if write_value:
            value += c
        else:
            key += c

    if str_ctx:
        raise UnexpectedToken(f"Missing token `\"` at the end of value\n{show_index(kwargs, len(kwargs))}")

    log.info(f"key: {key} | value: {value}")
    # Write last key=value since there is no space to end.
    if len(key) > 0:
        result[key] = value

    return result
