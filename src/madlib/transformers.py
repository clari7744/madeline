from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from discord import Interaction, app_commands
from discord.utils import MISSING

from .cache import SearchTerm
from .config import LOCAL_DEBUG
from .helpers import FLIP_DIRECTION, FailedTransform
from .tables import Connection, Player, Room, Zone

if TYPE_CHECKING:
    from .madeline import Madeline

log = getLogger(__name__)


class ZoneTransformer(app_commands.Transformer):
    async def transform(self, ixn: Interaction[Madeline], zone_name: str):
        """
        Validates a zone name.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        zone_name : str
            The zone name to transform.

        Returns
        -------
        Zone
            The validated Zone object.
        """
        log.log(LOCAL_DEBUG, f"Trying to transform '{zone_name}' into a Zone")
        zone = ixn.client.cache.get_cache(Zone).get_first(zone_name=SearchTerm(zone_name, ignore_case=True))
        if zone is not None:
            return zone
        raise FailedTransform(f"Invalid zone name `{zone_name}`.")

    async def autocomplete(self, ixn: Interaction[Madeline], current_name: str) -> list[app_commands.Choice[str]]:
        """
        Autocomplete zone names based on the current input.

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
            app_commands.Choice(name=zone.zone_name, value=zone.zone_name)
            for zone in ixn.client.cache.get_cache(Zone).get_many(zone_name=SearchTerm(current_name, fuzzy=True))
        ][:25]


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
        room = ixn.client.cache.get_cache(Room).get_first(room_name=SearchTerm(room_name, ignore_case=True))
        if room is not None:
            return room
        raise FailedTransform(f"Invalid room name `{room_name}`.")

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
        current_player = await Player.from_interaction(ixn)
        conn = ixn.client.cache.get_cache(Connection).get_first(
            room__room_name=current_player.location.room_name,
            connected_to__room_name=SearchTerm(adj_room_name, ignore_case=True),
        )
        if conn is not None:
            return conn
        raise FailedTransform(
            f"There is no direct connection between `{current_player.location}` and `{adj_room_name}`."
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

        matching_rooms = ixn.client.cache.get_cache(Connection).get_many(
            room__room_name=player.location.room_name,
            hidden=False,
            direction=current_name if current_name in FLIP_DIRECTION else MISSING,
            connected_to__room_name=(
                SearchTerm(current_name, fuzzy=True) if current_name and current_name not in FLIP_DIRECTION else MISSING
            ),
        )
        return [
            app_commands.Choice(name=f"{conn.connected_to} ({conn.direction})", value=conn.connected_to.room_name)
            for conn in matching_rooms
        ][:25]


class ConnectionTransformer(app_commands.Transformer):
    async def transform(self, ixn: Interaction[Madeline], room_name: str) -> Connection:
        """
        Validates a connection between two rooms split by |.

        Parameters
        ----------
        ixn : Interaction
            The interaction object.
        room_name : str
            The names of the rooms to validate the connection with.

        Returns
        -------
        Connection
            The Connection object representing the connection between the two rooms.
        """
        try:
            room1_name, room2_name = map(str.strip, room_name.split("|"))
        except ValueError:
            raise FailedTransform("Invalid connection format. Use 'room1 | room2'.")
        try:
            return await ixn.client.cache.get_cache(Connection).fetch((room1_name, room2_name))
        except ValueError as e:
            raise FailedTransform(f"There is no direct connection between `{room1_name}` and `{room2_name}`.")

    async def autocomplete(self, ixn: Interaction[Madeline], current_name: str) -> list[app_commands.Choice[str]]:
        """
        Autocomplete connections based on the current input.

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
        if "|" in current_name:
            room1_name, room2_name = map(str.strip, current_name.split("|", 1))
            matching_connections = ixn.client.cache.get_cache(Connection).get_many(
                room__room_name=SearchTerm(room1_name, fuzzy=True),
                connected_to__room_name=SearchTerm(room2_name, fuzzy=True),
            )
        else:
            matching_connections = ixn.client.cache.get_cache(Connection).get_many(
                match_all=False,
                room__room_name=SearchTerm(current_name, fuzzy=True),
                connected_to__room_name=SearchTerm(current_name, fuzzy=True),
            )
        return [
            app_commands.Choice(
                name=f"{conn.room}->{conn.connected_to} ({conn.direction})",
                value=f"{conn.room}|{conn.connected_to}",
            )
            for conn in matching_connections
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
            log.log(LOCAL_DEBUG, f"Failed to transform channel ID '{channel_id}' into a Player: {e}")
            raise FailedTransform(f"Invalid player channel `{channel_id}`.")

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
