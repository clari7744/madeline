from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from discord import Interaction, app_commands

from .cache import SearchTerm
from .config import LOCAL_DEBUG
from .helpers import FLIP_DIRECTION
from .tables import Connection, Player, Room

if TYPE_CHECKING:
    from .madeline import Madeline

log = getLogger(__name__)


class RoomTransformer(app_commands.Transformer):
    async def transform(self, ixn: Interaction[Madeline], room_name: str) -> Room:
        """
        Validates a room name.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        room_name : str
            The room name to transform.

        Returns
        -------
        Room
            The validated Room object.
        """
        log.log(LOCAL_DEBUG, f"Trying to transform '{room_name}' into a Room")
        try:
            return await ixn.client.cache.get_cache(Room).fetch(room_name)
        except ValueError as e:
            raise app_commands.TransformerError(f"Invalid room name '{room_name}': {e}")

    async def autocomplete(self, ixn: Interaction[Madeline], current_name: str) -> list[app_commands.Choice[str]]:
        """
        Autocomplete room names based on the current input.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        current_name : str
            The current input string.

        Returns
        -------
        list[app_commands.Choice[str]]
            A list of choices for the autocomplete.
        """
        return [
            app_commands.Choice(name=room.room_name, value=room.room_name)
            for room in ixn.client.cache.get_cache(Room).get_many(room_name=SearchTerm(current_name, fuzzy=True))
        ][:25]


class AdjacentRoomTransformer(app_commands.Transformer):
    async def transform(self, ixn: Interaction[Madeline], adj_room_name: str) -> Connection:
        """
        Validates that the room is adjacent to the player's current location.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        adj_room_name : str
            The room name to transform.

        Returns
        -------
        Connection
            The player's room, connected room, and direction of connection.
        """
        player = await ixn.client.cache.get_cache(Player).fetch(ixn.channel_id)
        try:
            return await ixn.client.cache.get_cache(Connection).fetch((player.location.room_name, adj_room_name))
        except ValueError as e:
            raise app_commands.TransformerError(f"Invalid connection '{adj_room_name}': {e}")

    async def autocomplete(self, ixn: Interaction[Madeline], current_name: str) -> list[app_commands.Choice[str]]:
        """
        Autocomplete adjacent room names based on the current input.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        current_name : str
            The current input string.

        Returns
        -------
        list[app_commands.Choice[str]]
            A list of choices for the autocomplete.
        """
        log.log(LOCAL_DEBUG, f"Autocomplete for adjacent rooms with current_name: {current_name}")
        player = await ixn.client.cache.get_cache(Player).fetch(ixn.channel_id)

        check = {}
        if current_name in FLIP_DIRECTION:
            check["direction"] = current_name
        elif current_name:
            check["connected_to__room_name"] = SearchTerm(current_name, fuzzy=True)
        log.log(LOCAL_DEBUG, f"Autocomplete check: {check}")

        matching_rooms = ixn.client.cache.get_cache(Connection).get_many(
            room__room_name=player.location.room_name, **check
        )
        return [
            app_commands.Choice(
                name=f"{conn.connected_to.room_name} ({conn.direction})", value=conn.connected_to.room_name
            )
            for conn in matching_rooms
        ][:25]


class PlayerTransformer(app_commands.Transformer):
    async def transform(self, ixn: Interaction[Madeline], channel_id: str) -> Player:
        """
        Transform a channel ID into a Player object.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        channel_id : str
            The channel ID to transform.

        Returns
        -------
        Player
            The Player object corresponding to the given channel ID.
        """
        log.log(LOCAL_DEBUG, f"Trying to transform '{channel_id}' into a Player")
        try:
            return await ixn.client.cache.get_cache(Player).fetch(int(channel_id))
        except ValueError as e:
            raise app_commands.TransformerError(f"Invalid player channel '{channel_id}': {e}")

    async def autocomplete(self, ixn: Interaction[Madeline], current_name: str) -> list[app_commands.Choice[str]]:
        """
        Autocomplete player names based on the current input.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        current_name : str
            The current input string.

        Returns
        -------
        list[app_commands.Choice[str]]
            A list of choices for the autocomplete.
        """
        # If the current input is empty, return all players (:25)
        # "" in value is True
        return [
            app_commands.Choice(name=player.short_name, value=str(player.channel_id))
            for player in ixn.client.cache.get_cache(Player).get_many(
                match_all=False,
                short_name=SearchTerm(current_name, fuzzy=True),
                full_name=SearchTerm(current_name, fuzzy=True),
            )
        ][:25]
