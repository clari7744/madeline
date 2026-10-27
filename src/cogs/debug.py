from logging import getLogger

import DPyUtils
import tabulate
from discord import Color, Embed, Interaction, PartialEmoji, TextChannel, app_commands
from discord.ext import commands
from discord.utils import MISSING

from madlib import (
    DIRECTION,
    FLIP_DIRECTION,
    Connection,
    ConnectionTransformer,
    Madeline,
    Player,
    PlayerTransformer,
    Room,
    RoomTransformer,
    Zone,
    ZoneTransformer,
)
from madlib.config import COMMAND_GUILDS, LOCAL_DEBUG
from madlib.ui import TablePaginator, TablePaginatorView

log = getLogger(__name__)


@app_commands.guild_only()
# @app_commands.guilds(*COMMAND_GUILDS)
@app_commands.default_permissions(administrator=True)
@app_commands.check(lambda ixn: ixn.client.is_owner(ixn.user))
class DebugCog(commands.GroupCog):
    """Debug commands for the bot."""

    def __init__(self, bot: Madeline):
        self.bot = bot

    def interaction_check(self, ixn: Interaction[Madeline]) -> bool:
        """Check if the user is an owner."""
        return ixn.user.id in ixn.client.owner_ids


async def set_clr(obj: Zone | Room, color: str):
    """Set the color of a zone or room."""
    if color.isdigit():
        color = hex(int(color))
    clr = Color.from_str(color)
    obj.color = clr.value
    await obj.save()
    return clr


def clr_embed(obj: Zone | Room) -> Embed:
    return Embed(
        title=f"{obj}'s Color",
        description=f"Current color of {obj} is:\n"
        f"**Hex:** `#{obj.color:06x}`\n"
        f"**Int:** `{obj.color}`\n"
        f"**RGB:** `{Color(obj.color).to_rgb()}`",
        color=obj.color,
    )


class ZoneMgmtCog(DebugCog, name="zone"):
    """Manage zones in the database."""

    @app_commands.command(name="add")
    async def zone_add(
        self,
        ixn: Interaction[Madeline],
        zone_name: str,
        description: str = "default",
    ):
        """
        Add a zone to the database.

        Parameters
        ----------
        zone_name : str
            The name of the zone.
        description : str
            The description of the zone.
        """
        async with ixn.client.db.cursor() as c:
            try:
                await c.execute("INSERT INTO zones (zone_name, description) VALUES (?, ?)", (zone_name, description))
            except Exception as e:
                return await ixn.send(f"Error adding zone: {e}", ephemeral=True)
        await ixn.client.db.commit()
        return await ixn.send(f"Added `{zone_name}` to the database.")

    @app_commands.command(name="color")
    async def zone_color(
        self, ixn: Interaction[Madeline], zone: app_commands.Transform[Zone, ZoneTransformer], color: str = None
    ):
        """
        Set or get the color of a zone.

        Parameters
        ----------
        zone : Zone
            The zone to set or get the color for.
        color : str, optional
            The color to set (hex or int). If not provided, shows the current color of the zone.
        """
        if color is None:
            return await ixn.send(embed=clr_embed(zone))
        res = await set_clr(zone, color)
        return await ixn.send(f"Set color of zone `{zone}` to `{res}`.")

    @app_commands.command(name="list")
    async def zone_list(self, ixn: Interaction[Madeline]):
        """
        List all zones in the database.
        """
        async with ixn.client.db.cursor() as c:
            await c.execute("SELECT zone_name, description FROM zones")
            zones = await c.fetchall()

        if not zones:
            return await ixn.send("No zones found in the database.")

        zlist = tabulate.tabulate(
            [tuple(z) for z in zones],
            headers=["Zone Name", "Description"],
            tablefmt="fancy_grid",
        )
        return await ixn.send(f"## Saved Zones\n```\n{zlist}```")

    @app_commands.command(name="remove")
    async def zone_remove(self, ixn: Interaction[Madeline], zone: app_commands.Transform[Zone, ZoneTransformer]):
        """
        Remove a zone from the database.

        Parameters
        ----------
        zone : Zone
            The zone to remove.
        """
        await zone.delete()
        return await ixn.send(f"Removed `{zone}` from the database.")


