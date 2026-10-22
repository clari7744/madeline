# ---------------------------------------------------------------------------------------#
#                                IMPORTS & PREREQUISITES
# ---------------------------------------------------------------------------------------#

import asyncio
from logging import DEBUG, INFO, getLogger

from discord import utils
from DPyUtils import load_extensions

from madlib import Madeline
from madlib.config import CURRENT_DEBUG, LOCAL_DEBUG, TOKEN

log = getLogger(__name__)

bot = Madeline()


@bot.event
async def on_ready():
    log.log(INFO, "-------------------------------------------------------------")
    log.log(INFO, f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.log(INFO, "-------------------------------------------------------------")


async def main():
    async with bot, bot.db:
        await load_extensions(bot, extra_cogs=["jishaku", "DPyUtils.ContextEditor2"])
        await bot.start(TOKEN)


utils.setup_logging(level=CURRENT_DEBUG)
asyncio.run(main())
