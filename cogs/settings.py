from discord import Interaction, app_commands
from discord.ext import commands

from madlib import Actions, Madeline, Player, RoommateTransformer, is_game_channel
from madlib.config import COMMAND_GUILDS


class SettingsCog(commands.Cog):
    """Commands for players to manage their settings and preferences."""

    def __init__(self, bot: Madeline):
        self.bot = bot

    @app_commands.command(name="follow")
    @app_commands.guild_only()
    @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def follow(
        self,
        ixn: Interaction[Madeline],
        target: app_commands.Transform[Player, RoommateTransformer(Actions.FOLLOW)] = None,
    ):
        """
        Follow a player around.

        Parameters
        ----------
        target : Player
            The player to follow.
        """
        player = await Player.from_interaction(ixn)
        old_following = player.following

        if not target:
            if player.following:
                player.following = None
                await player.save()
                return await ixn.send(f"*You have stopped following **{old_following.pretty_name}**.*")
            else:
                return await ixn.send("*You are not currently following anyone.*", ephemeral=True)

        if target.following == player:
            return await ixn.send(f"*You can't follow **{target}** because they are following you.*", ephemeral=True)

        await ixn.response.defer(thinking=True)

        player.following = target
        await player.save()

        await target.send(f"***{player.pretty_name}** is now following you.*", fallback=ixn)
        old_follow_text = ""
        if old_following:
            await old_following.send(f"***{player.pretty_name}** has stopped following you.*", fallback=ixn)
            old_follow_text = f"You have stopped following **{old_following.pretty_name}**. "
        return await ixn.send(f"*{old_follow_text}You are now following **{target.pretty_name}**.*")

    @app_commands.command(name="notifications")
    @app_commands.guild_only()
    @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def notifications(self, ixn: Interaction[Madeline], enable: bool = None):
        """
        Set your notification preferences.

        Parameters
        ----------
        enable : bool
            Enable (True) or disable (False) notifications. Omitting this parameter will show your current notification status.
        """
        player = await Player.from_interaction(ixn)
        if enable is None:
            return await ixn.send(
                f"Notifications are currently {'en' if player.notifications_enabled else 'dis'}abled."
            )

        player.notifications_enabled = enable
        await player.save()
        return await ixn.send(f"Notifications have been {'en' if enable else 'dis'}abled.")

    @app_commands.command(name="appearance")
    @app_commands.guild_only()
    @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def appearance(self, ixn: Interaction[Madeline], new_appearance: str = None):
        """
        Set your appearance.

        Parameters
        ----------
        new_appearance : str
            Your player's new appearance.
        """
        player = await Player.from_interaction(ixn)
        if not new_appearance:
            return await ixn.send(f"Current appearance for **{player}**: '{player.appearance}'")

        old_appearance = player.appearance
        player.appearance = new_appearance
        await player.save()

        await player.location.alert(
            f"***{player.pretty_name}** has changed their appearance from *`{old_appearance}`* to *`{new_appearance}`*.",
            excludes=[player],
        )
        return await ixn.send(f"*Changed your appearance from *`{old_appearance}`* to *`{new_appearance}`*.")

    @app_commands.command(name="action")
    @app_commands.guild_only()
    @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def action(self, ixn: Interaction[Madeline], new_action: str = None):
        """
        Set your action text.

        Parameters
        ----------
        new_action : str
            Your player's new action text.
        """
        player = await Player.from_interaction(ixn)
        if not new_action:
            return await ixn.send(f"Current action text for **{player.pretty_name}**: '{player.action}'")

        old_action = player.action
        player.action = new_action
        await player.save()

        await player.location.alert(
            f"***{player.pretty_name}** has changed their action text from *`{old_action}`* to *`{new_action}`*.",
            excludes=[player],
        )
        return await ixn.send(f"*Changed your action text from *`{old_action}`* to *`{new_action}`*.")

    @app_commands.command(name="subtle")
    @app_commands.guild_only()
    @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def subtle(self, ixn: Interaction[Madeline], new_subtle: str = None):
        """
        Set your subtle text.

        Parameters
        ----------
        new_subtle : str
            Your player's new subtle text.
        """
        player = await Player.from_interaction(ixn)
        if not new_subtle:
            return await ixn.send(f"Current subtle text for **{player.pretty_name}**: '{player.subtle}'")

        old_subtle = player.subtle
        player.subtle = new_subtle
        await player.save()

        return await ixn.send(f"*Changed your subtle text from *`{old_subtle}`* to *`{new_subtle}`*.")


async def setup(bot: Madeline):
    await bot.add_cog(SettingsCog(bot))
