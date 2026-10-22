from __future__ import annotations

from dataclasses import KW_ONLY, dataclass
from logging import getLogger
from operator import attrgetter
from typing import TYPE_CHECKING, Callable, Optional

import aiosqlite
from discord.utils import MISSING
from fuzzywuzzy import fuzz

from .config import LOCAL_DEBUG
from .tables import DbValueT, Table

if TYPE_CHECKING:
    from .madeline import Madeline

log = getLogger(__name__)


@dataclass
class SearchTerm:
    """
    Represents a search term for filtering cached objects.

    Attributes
    ----------
    value : DbValueT
        The value to search for.
    ignore_case : bool
        Whether to ignore case when comparing values (default is False).
    fuzzy : bool
        Whether to perform a fuzzy search (default is False).
    negative : bool
        Whether to negate the search (default is False).
    """

    value: DbValueT | Table
    _: KW_ONLY
    ignore_case: bool = False
    fuzzy: bool = False
    negative: bool = False

    def __str__(self) -> str:
        return str(self.value)


CacheKeyT = DbValueT | tuple[DbValueT]  # The types that can be used as keys in the cache


class Cache[CachedT: Table]:
    """
    A cache for storing and retrieving objects of a specific type.
    """

    def __init__(
        self, cached_type: type[CachedT], /, *, bot: Madeline, foreign_refs: Optional[dict[str, type[Table]]] = None
    ):
        self.type = cached_type
        self.foreign_refs = foreign_refs or {}
        self.bot = bot

        self._cache: dict[CacheKeyT, CachedT] = {}

    def get(self, key: CacheKeyT) -> Optional[CachedT]:
        """
        Get an object from the cache by its primary key.

        Parameters
        ----------
        key : CacheKeyT
            The primary key of the object to retrieve.
        """
        return self._cache.get(key)

    def _search(
        self,
        *,
        many: bool,
        match_all: bool = True,
        predicate: Callable[[CachedT], bool] = None,
        **kwargs: dict[str, DbValueT | Table | SearchTerm],
    ) -> list[CachedT]:
        """
        Get objects from the cache that match the given criteria. If the criteria is empty, return all cached objects.

        Parameters
        ----------
        many : bool
            Whether to return multiple objects (True) or just the first match (False).
        match_all : bool, optional
            If True, all criteria must match for an object to be included. If False, any criteria match is sufficient (default is True).
        predicate : callable, optional
            A function that takes a cached object and returns True if it should be included in the results.
        **kwargs : dict[str, DbValueT | Table | SearchTerm]
            The criteria to filter the cached objects.

        Returns
        -------
        list[CachedT]
            A list of cached objects that match the criteria.
        """
        log.log(LOCAL_DEBUG, f"Getting many from cache for {self.type.__name__} with criteria: {kwargs}")
        # example kwargs: room__room_name="foo", connected_to__room_name={"value": "bar", "fuzzy": True}
        # example kwargs: room__room_name="foo", connected_to__room_name=(SearchTerm("bar", fuzzy=True),)

        def matches(
            value: DbValueT | Table,
            to_match: DbValueT | Table | SearchTerm = MISSING,
        ) -> bool:
            """
            Check if a value matches a search term.

            Parameters
            ----------
            value : DbValueT | Table
                The source-of-truth value to compare against.
            to_match : DbValueT | Table | SearchTerm
                The value to compare against the source-of-truth value. If it's a SearchTerm, it can provide extra config options.
            Returns
            -------
            bool
                True if the value matches the search term, False otherwise.
            """
            log.log(LOCAL_DEBUG, f"Matching search term: {to_match} against known value: {value}")
            if not isinstance(to_match, SearchTerm):
                to_match = SearchTerm(to_match)
            if to_match.value is MISSING:
                return True
            svalue = str(value)
            tvalue = str(to_match)
            if to_match.fuzzy or to_match.ignore_case:
                svalue = svalue.lower()
                tvalue = tvalue.lower()
            log.log(LOCAL_DEBUG, f"STRINGS: Matching search term: {tvalue} against known value: {svalue}")
            # we're doing this LATER. please don't give this a table i will scream (edit: tables will work great actually)
            # (can you tell i got tired?)
            if isinstance(to_match.value, Table):
                # THEN NOTHING
                # IT HAS A __EQ__
                # SHUT UP COPILOT
                # IT CAN EVEN FUZZY SEARCH
                # BECAUSE IT HAS A __STR__ OR AT LEAST SHOULD
                ...
            if to_match.fuzzy:
                result = fuzz.partial_ratio(svalue, tvalue) > 80 or tvalue in svalue
                log.log(LOCAL_DEBUG, f"FUZZY MATCH: {tvalue} vs {svalue} = {result}")
            else:
                result = value == to_match.value
                log.log(LOCAL_DEBUG, f"EXACT MATCH: {to_match.value} vs {value} = {result}")
                if to_match.ignore_case:
                    result = svalue == tvalue
                    log.log(LOCAL_DEBUG, f"IGNORE CASE: {tvalue.lower()} vs {svalue.lower()} = {result}")
            if to_match.negative:
                result = not result
                log.log(LOCAL_DEBUG, f"NEGATE MATCH: {tvalue} vs {svalue} = {result}")
            log.log(LOCAL_DEBUG, f"FINAL MATCH: {tvalue} vs {svalue} = {result}")
            return result

        def _pred(item: CachedT) -> bool:
            for k, v in kwargs.items():
                log.log(LOCAL_DEBUG, f"Filtering cache for {self.type.__name__} with key: {k}, value: {v}")
                log.log(
                    LOCAL_DEBUG,
                    f"Item: {item}, Attribute: {item}.{k.replace('__', '.')} = {attrgetter(k.replace('__', '.'))(item)}",
                )
                success = matches(attrgetter(k.replace("__", "."))(item), v)
                if success and not match_all:
                    log.log(LOCAL_DEBUG, f"Any match required. Found a match for {k} with value: {v}")
                    return True
                elif not success and match_all:
                    log.log(LOCAL_DEBUG, f"All match required. No match for {k} with value: {v}")
                    return False
                # otherwise check others to find a success (if not match_all) or a failure (if match_all)
                # or it returns true at the end if match_all matched all!
            if predicate:
                # any() and all others are false
                # all() and all are true so far
                # aka no early return so we check custom predicate too
                return predicate(item)
            return match_all  # if match_all is True, we matched all, otherwise we didn't match any

        if many:
            return [itm for itm in self._cache.values() if _pred(itm)]
        for itm in self._cache.values():
            if _pred(itm):
                return [itm]
        return []

    def get_many(
        self,
        *,
        match_all: bool = True,
        predicate: Callable[[CachedT], bool] = None,
        **kwargs: dict[str, DbValueT | Table | SearchTerm],
    ) -> list[CachedT]:
        """
        Get all objects from the cache that match the given criteria.

        Parameters
        ----------
        match_all : bool, optional
            If True, all criteria must match for an object to be included. If False, any criteria match is sufficient (default is True).
        predicate : callable, optional
            A function that takes a cached object and returns True if it should be included in the results.
        **kwargs : dict[str, DbValueT | Table | SearchTerm]
            The criteria to filter the cached objects.

        Returns
        -------
        list[CachedT]
            A list of cached objects that match the given criteria.
        """
        return self._search(many=True, match_all=match_all, predicate=predicate, **kwargs)

    def get_first(
        self,
        *,
        match_all: bool = True,
        predicate: Callable[[CachedT], bool] = None,
        **kwargs: dict[str, DbValueT | Table | SearchTerm],
    ) -> Optional[CachedT]:
        """
        Get the first object from the cache that matches the given criteria.

        Parameters
        ----------
        match_all : bool, optional
            If True, all criteria must match for an object to be included. If False, any criteria match is sufficient (default is True).
        predicate : callable, optional
            A function that takes a cached object and returns True if it should be included in the results
        **kwargs : dict[str, DbValueT | Table | SearchTerm]
            The criteria to filter the cached objects.
        """
        results = self._search(many=False, match_all=match_all, predicate=predicate, **kwargs)
        if not len(results):
            log.log(LOCAL_DEBUG, f"No results found for criteria: {kwargs}")
            return None
        elif len(results) > 1:
            log.warning(f"Expected one result but found {len(results)} for criteria: {kwargs}")
            # raise ValueError(f"Expected one result but found {len(results)} for criteria: {kwargs}")
        return results[0]

    async def fetch(self, key: CacheKeyT) -> CachedT:
        log.log(LOCAL_DEBUG, f"Fetching {self.type.__name__} with key: {key}")
        if key is None:
            raise ValueError("Key cannot be None when fetching from cache.")
        obj = self.get(key)
        if obj is not None:
            return obj
        log.log(LOCAL_DEBUG, f"{self.type.__name__} with key {key} not found in cache. Fetching from database...")
        # If not in cache, fetch from database
        where_clause = " AND ".join(f"{key}=?" for key in self.type.primary_key)

        if not isinstance(key, tuple):
            key = (key,)
        async with self.bot.db.cursor() as c:
            await c.execute(f"SELECT * FROM {self.type.table_name} WHERE {where_clause}", key)
            row = await c.fetchone()
            if row is None:
                raise ValueError(f"No {self.type.__name__} found with the given primary key(s) {key}.")
            obj: CachedT = await self.load_from_row(row)
            self.set(obj)  # Cache the fetched object
            for ref_name, ref_type in self.foreign_refs.items():
                log.log(LOCAL_DEBUG, f"Resolving foreign reference {ref_name} for {self.type.__name__} with key {key}")
                # player.location
                # room_cache
                ref_cache = self.bot.cache.get_cache(ref_type)

                # room_name = getattr(player, "location").room_name
                log.log(LOCAL_DEBUG, f"getting {obj}.{ref_name} primary key values")
                ref_item = getattr(obj, ref_name)
                if ref_item is None:
                    log.log(LOCAL_DEBUG, f"{obj}.{ref_name} is None, skipping foreign reference resolution.")
                    continue
                ref_pk_val = ref_item.get_primary_key_values()
                # room_name = room.room_name
                # room = await room_cache.fetch(room_name)
                ref_obj = await ref_cache.fetch(ref_pk_val)
                # player.location = room
                setattr(obj, ref_name, ref_obj)
            return obj

    def set(self, item: CachedT):
        log.log(LOCAL_DEBUG, f"Setting item in cache: {repr(item)}")
        if not isinstance(item, self.type):
            raise ValueError(f"Item must be of the same type as the cache's model_type (got a {type(item).__name__}).")
        item.bot = self.bot  # Ensure the bot reference is set on the item
        # PRIMARY KEY IS THE NAMES OF THE COLUMNS SHUT UP COPILOT
        pk_values = item.get_primary_key_values()
        if item.composite_key:
            self._cache[pk_values] = item
        else:
            self._cache[pk_values[0]] = item
        return self

    async def write_many(self, items: list[CachedT]) -> None:
        """
        Write multiple objects to the database and update the cache.

        Parameters
        ----------
        bot : Madeline
            The bot instance to use for database access.
        items : list[CachedT]
            A list of objects to write to the database.
        """
        if not items:
            return
        log.log(LOCAL_DEBUG, f"Writing {len(items)} items to database for {self.type.__name__}")

        # Build sequence of tuples for executemany
        param_list: list[tuple[str]] = []
        columns = []
        for item in items:
            if item is None:
                continue
            if not isinstance(item, self.type):
                raise ValueError(
                    f"All objects must be of the same type as the cache's model_type (got a {type(item).__name__})."
                )
            log.log(LOCAL_DEBUG, f"Flattening item for database write: {repr(item)}")
            flat = item.flatten()
            if not columns:
                columns = list(flat.keys())
                log.log(LOCAL_DEBUG, f"Database write keys: {columns}")
            param_list.append(tuple(flat.values()))
            log.log(LOCAL_DEBUG, f"Flattened values: {param_list[-1]}")

        # Extract column names and prepare SQL once
        # Assuming all objs in objs are of the same CachedT type
        # columns = list(param_list[0].keys())
        log.log(LOCAL_DEBUG, f"Fields to update: {columns}")

        # Single cursor, single executemany call, single commit
        async with self.bot.db.cursor() as c:
            await c.executemany(
                f"""
                    INSERT INTO {self.type.table_name} ({', '.join(columns)})
                    VALUES ({', '.join('?' for _ in columns)})
                    ON CONFLICT DO UPDATE SET {', '.join(f"{col}=excluded.{col}" for col in columns if col not in self.type.primary_key)}
                """,
                param_list,
            )
        await self.bot.db.commit()

        # Update in-memory cache
        for item in items:
            self.set(item)

    async def write(self, item: CachedT) -> None:
        """
        Write an object to the database and update the cache.

        Parameters
        ----------
        bot : Madeline
            The bot instance to use for database access.
        item : CachedT
            The object to write to the database.
        """
        await self.write_many([item])

    def remove(self, item: CachedT) -> CachedT:
        """
        Remove an object from the cache.

        Parameters
        ----------
        item : CachedT
            The object to remove from the cache.
        """
        if not isinstance(item, self.type):
            raise ValueError(f"Item must be of the same type as the cache's model_type (got a {type(item).__name__}).")
        pk_values = item.get_primary_key_values()
        if item.composite_key:
            return self._cache.pop(pk_values, None)
        else:
            return self._cache.pop(pk_values[0], None)

    async def delete_many(self, items: list[CachedT]) -> None:
        """
        Delete multiple objects from the database and remove them from the cache.

        Parameters
        ----------
        items : list[CachedT]
            A list of objects to delete.
        """
        if not items:
            return

        for itm in items:
            if not isinstance(itm, self.type):
                raise ValueError(
                    f"All items must be of the same type as the cache's model_type (got a {type(itm).__name__})."
                )
            self.remove(itm)  # Remove from cache first to avoid stale data if deletion fails
        where_clause = " AND ".join(f"{key}=?" for key in self.type.primary_key)
        async with self.bot.db.cursor() as c:
            await c.executemany(
                f"DELETE FROM {self.type.table_name} WHERE {where_clause}",
                [item.get_primary_key_values() for item in items],
            )
        await self.bot.db.commit()

    async def delete(self, item: CachedT) -> None:
        """
        Delete an object from the database and remove it from the cache.

        Parameters
        ----------
        item : CachedT
            The object to delete.
        """
        await self.delete_many([item])

    async def load_from_row(self, row: aiosqlite.Row) -> CachedT:
        """
        Create an instance of the cached dataclass from a database row.

        Parameters
        ----------
        row : aiosqlite.Row
            A row from the database.

        Returns
        -------
        CachedT
            An instance of the cached dataclass type.
        """
        data = dict(row)
        # this breaks if foreign key reference is a tuple but idc bc we don't need it to my knowledge
        # BUILD FOREIGN KEY REFS #
        for key in self.foreign_refs.keys():
            if key in row.keys() and row[key] is not None:
                ftable = self.foreign_refs[key]
                # link to existing object. fetch will cache if it doesn't exist
                data[key] = await self.bot.cache.get_cache(ftable).fetch(row[key])

        return self.type(**data)


