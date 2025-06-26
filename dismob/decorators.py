# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import functools
from dismob import log

def cog_priority(priority: int):
    def decorator(cls):
        setattr(cls, "__cog_priority__", priority)
        return cls
    return decorator

def get_cog_priority(cls, default: int = 0) -> int:
    return getattr(cls, "__cog_priority__", default)

def suppress_command(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = None
        if len(args) > 1 and hasattr(args[1], 'message'):
            ctx = args[1]
        elif len(args) > 0 and hasattr(args[0], 'message'):
            ctx = args[0]
        else:
            ctx = kwargs.get('ctx')
        if ctx is not None and hasattr(ctx, 'message') and hasattr(ctx.message, 'delete'):
            try:
                await ctx.message.delete()
            except Exception:
                log.warning("Failed to delete member message")
        else:
            log.warning("No ctx found to delete member message")
        return await func(*args, **kwargs)
    return wrapper
