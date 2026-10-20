# ---------------------------------------------------------------------------------------#
#                                IMPORTS & PREREQUISITES
# ---------------------------------------------------------------------------------------#

import asyncio
from logging import INFO, getLogger

import aiosqlite
from discord import Intents, utils
from discord.ext import commands
from DPyUtils import load_extensions

from madlib import Madeline
from madlib.config import DATABASE_NAME, LOCAL_DEBUG, TOKEN

log = getLogger(__name__)

intents = Intents.default()
# intents.message_content = True
bot = Madeline(
    command_prefix=commands.when_mentioned,
    intents=intents,
    help_command=commands.MinimalHelpCommand(),
    case_insensitive=True,
    owner_ids={351516798635606020, 642416218967375882},
    owner_id=None,
)

bot.db = aiosqlite.connect(DATABASE_NAME)


async def main():
    async with bot, bot.db:
        await load_extensions(bot, extra_cogs=["jishaku", "DPyUtils.ContextEditor2"])
        await bot.start(TOKEN)


utils.setup_logging(level=17)
asyncio.run(main())
