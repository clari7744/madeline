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
            raise FailedTransform(f"Invalid room name '{room_name}': {e}")

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
        player = await Player.from_interaction(ixn)
        try:
            return await ixn.client.cache.get_cache(Connection).fetch((player.location.room_name, adj_room_name))
        except ValueError as e:
            raise FailedTransform(
                f"There is no direct connection between '{player.location.room_name}' and '{adj_room_name}': {e}"
            )

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
        try:
            player = await Player.from_interaction(ixn)
        except Exception as e:
            log.info(f"Failed to fetch player for autocomplete: {e}")
            return []

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
            return await Player.from_interaction(ixn)
        except ValueError as e:
            raise FailedTransform(f"Invalid player channel '{channel_id}': {e}")

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


class RoommateTransformer(app_commands.Transformer):
    def __init__(self, action: str = "interact with"):
        """
        Initialize the RoommateTransformer.

        Parameters
        ----------
        action : str
            The action being performed (used in error messages).
        """
        self.action = action

    async def transform(self, ixn: Interaction[Madeline], channel_id: str) -> Player:
        """
        Transform a channel ID into a Player object, ensuring the player is a roommate.

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
        log.log(LOCAL_DEBUG, f"Trying to transform '{channel_id}' into a Roommate Player")
        try:
            current_player = await Player.from_interaction(ixn)
        except ValueError as e:
            log.log(LOCAL_DEBUG, f"Failed to fetch current player for roommate transformation: {e}")
            raise FailedTransform(f"<#{ixn.channel_id}> is not a valid player channel.")

        try:
            player = await ixn.client.cache.get_cache(Player).fetch(int(channel_id))
        except ValueError as e:
            log.log(LOCAL_DEBUG, f"Failed to fetch player for channel_id '{channel_id}': {e}")
            raise FailedTransform(f"{channel_id} is not a valid player channel or is not a roommate.")

        roommate, msg = current_player.is_roommate(player, action=self.action)
        if not roommate:
            log.log(LOCAL_DEBUG, f"Player '{player.short_name}' is not a roommate of '{current_player.short_name}'")
            raise FailedTransform(msg)

        return player

    async def autocomplete(self, ixn: Interaction[Madeline], current_name: str) -> list[app_commands.Choice[str]]:
        """
        Autocomplete roommate names based on the current input.

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
        try:
            current_player = await Player.from_interaction(ixn)
        except ValueError as e:
            log.info(f"Failed to fetch current player for roommate autocomplete: {e}")
            return []

        return [
            app_commands.Choice(name=player.short_name, value=str(player.channel_id))
            for player in ixn.client.cache.get_cache(Player).get_many(
                match_all=False,
                short_name=SearchTerm(current_name, fuzzy=True),
                full_name=SearchTerm(current_name, fuzzy=True),
            )
            if current_player.is_roommate(player, action="")[0] and player != current_player
        ][:25]


class FailedTransform(app_commands.AppCommandError):
    def __init__(self, message: str):
        super().__init__(message)