class RoomMgmtCog(DebugCog, name="room"):
    """Manage rooms in the database."""

    @app_commands.command(name="add")
    async def room_add(
        self,
        ixn: Interaction[Madeline],
        room_name: str,
        zone: app_commands.Transform[Zone, ZoneTransformer],
        description: str,
        color: str = "#000000",
        locked: bool = False,
    ):
        """
        Add a room to the database.

        Parameters
        ----------
        room_name : str
            The name of the room.
        zone : Zone
            The zone of the room.
        description : str
            The description of the room.
        color : str, optional
            The color of the room (default is "#000000").
        locked : bool, optional
            Whether the room is locked (default is False).
        """
        if color.isdigit():
            color = hex(int(color))
        r = Room(
            room_name=room_name,
            zone=zone,
            description=description,
            color=Color.from_str(color).value,
            locked=locked,
        )
        await r.save(ixn.client)
        return await ixn.send(f"Added `{room_name}` to the database.")

    @app_commands.command(name="update")
    async def room_update(
        self,
        ixn: Interaction[Madeline],
        room: app_commands.Transform[Room, RoomTransformer],
        zone: app_commands.Transform[Zone, ZoneTransformer] | None = None,
        description: str | None = None,
        color: str | None = None,
        locked: bool | None = None,
    ):
        """
        Update a room's information in the database.

        Parameters
        ----------
        room : Room
            The room to update.
        zone : Zone, optional
            The new zone of the room.
        description : str, optional
            The new description of the room.
        color : str, optional
            The new color of the room.
        locked : bool, optional
            The new locked status of the room.
        """
        updates = {
            "zone": zone,
            "description": description,
            "color": color,
            "locked": locked,
        }
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            return await ixn.send("No updates provided.", ephemeral=True)

        for key, value in updates.items():
            setattr(room, key, value)

        await room.save()
        return await ixn.send(f"Updated `{room.room_name}` in the database.")

    @app_commands.command(name="color")
    async def room_color(
        self, ixn: Interaction[Madeline], room: app_commands.Transform[Room, RoomTransformer], color: str = None
    ):
        """
        Set or get the color of a room.

        Parameters
        ----------
        room : Room
            The room to set or get the color for.
        color : str, optional
            The color to set (hex or int). If not provided, shows the current color of the room.
        """
        if color is None:
            return await ixn.send(embeds=[clr_embed(room), clr_embed(room.zone)])
        res = await set_clr(room, color)
        return await ixn.send(f"Set color of room `{room}` to `{res}`.")

    @app_commands.command(name="list")
    async def room_list(self, ixn: Interaction[Madeline]):
        """
        List all rooms in the database.
        """
        rooms = self.bot.cache.get_cache(Room).get_many()

        if not rooms:
            return await ixn.send("No rooms found in the cache.")

        rpaginator = TablePaginator(
            headers=["Room Name", "Zone", "Description"],
            rows=[[r.room_name, r.zone.zone_name, r.description] for r in rooms],
            max_rows_per_page=8,
        )

        await ixn.send(content=rpaginator.pages[0], view=TablePaginatorView(author=ixn.user, paginator=rpaginator))

    @app_commands.command(name="remove")
    async def room_remove(self, ixn: Interaction[Madeline], room: app_commands.Transform[Room, RoomTransformer]):
        """
        Remove a room from the database.

        Parameters
        ----------
        room : Room
            The room to remove.
        """
        await room.delete()
        return await ixn.send(f"Removed `{room.room_name}` from the database.")


