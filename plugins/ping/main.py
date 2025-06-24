# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from discord.ext import commands
from dismob import log

async def setup(bot: commands.Bot):
    log.info("Module `ping` setup")
    await bot.add_cog(Ping(bot))

async def teardown(bot: commands.Bot):
    log.info("Module `ping` teardown")
    await bot.remove_cog("Ping")

class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        log.info(f"Cog `ping` initialized")

    @commands.command()
    async def ping(self, ctx: commands.Context):
        log.info(f"Command `ping` sent by {ctx.author}")
        await ctx.send("pong")
