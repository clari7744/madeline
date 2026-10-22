# ---------------------------------------------------------------------------------------#
#                                IMPORTS & PREREQUISITES
# ---------------------------------------------------------------------------------------#

import asyncio
from logging import INFO, getLogger

from discord import utils
from DPyUtils import load_extensions

from madlib import Madeline
from madlib.config import CURRENT_DEBUG, LOCAL_DEBUG, TOKEN

log = getLogger(__name__)


async def main():
    async with Madeline() as bot, bot.db:
        await load_extensions(bot, extra_cogs=["jishaku", "DPyUtils.ContextEditor2"])
        await bot.start(TOKEN)


utils.setup_logging(level=CURRENT_DEBUG)
asyncio.run(main())