class PlayerMgmtCog(DebugCog, name="player"):
    """Manage players in the database."""

    @app_commands.command(name="add")
    async def player_add(
        self,
        ixn: Interaction[Madeline],
        channel: TextChannel,
        short_name: str,
        location: app_commands.Transform[Room, RoomTransformer],
        full_name: str = None,
        emoji: str = None,
        notifications_enabled: bool = True,
        appearance: str = None,
        action: str = None,
        subtle: str = None,
        following: app_commands.Transform[Player, PlayerTransformer] = None,
    ):
        """
        Add a player to the database.

        Parameters
        ----------
        channel : TextChannel
            The Discord channel associated with the player.
        short_name : str
            The short name of the player.
        full_name : str
            The full name of the player.
        location : str
            The location of the player.
        emoji : str, optional
            The emoji for the player. Defaults to None.
        appearance : str, optional
            The appearance of the player. Defaults to "default".
        action : str, optional
            The action of the player. Defaults to "default".
        subtle : str, optional
            The subtle of the player. Defaults to "default".
        following : Player, optional
            The player that this player is following. Defaults to None.
        """
        p = Player(
            channel_id=channel.id,
            short_name=short_name,
            full_name=full_name or short_name,
            emoji_id=getattr(PartialEmoji.from_str(emoji or "0"), "id", emoji),
            notifications_enabled=notifications_enabled,
            location=location,
            appearance=appearance,
            action=action,
            subtle=subtle,
            following=following,
        )
        await p.save(ixn.client)
        return await ixn.send(f"Added `{short_name}` to the database.")

    @app_commands.command(name="update")
    async def player_update(
        self,
        ixn: Interaction[Madeline],
        player: app_commands.Transform[Player, PlayerTransformer],
        short_name: str | None = None,
        full_name: str | None = None,
        location: app_commands.Transform[Room, RoomTransformer] | None = None,
        emoji: str | None = None,
        notifications_enabled: bool | None = None,
        appearance: str | None = None,
        action: str | None = None,
        subtle: str | None = None,
        following: app_commands.Transform[Player, PlayerTransformer] | None = None,
    ):
        """
        Update a player's information in the database.

        Parameters
        ----------
        player : Player
            The player to update.
        short_name : str, optional
            The new short name of the player.
        full_name : str, optional
            The new full name of the player.
        location : Room, optional
            The new location of the player.
        emoji : str, optional
            The new emoji for the player.
        notifications_enabled : bool, optional
            Whether notifications are enabled for the player.
        appearance : str, optional
            The new appearance of the player.
        action : str, optional
            The new action of the player.
        subtle : str, optional
            The new subtle of the player.
        following : Player, optional
            The new player that the current player is following.
        """
        try_e = PartialEmoji.from_str(emoji) if emoji else None
        eid = getattr(try_e, "id", emoji)
        updates = {
            "short_name": short_name,
            "full_name": full_name,
            "location": location,
            "emoji_id": eid,
            "notifications_enabled": notifications_enabled,
            "appearance": appearance,
            "action": action,
            "subtle": subtle,
            "following": following,
        }
        updates = {k: v for k, v in updates.items() if v is not None}

        if not updates:
            return await ixn.send("No updates provided.", ephemeral=True)

        for key, value in updates.items():
            setattr(player, key, value)

        await player.save()
        return await ixn.send(f"Updated `{player.short_name}` in the database.")

    @app_commands.command(name="list")
    async def player_list(self, ixn: Interaction[Madeline], room: app_commands.Transform[Room, RoomTransformer] = None):
        """
        List all players in the cache.

        Parameters
        ----------
        room : Room, optional
            The room to filter players by (default is None, which lists all players).
        """
        players = self.bot.cache.get_cache(Player).get_many(location=room or MISSING)

        if not players:
            return await ixn.send("No players found in the cache.")

        # Create table paginator chunking 8 rows per page
        ppaginator = TablePaginator(
            headers=["Short Name", "Full Name", "Location", "Following"],
            rows=[[p.short_name, p.full_name, str(p.location), str(p.following)] for p in players],
            max_rows_per_page=8,
        )

        # Send first page with navigation view
        await ixn.send(content=ppaginator.pages[0], view=TablePaginatorView(author=ixn.user, paginator=ppaginator))

    @app_commands.command(name="remove")
    async def player_remove(
        self, ixn: Interaction[Madeline], player: app_commands.Transform[Player, PlayerTransformer]
    ):
        """
        Remove a player from the database.

        Parameters
        ----------
        player : Player
            The player to remove.
        """
        await player.delete()
        return await ixn.send(f"Removed `{player.short_name}` from the database.")


