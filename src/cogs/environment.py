from logging import getLogger
from typing import Literal

from discord import Embed, Interaction, app_commands
from discord.ext import commands

from madlib import (
    Actions,
    AdjacentRoomTransformer,
    Connection,
    Madeline,
    Player,
    RoommateTransformer,
    is_game_channel,
)
from madlib.config import COMMAND_GUILDS, LOCAL_DEBUG
from madlib.helpers import FLIP_DIRECTION

log = getLogger(__name__)


@app_commands.guild_only()
# @app_commands.guilds(*COMMAND_GUILDS)
@app_commands.check(is_game_channel)
class CheckGroup(app_commands.Group, name="check", description="Check various things."):
    """
    Group of commands for checking various things.
    """

    room = app_commands.Group(name="room", description="Check the current room.")

    @room.command(name="simple")
    async def check_room_simple(self, ixn: Interaction[Madeline]):
        """
        Check the current room (simple).

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The interaction that triggered the command.
        """
        player = await Player.from_interaction(ixn)
        room = player.location

        return await ixn.send(
            embed=Embed(
                title=f"{room} | {room.zone}",
                color=room.resolved_color,
            ).add_field(
                name="Connected Rooms",
                value="\n".join(f"{c.connected_to} ({c.direction})" for c in room.get_connected()) or "None (???)",
            )
        )

    @room.command(name="detailed")
    async def check_room_detailed(self, ixn: Interaction[Madeline]):
        """
        Check the current room (detailed).

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The interaction that triggered the command.
        """
        player = await Player.from_interaction(ixn)
        room = player.location

        return await ixn.send(
            embed=Embed(
                title=f"{room} | {room.zone}",
                description=room.description,
                color=room.resolved_color,
            ).add_field(
                name="Connected Rooms",
                value="\n".join(f"{c.connected_to} ({c.direction})" for c in room.get_connected()) or "None (???)",
            )
        )

    people = app_commands.Group(name="people", description="Check the people in the current room.")

    @people.command(name="simple")
    async def check_people_simple(self, ixn: Interaction[Madeline]):
        """
        Check the people in the current room (simple).

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The interaction that triggered the command.
        """
        player = await Player.from_interaction(ixn)
        room = player.location
        members = room.get_members()

        return await ixn.send(
            embed=Embed(
                title=f"People in {room}",
                color=room.resolved_color,
                description="\n".join(p.pretty_name for p in members) or "You're the only one here.",
            )
        )

    @people.command(name="detailed")
    async def check_people_detailed(self, ixn: Interaction[Madeline]):
        """
        Check the people in the current room (detailed).

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The interaction that triggered the command.
        """
        player = await Player.from_interaction(ixn)
        room = player.location

        members = room.get_members(excludes=[player])
        embed = Embed(
            title=f"People in {room}",
            color=room.resolved_color,
            description="" if members else "You're the only one here.",
        )
        for p in members:
            embed.add_field(
                name=p.pretty_name,
                value=f"**Full Name**: {p.full_name}\n**Appearance**: {p.appearance}\n**Action**: {p.action}",
            )
        return await ixn.send(embed=embed)


