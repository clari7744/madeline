from discord import Interaction, app_commands
from discord.ext import commands
from DPyUtils import _and, an

from madlib import Madeline, Player, PlayerTransformer, Room, RoomTransformer, SearchTerm
from madlib.config import GUILD_ID
from madlib.ui import DiceRollView


@app_commands.guild_only()
@app_commands.guilds(GUILD_ID)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.check(lambda ixn: ixn.client.is_owner(ixn.user))
class AdminCog(commands.GroupCog, name="admin"):
    """Admin commands for managing the game."""

    def __init__(self, bot: Madeline):
        self.bot = bot

    @app_commands.command(name="teleport")
    async def teleport(
        self,
        ixn: Interaction[Madeline],
        player: app_commands.Transform[Player, PlayerTransformer],
        room: app_commands.Transform[Room, RoomTransformer],
        bring_followers: bool = False,
    ):
        """
        Teleport a player to a different room.

        Parameters
        ----------
        player : Player
            The player to teleport.
        room : Room
            The room to teleport the player to.
        bring_followers : bool, optional
            Whether to bring the player's followers along (default is False).
        """
        await ixn.response.defer(thinking=True)

        was_following = await player.move_to(room)

        await player.send(
            f"*You have been teleported to {room}.{f' You are no longer following {was_following.pretty_name}.' if was_following else ''}*",
            fallback=ixn,
        )

        # only recurse if we're bringing everyone
        # if we're not bringing followers, then we only need to break the top level of the chain
        # i.e., anybody following a follower should *continue following the follower*
        # however, if we *are* bringing followers, then we gotta bring EVERYONE
        followers = await player.get_followers(recursive=bring_followers)
        for follower in followers:
            # FYI: if we bring followers and X follows Y who follows Z and Z was teleported, then it'll tell X
            # that Z was teleported, even though X is still following Y.
            # could be fixed with follower.following?
            message = f"***{follower.following.pretty_name}** was teleported to {room} and you were brought along.*"
            follower.location = room
            # message = f"***{player.pretty_name}** was teleported to {room} and you were brought along.*"
            if not bring_followers:
                follower.following = None  # Stop followers from following the teleported player
                message = f"***{player.pretty_name}** was teleported away, so you stopped following them*."
            await follower.send(message, fallback=ixn)
        await self.bot.cache.get_cache(Player).write_many(followers)  # Update the cache and database

        return await ixn.send(
            f"Teleported {player.pretty_name} to {room}.\n{f' Brought {len(followers)} followers along.' if bring_followers else ''}"
        )

    @app_commands.command(name="roll")
    async def roll(
        self,
        ixn: Interaction[Madeline],
        target: app_commands.Transform[Player, PlayerTransformer],
        check_type: str,
        goal: app_commands.Range[int, 1, 100],
        bonus_dice: int = 0,
        penalty_dice: int = 0,
    ):
        """
        Prompt a player to roll for a specific check and report the result.

        Parameters
        ----------
        target : Player
            The player to ask to roll.
        check_type : str
            The type of check to roll.
        goal : int
            The goal number to beat.
        bonus_dice : int, optional
            The number of bonus dice to roll (default is 0).
        penalty_dice : int, optional
            The number of penalty dice to roll (default is 0).
        """
        details = _and(
            *filter(
                bool,
                (
                    f"a goal of **{goal}**",
                    f"{bonus_dice} bonus dice" if bonus_dice > 1 else "a bonus die" if bonus_dice == 1 else "",
                    (
                        f"{penalty_dice} penalty dice"
                        if penalty_dice > 1
                        else "a penalty die" if penalty_dice == 1 else ""
                    ),
                ),
            )
        )

        await target.send(
            f"You have been prompted to roll **{an(check_type)} check** with {details}.",
            fallback=ixn,
            view=DiceRollView(
                triggered_by=ixn,
                target=target,
                check_type=check_type,
                goal=goal,
                bonus_dice=bonus_dice,
                penalty_dice=penalty_dice,
            ),
        )
        return await ixn.send(f"Prompted **{target}** to roll **{an(check_type)} check** with {details}.")

    loudspeaker = app_commands.Group(
        name="loudspeaker", description="Send a message to all players, a specific zone, room, or player."
    )

    @loudspeaker.command(name="all")
    async def loudspeaker_all(self, ixn: Interaction[Madeline], message: str):
        """
        Send a message to all players.

        Parameters
        ----------
        message : str
            The message to send.
        """
        recipients = ixn.client.cache.get_cache(Player).get_many()
        if not recipients:
            return await ixn.send("No players found (the player cache is empty?).")
        for recipient in recipients:
            await recipient.send(f"**Loudspeaker:** {message}", fallback=ixn)
        return await ixn.send(f"Sent loudspeaker message to all players: {message}")

    @loudspeaker.command(name="zone")
    async def loudspeaker_zone(self, ixn: Interaction[Madeline], zone: str, message: str):
        """
        Send a message to all players in the same zone.

        Parameters
        ----------
        zone : str
            The zone to send the message to.
        message : str
            The message to send.
        """
        recipients = ixn.client.cache.get_cache(Player).get_many(location__zone=SearchTerm(zone, fuzzy=True))
        if not recipients:
            return await ixn.send(f"No players found in zone {zone} (either that zone doesn't exist or is empty).")
        for recpient in recipients:
            await recpient.send(f"**Loudspeaker:** {message}", fallback=ixn)
        return await ixn.send(f"Sent loudspeaker message to all players in zone {zone}: {message}")

    @loudspeaker.command(name="room")
    async def loudspeaker_room(
        self, ixn: Interaction[Madeline], room: app_commands.Transform[Room, RoomTransformer], message: str
    ):
        """
        Send a message to all players in the same room.

        Parameters
        ----------
        message : str
            The message to send.
        """
        recipients = ixn.client.cache.get_cache(Player).get_many(location__room_name=room.room_name)
        if not recipients:
            return await ixn.send(f"No players found in room {room} (either that room doesn't exist or is empty).")
        for recipient in recipients:
            await recipient.send(f"**Loudspeaker:** {message}", fallback=ixn)
        return await ixn.send(f"Sent loudspeaker message to all players in room {room}: {message}")

    @loudspeaker.command(name="player")
    async def loudspeaker_player(
        self, ixn: Interaction[Madeline], player: app_commands.Transform[Player, PlayerTransformer], message: str
    ):
        """
        Send a message to a specific player.

        Parameters
        ----------
        player : Player
            The player to send the message to.
        message : str
            The message to send.
        """
        await player.send(f"**Loudspeaker:** {message}", fallback=ixn)
        return await ixn.send(f"Sent loudspeaker message to **{player}**: {message}")

    @app_commands.command(name="lock")
    async def lock(
        self, ixn: Interaction[Madeline], room: app_commands.Transform[Room, RoomTransformer], lock: bool = None
    ):
        """
        Lock or unlock a room.

        Parameters
        ----------
        room : Room
            The room to lock or unlock.
        lock : bool, optional
            True to lock the room, False to unlock it. If not specified,currently locked state will be shown.
        """
        if lock is None:
            return await ixn.send(f"**{room}** is currently {'' if room.locked else 'un'}locked.")

        room.locked = lock
        await room.save()
        await room.alert(f"**{room}** has been {'' if lock else 'un'}locked by an administrator.", fallback=ixn)
        return await ixn.send(f"{'L' if lock else 'Unl'}ocked **{room}**.")


async def setup(bot: Madeline):
    await bot.add_cog(AdminCog(bot))