class ConnectionMgmtCog(DebugCog, name="connection"):
    """Manage connections between rooms."""

    @app_commands.command(name="add")
    async def connection_add(
        self,
        ixn: Interaction[Madeline],
        room: app_commands.Transform[Room, RoomTransformer],
        direction: DIRECTION,
        connected_to: app_commands.Transform[Room, RoomTransformer],
        hidden: bool = False,
        bidirectional: bool = True,
    ):
        """
        Add a connection between two rooms in the database. Note that connections are bidirectional by default.

        Parameters
        ----------
        room : Room
            The room to connect.
        connected_to : Room
            The room it connects to.
        direction : str
            The direction of the connection.
        hidden : bool, optional
            Whether the connection is hidden (default is False).
        bidirectional : bool, optional
            Whether the connection is bidirectional (default is True).
        """
        if room == connected_to:
            return await ixn.send("A room cannot connect to itself.", ephemeral=True)
        conns = [Connection(room=room, connected_to=connected_to, direction=direction, hidden=hidden)]
        if bidirectional:
            conns.append(
                Connection(room=connected_to, connected_to=room, direction=FLIP_DIRECTION[direction], hidden=hidden)
            )
        await self.bot.cache.get_cache(Connection).write_many(conns)
        return await ixn.send(
            f"Added connection from `{room.room_name}` to `{connected_to.room_name}` ({'bi' if bidirectional else 'uni'}directionally). Hidden: {hidden}."
        )

    @app_commands.command(name="update")
    async def connection_update(
        self,
        ixn: Interaction[Madeline],
        connection: app_commands.Transform[Connection, ConnectionTransformer],
        direction: DIRECTION | None = None,
        hidden: bool | None = None,
        bidirectional: bool = False,
    ):
        """
        Update a connection between two rooms in the database.

        Parameters
        ----------
        connection : Connection
            The connection to update.
        direction : str, optional
            The new direction of the connection.
        hidden : bool, optional
            Whether the connection is hidden (default is False).
        bidirectional : bool, optional
            Whether to update the connection bidirectionally (default is False).
        """
        updates = {
            "direction": direction,
            "hidden": hidden,
        }
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            return await ixn.send("No updates provided.", ephemeral=True)

        for key, value in updates.items():
            setattr(connection, key, value)

        saves = [connection]
        if bidirectional:
            reverse = connection.reversed
            for key, value in updates.items():
                if key == "direction":
                    value = FLIP_DIRECTION[value]
                setattr(reverse, key, value)
            saves.append(reverse)
        await self.bot.cache.get_cache(Connection).write_many(saves)
        return await ixn.send(f"Updated `{connection}` in the database.")

    @app_commands.command(name="list")
    async def connection_list(
        self, ixn: Interaction[Madeline], room: app_commands.Transform[Room, RoomTransformer] = None
    ):
        """
        List all connections in the cache.

        Parameters
        ----------
        room : Room, optional
            The room to filter connections by (default is None, which lists all connections).
        """
        connections = ixn.client.cache.get_cache(Connection).get_many(room=room or MISSING)
        if not connections:
            return await ixn.send("No connections found in the cache.")

        cpaginator = TablePaginator(
            headers=["Room", "Connected To", "Direction", "Hidden"],
            rows=[[c.room, c.connected_to, c.direction, "Yes" if c.hidden else "No"] for c in connections],
            max_rows_per_page=8,
        )
        await ixn.send(content=cpaginator.pages[0], view=TablePaginatorView(author=ixn.user, paginator=cpaginator))

    @app_commands.command(name="remove")
    async def connection_remove(
        self,
        ixn: Interaction[Madeline],
        connection: app_commands.Transform[Connection, ConnectionTransformer],
        bidirectional: bool = False,
    ):
        """
        Remove a connection between two rooms in the database.

        Parameters
        ----------
        connection : Connection
            The connection to remove.
        bidirectional : bool, optional
            Whether to remove the connection bidirectionally, if it exists (default is False).
        """
        reverse = None
        if bidirectional:
            reverse = connection.reversed
        removed = [connection, reverse]
        await self.bot.cache.get_cache(Connection).delete_many(removed)
        return await ixn.send(
            f"Removed the **`{connection}`** connection from the database."
            + (f"\nAlso removed the **`{reverse}`** connection." if reverse else "")
        )


class DatabaseMgmtCog(DebugCog, name="database"):
    """Commands for database management."""

    @app_commands.command(name="view-schema")
    async def database_view_schema(self, ixn: Interaction[Madeline], table_name: str = ""):
        """
        View the schema of a table in the database.
        """
        async with ixn.client.db.cursor() as c:
            await c.execute(
                "SELECT sql FROM sqlite_master WHERE type='table'" + (" AND name=?" if table_name else ""),
                (table_name,) if table_name else (),
            )
            schema = await c.fetchall()

        if not schema:
            return await ixn.send(f"Table `{table_name}` not found in the database.", ephemeral=True)

        schema_list = "\n".join([f"{s[0]}" for s in schema])
        return await ixn.send(f"```sql\n{schema_list}```")

    @app_commands.command(name="reset")
    async def database_reset(self, ixn: Interaction[Madeline]):
        """
        Reset the database by dropping all tables and recreating them.
        """
        log.log(LOCAL_DEBUG, "Resetting database.")
        c = DPyUtils.Confirmation(ixn)
        await ixn.send(
            "Are you sure you want to reset the database? This will delete all data.", view=c, ephemeral=True
        )
        if not await c.run():
            return await ixn.edit_original_response(content="Database reset cancelled.", view=None)
        log.log(LOCAL_DEBUG, "Resetting database confirmed.")
        await ixn.edit_original_response(content="Resetting database...", view=None)
        log.log(LOCAL_DEBUG, "Setting up database.")
        await self.bot.setup_db(reset=True)
        return await ixn.edit_original_response(content="Database has been reset.")


async def setup(bot: Madeline):
    await bot.add_cog(ZoneMgmtCog(bot))
    await bot.add_cog(RoomMgmtCog(bot))
    await bot.add_cog(PlayerMgmtCog(bot))
    await bot.add_cog(ConnectionMgmtCog(bot))
    await bot.add_cog(DatabaseMgmtCog(bot))
