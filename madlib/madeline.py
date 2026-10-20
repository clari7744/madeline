from logging import getLogger
from os import listdir

import aiosqlite
from discord.ext import commands

from .cache import CacheMap
from .config import LOCAL_DEBUG, TESTING
from .tables import Connection, Player, RoleplayMessage, Room

log = getLogger(__name__)


class Madeline(commands.Bot):
    """
    Custom bot class for Madeline, extending commands.Bot.
    """

    db: aiosqlite.Connection
    # TODO: i hate building caches but this would unlock fuzzy searching
    # and probably be better than hitting the db on every autocomplete...
    # this is a bonus
    cache: CacheMap

    async def setup_hook(self) -> None:
        """
        Called when the bot is ready to set up its commands and cogs.
        """

        # Create caches
        self.cache = (
            CacheMap(self, Room)
            .add_cache(Player, foreign_refs={"location": Room, "following": Player})
            .add_cache(Connection, foreign_refs={"room": Room, "connected_to": Room})
            .add_cache(RoleplayMessage, foreign_refs={"sent_by": Player, "sent_to": Player})
        )
        # Set up the database (including the row factory)
        await self.setup_db()

    async def setup_db(self, reset: bool = False) -> None:
        """
        Load the database for the bot.

        Parameters
        ----------
        reset : bool, optional
            Whether to reset the database by dropping all tables and recreating them (default is False).
        """
        self.db.row_factory = aiosqlite.Row

        async with self.db.cursor() as c:
            await c.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key support
            if reset:
                with open("sqls/_drop_tables.sql", "r") as f:
                    drop_sqls = f.read().splitlines()
                for drop_sql in drop_sqls:
                    log.log(LOCAL_DEBUG, f"Executing drop SQL: {drop_sql}")
                    await c.execute(drop_sql)

                log.log(LOCAL_DEBUG, "Done dropping")

            for sql in sorted(listdir("sqls")):
                if not sql.startswith("_") and sql.endswith(".sql"):
                    if not sql.startswith("0") and (("test" in sql and not TESTING) or (TESTING and "test" not in sql)):
                        continue
                    log.log(LOCAL_DEBUG, f"Loading SQL schema: {sql}")
                    with open(f"sqls/{sql}", "r") as f:
                        stmts = f.read().split(";")
                        log.log(LOCAL_DEBUG, f"Loaded {len(stmts)} statements from {sql}")
                        for stmt in stmts:
                            if stmt.strip():
                                try:
                                    await c.execute(stmt)
                                except Exception as e:
                                    log.error(f"Error executing statement from {sql}: {stmt}\nError: {e}")
                                    raise e

        await self.db.commit()

        await self.cache.fill_caches()
