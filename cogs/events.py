from datetime import datetime
from logging import getLogger

import aiosqlite
from discord import ChannelType, HTTPException, Interaction, Member, Message, TextChannel, app_commands
from discord.ext import commands

from madlib import Madeline, Player, SearchTerm
from madlib.config import TYPING_CATEGORIES, TYPING_EXCLUDE_CHANNELS
from madlib.transformers import FailedTransform

log = getLogger(__name__)


class Events(commands.Cog):
    """
    A Cog for handling various events.
    Error logging more or less borrowed from https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
    """

    def __init__(self, bot: Madeline) -> None:
        # Save the default handlers in case we have to unload this extension...
        self.original_command_error = bot.on_command_error
        self.original_app_error = bot.tree.on_error

        # Assign the new handlers to the bot...
        bot.on_command_error = self.on_command_error
        bot.tree.on_error = self.on_app_command_error

        self.bot = bot

    async def cog_unload(self) -> None:
        """Load the original error handlers back into the bot when this Cog unloads."""
        self.bot.on_command_error = self.original_command_error
        self.bot.tree.on_error = self.original_app_error

    async def send(
        self,
        content: str,
        /,
        context: commands.Context[Madeline] | Interaction[Madeline],
        ephemeral: bool = True,
    ) -> None:
        """Simple generic method for sending a response.

        This method catches and logs discord.HTTPExceptions.

        Parameters
        ----------
        content: str
            The content to send in the response.
        context: commands.Context | discord.Interaction
            The context or interaction surrounding the command or app command.
        ephemeral: bool
            Optional bool indicating whether the repsonse should attempted to be sent ephemerally. Defaults to True.
        """
        try:
            await context.send(content=content, ephemeral=ephemeral)
        except HTTPException as e:
            msg = "Ignoring HTTPException in %r for %r: %s\n\n"
            log.error(msg, self.send.__name__, self.__class__.__name__, e, exc_info=e)

    async def on_command_error(self, ctx: commands.Context[Madeline], error: commands.CommandError) -> None:
        """Prefix command error handler."""
        log.info(f"Command error handler called for {ctx.command} with error: {error}")

        # Don't continue if we have a command specific handler...
        if ctx.command and ctx.command.has_error_handler():
            return

        # Don't continue if we have a Cog error handler...
        elif ctx.cog and ctx.cog.has_error_handler():
            return

        error = getattr(error, "original", error)
        ignored = (commands.CommandNotFound, commands.NotOwner)
        # Don't continue if the error is in ignored...
        if isinstance(error, ignored):
            return

        # Example of handling some command errors...
        # If we don't handle the Exception we log it to console...
        elif isinstance(error, commands.NoPrivateMessage):
            await self.send("This command cannot be used in Private Messages.", context=ctx)
        elif isinstance(error, commands.DisabledCommand):
            await self.send("This command has been disabled by the owner.", context=ctx)
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, (aiosqlite.IntegrityError, aiosqlite.OperationalError)):
                await self.send(f"The database transaction failed: {error.original}", context=ctx)
                log.error(f"The database transaction failed: {error.original}", exc_info=error)
            else:
                await self.send(f"**This command received an unhandled exception:**\n\n{error}", context=ctx)
                log.error("Ignoring exception in command %r", ctx.command, exc_info=error)
        else:
            await self.send(f"**This command received an unhandled exception:**\n\n{error}", context=ctx)
            log.error("Ignoring exception in command %r", ctx.command, exc_info=error)

    async def on_app_command_error(
        self,
        ixn: Interaction[Madeline],
        error: app_commands.AppCommandError,
    ) -> None:
        """AppCommand error handler."""
        log.info(f"AppCommand error handler called for {ixn.command.qualified_name} with error: {error}")
        command = ixn.command

        # Default logging if the AppCommand is None...
        if command is None:
            await self.send(f"**This application received an unhandled exception:**\n\n{error}", context=ixn)
            log.error("Ignoring exception in command tree", exc_info=error)
            return

        # Don't continue if we have a command specific handler...
        if command.on_error:
            return

        # Example of responding to an error...
        if isinstance(error, app_commands.CommandOnCooldown):
            retry_after = error.cooldown.get_retry_after()
            await self.send(f"This command is on cooldown. Try again in {retry_after:.2f} seconds...", context=ixn)
        elif isinstance(error, app_commands.CommandNotFound):
            await self.send("This command was not found.", context=ixn)
        elif isinstance(error, app_commands.CommandInvokeError):
            if isinstance(error.original, (aiosqlite.IntegrityError, aiosqlite.OperationalError)):
                await self.send(f"The database transaction failed: {error.original}", context=ixn)
                log.error(f"The database transaction failed: {error.original}", exc_info=error)
            else:
                await self.send(f"**This command received an unhandled exception:**\n\n{error}", context=ixn)
                log.error("Ignoring exception in command %r", ixn.command, exc_info=error)
        elif isinstance(error, app_commands.CheckFailure):
            await self.send(f"Check failure: {error}", context=ixn)
        elif isinstance(error, FailedTransform):
            await self.send(f"{error}", context=ixn)
        else:
            # Respond to all unhandled errors as an example... Could be removed to show the default response from Discord.
            # All unhandled errors are also logged to console...
            await self.send(f"**This application received an unhandled exception:**\n\n{error}", context=ixn)
            log.error("Ignoring exception in command %r", command.name, exc_info=error)

    @commands.Cog.listener("on_message")
    async def dm_logs(self, message: Message):
        if message.channel.type == ChannelType.private:
            log.info(msg=f"DM from {message.author} to {message.channel}: {message.content}")

    @commands.Cog.listener("on_typing")
    async def notify_room_members(self, channel: TextChannel, user: Member, when: datetime):
        log.info(f"{user} is typing in {channel} at {when}")
        if (
            channel.category_id not in TYPING_CATEGORIES
            or channel.id in TYPING_EXCLUDE_CHANNELS
            or channel.type != ChannelType.text
            or user.bot
        ):
            return
        pcache = self.bot.cache.get_cache(Player)
        typer = await pcache.fetch(channel.id)
        notified = pcache.get_many(
            notifications_enabled=True,
            location=typer.location,
            channel=SearchTerm(channel, negative=True),
        )
        for player in notified:
            await player.send(
                f"<a:typing:1560111253509247076> {typer.short_name} is typing...", fallback=channel, delete_after=8
            )
            try:
                await player.channel.typing()
            except:
                log.warning(
                    f"Failed to send typing notification to {player} in {player.channel} ({player.channel_id})."
                )


async def setup(bot: Madeline):
    await bot.add_cog(Events(bot))