class CacheMap:
    """A map of caches for different table types."""

    def __init__(self, bot: Madeline, *cached_types: type[Table]):
        self.bot = bot
        self._caches: dict[type[Table], Cache] = {
            cached_type: Cache(cached_type, bot=bot) for cached_type in cached_types
        }

    def add_cache[TableT: Table](
        self, table_type: type[TableT], /, *, foreign_refs: dict[str, type[Table]]
    ) -> CacheMap:
        """
        Add a cache for a specific table type to the cache map.

        Parameters
        ----------
        table_type : type[TableT]
            The table type for which to add a cache.
        foreign_refs : dict[str, type[Table]]
            A dictionary mapping field names to their corresponding foreign table types.

        Returns
        -------
        CacheMap
            The current instance of CacheMap, allowing for method chaining.
        """
        if table_type not in self._caches:
            self._caches[table_type] = Cache(table_type, bot=self.bot, foreign_refs=foreign_refs)
        return self

    def get_cache[TableT: Table](self, table_type: type[TableT]) -> Cache[TableT]:
        """
        Get the cache for a specific table type.

        Parameters
        ----------
        table_type : type[TableT]
            The table type for which to get the cache.

        Returns
        -------
        Cache[TableT]
            The cache for the specified table type.

        Raises
        """
        log.log(LOCAL_DEBUG, f"Getting cache: {table_type}")
        if table_type not in self._caches:
            raise ValueError(f"No cache found for table type {table_type.__name__}. Please add it first.")
        return self._caches[table_type]

    def clear_caches(self):
        """
        Clear all caches in the cache map.
        """
        for cache in self._caches.values():
            cache._cache.clear()

    def remove_cache[TableT: Table](self, table_type: type[TableT]) -> CacheMap:
        """
        Remove the cache for a specific table type from the cache map.

        Parameters
        ----------
        table_type : type[TableT]
            The table type for which to remove the cache.

        Returns
        -------
        CacheMap
            The current instance of CacheMap, allowing for method chaining.
        """
        if table_type in self._caches:
            del self._caches[table_type]
        return self

    async def fill_caches(self):
        """
        Fill all caches in the cache map with data from the database.
        """
        self.clear_caches()
        async with self.bot.db.cursor() as c:
            for table_type, cache in self._caches.items():
                await c.execute(f"SELECT * FROM {table_type.table_name}")
                async for row in c:
                    obj: Table = await cache.load_from_row(row)
                    log.log(LOCAL_DEBUG, f"Filling cache for {table_type.__name__} with object: {obj}")
                    cache.set(obj)
