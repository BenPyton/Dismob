# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import discord
from discord.ext import commands

class MyHelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        e = discord.Embed(title=f"Help", color=discord.Color.blurple(), description='')
        for page in self.paginator.pages:
            e.description += page
        e.set_footer(text=f"Commande faites par {self.context.author.display_name}", icon_url=self.context.author.display_avatar)
        await destination.send(embed=e)

    async def send_error_message(self, error: str):
        destination = self.get_destination()
        e = discord.Embed(title=f"Error", color=discord.Color.red(), description=error)
        for page in self.paginator.pages:
            e.description += page
        await destination.send(embed=e)