class EnvironmentCog(commands.Cog):
    """
    Commands for players to interact with their environment
    """

    def __init__(self, bot: Madeline):
        self.bot = bot

    check = CheckGroup()

    @app_commands.command(name="look-at")
    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def look_at(
        self,
        ixn: Interaction[Madeline],
        target: app_commands.Transform[Player, RoommateTransformer(Actions.LOOK_AT)],
        level: Literal["general", "subtle"],
    ):
        """
        Look at a player in the same room.

        Parameters
        ----------
        target : Player
            The player to look at.
        level : Literal["general", "subtle"]
            The attributes to show.
        """
        player = await Player.from_interaction(ixn)

        await ixn.response.defer(thinking=True)

        await target.send(f"***{player.pretty_name}** looks at you (level: {level}).*", fallback=ixn)
        title = f"Looking at {target.pretty_name}"
        description = (
            f"**Full Name:** {target.full_name}\n**Appearance:** {target.appearance}\n**Action:** {target.action}"
        )
        if level == "subtle":
            title = f"Taking a closer look at {target.pretty_name}"
            description += f"\n**Subtle:** {target.subtle}"
        return await ixn.send(
            embed=Embed(
                title=title,
                description=description,
                color=target.location.resolved_color,
            )
        )

    @app_commands.command(name="go-to")
    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    @app_commands.rename(connection="room")
    async def go_to(
        self, ixn: Interaction[Madeline], connection: app_commands.Transform[Connection, AdjacentRoomTransformer]
    ):
        """
        Go to a connected room.

        Parameters
        ----------
        connection : Connection
            The name of the room to go to.
        """
        await ixn.response.defer(thinking=True)
        player = await Player.from_interaction(ixn)
        before = connection.room
        after = connection.connected_to

        if before != player.location:
            raise ValueError(
                f"### !!! Player {player} is not in the room {before}, but in {player.location}. !!!\nThis means that something about the converter broke."
            )

        jiggle = lambda: after.alert(  # noqa: E731
            (
                f"*The handle jiggles, as if somebody is trying to open the door to the **{before}** from the other side...unfortunately, this door is locked.*"
                if not connection.hidden
                else "*You hear a noise within the walls, but it only lasts a moment.*"
            ),
            excludes=[player],
        )
        hd = "You found a hidden door! However, y" if connection.hidden else "Y"
        if before.locked:
            await jiggle()
            return await ixn.send(f"*{hd}ou cannot leave **{before}** because it is locked.*", ephemeral=True)
        if after.locked:
            await jiggle()
            return await ixn.send(f"*{hd}ou cannot enter **{after}** because it is locked.*", ephemeral=True)
        # THIS IS IN A DUMB AND STUPID ORDER !
        # THE ALERTS HAPPEN BEFORE TEH ACTIONS !
        # IF YOU WANT TO KNOW WHY LOOK AT https://discord.com/channels/1555644504181317805/1555644505108123738/1561641548184289290

        # Let the rooms know that the player has left/entered
        btext = before.room_name
        atext = after.room_name
        if connection.hidden:
            btext = f"somewhere in the {FLIP_DIRECTION[connection.direction]}"
            atext = f"somewhere in the {connection.direction}"

        await before.alert(f"***{player.pretty_name}** leaves to **{atext}**.*", excludes=[player])
        await after.alert(f"***{player.pretty_name}** enters from **{btext}**.*", excludes=[player])

        # Recursively move followers
        # The top level is moved first
        followers = await player.get_followers(recursive=not connection.hidden)
        if connection.hidden:
            log.log(LOCAL_DEBUG, f"Breaking follow for {len(followers)} followers of {self} to {after}\n{followers}")
        else:
            log.log(LOCAL_DEBUG, f"Moving {len(followers)} followers of {self} to {after}\n{followers}")
        follow_text = ""
        for follower in followers:
            leader = follower.following
            if connection.hidden:
                follower.following = None
                await follower.send(
                    f"*You couldn't see where **{leader.pretty_name}** went, so you stopped following them.*",
                    fallback=ixn,
                )
                follow_text += f"\n***{follower.pretty_name}** is no longer following you.*"
            else:
                # Follower leaves their previous room
                follower.location = after
                await before.alert(
                    f"***{follower.pretty_name}** leaves to **{after}**, following **{leader.pretty_name}**.*",
                    excludes=[follower, leader, player],
                )
                # The person they're following is told about it, but only if they're not the root player
                # (root player has the special "follower.* follows")
                if leader != player:
                    await leader.send(f"***{follower.pretty_name}** follows you to **{after}**.*", fallback=ixn)
                # The top-chain is told
                follow_text += f"\n***{follower.pretty_name}** follows.*"
                # It is confirmed to them
                await follower.send(f"*You follow **{leader.pretty_name}** to **{after}**.*", fallback=ixn)
                # The new room is told about it
                await after.alert(
                    f"***{follower.pretty_name}** enters from **{before}**, following **{leader.pretty_name}**.*",
                    excludes=[follower, leader, player],
                )

        # Move player and their followers
        was_following = await player.move_to(after)
        await self.bot.cache.get_cache(Player).write_many(followers)  # Update the cache and database

        # Let the player know that they've moved
        msg = f"You move **{connection.direction}** from **{before}** to **{after}**."

        # if a follow was broken with this move, inform both parties
        if was_following:
            await was_following.send(f"***{player.pretty_name}** is no longer following you.*", fallback=ixn)
            msg += f" You are no longer following **{was_following.pretty_name}**."

        await ixn.send(f"*{msg}*{follow_text}")

        # Room description
        await player.send(
            "",
            embed=Embed(
                title=f"Room: {after}",
                description=f"{' | '.join(p.emoji if p.emoji else p.short_name for p in after.get_members())}\n{after.description}",
                color=after.resolved_color,
            ).add_field(
                name="Connected Rooms",
                value="\n".join(f"{c.connected_to} ({c.direction})" for c in after.get_connected()) or "None (???)",
            ),
            fallback=ixn,
        )


async def setup(bot: Madeline):
    await bot.add_cog(EnvironmentCog(bot))
