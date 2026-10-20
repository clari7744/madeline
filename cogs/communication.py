import random
import re
from datetime import timedelta
from logging import getLogger

import DPyUtils
from discord import Interaction, Message, app_commands
from discord.ext import commands
from discord.utils import format_dt, utcnow

from madlib import (
    AdjacentRoomTransformer,
    Connection,
    Madeline,
    Player,
    PlayerTransformer,
    RoleplayMessage,
    SearchTerm,
    is_game_channel,
)
from madlib.config import GUILD_ID, LOCAL_DEBUG
from madlib.ui import EditRoleplayMessageModal

log = getLogger(__name__)


class CommunicationCog(commands.Cog):
    """
    Commands for players to communicate with each other
    """

    def __init__(self, bot: Madeline):
        self.bot = bot
        self.dialog_re = re.compile(r'"(.*?)"', flags=re.I | re.M)
        self.ctx_edit_roleplay_message = app_commands.ContextMenu(
            name="Edit Roleplay Message",
            callback=self.context_edit_roleplay_message,
        )
        self.ctx_delete_roleplay_message = app_commands.ContextMenu(
            name="Delete Roleplay Message",
            callback=self.context_delete_roleplay_message,
        )
        self.bot.tree.add_command(self.ctx_edit_roleplay_message)
        self.bot.tree.add_command(self.ctx_delete_roleplay_message)

    @app_commands.command(name="rp")
    @app_commands.guild_only()
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_game_channel)
    async def rp(self, ixn: Interaction[Madeline], message: str):
        """
        Send a roleplay message to the current room.

        Parameters
        ----------
        message : str
            The message to send.
        """
        # TODO: use a modal or something to permit multiline. emojis are gonna suck ass unfortunately
        await ixn.response.defer(thinking=True)
        player = await Player.from_interaction(ixn)

        await player.rp(ixn, message)

    @app_commands.command(name="eavesdrop")
    @app_commands.guild_only()
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_game_channel)
    @app_commands.rename(connection="room")
    async def eavesdrop(
        self, ixn: Interaction[Madeline], connection: app_commands.Transform[Connection, AdjacentRoomTransformer]
    ):
        """
        Eavesdrop on a nearby room's RP messages.

        Parameters
        ----------
        connection : Connection
            The adjacent room to eavesdrop on.
        """
        # all messages sent in ROOM in the last 20 minutes, sorted by last_updated, oldest-first
        await ixn.response.defer(thinking=True)
        log.log(LOCAL_DEBUG, f"Eavesdropping on {connection.connected_to} from {connection.room.room_name}")
        all_msgs = self.bot.cache.get_cache(RoleplayMessage).get_many(
            sent_in_room=SearchTerm(connection.connected_to, ignore_case=True),
            message_type="rp",
            predicate=lambda msg: (utcnow() - msg.last_updated) < timedelta(minutes=20),
        )

        rp_unique: dict[int, RoleplayMessage] = {}
        for msg in all_msgs:
            rp_unique[msg.original_message_id] = msg
        eavesdroppable = sorted(rp_unique.values())

        if not eavesdroppable:
            return await ixn.send(
                f"No RP messages found in {connection.connected_to.room_name} within the last 20 minutes."
            )
        log.log(
            LOCAL_DEBUG,
            f"Found {len(eavesdroppable)} RP messages in {connection.connected_to.room_name} to eavesdrop on.",
        )
        # await ixn.send(
        #     f"Found {len(eavesdroppable)} RP message{'' if len(eavesdroppable) == 1 else 's'} in {connection.connected_to.room_name} from the last 20 minutes:"
        # )
        for msg in eavesdroppable:
            txt = "ERROR: NOT FOUND"
            try:
                original_msg = await msg.sent_by.channel.fetch_message(msg.original_message_id)
                match = self.dialog_re.findall(original_msg.content)
                if not match:  # no dialogue in this message!
                    continue
                txt = "\n".join(f'"{d}"' for d in match)
            except Exception as e:
                log.error(f"Failed to fetch original message for eavesdrop: {e}", exc_info=e)
            await ixn.send(
                f"*{format_dt(msg.last_updated)} - **{random.choice((msg.sent_by.pretty_name, '[REDACTED]'))}** said:* {txt}",
            )

    @app_commands.command(name="whisper")
    @app_commands.guild_only()
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_game_channel)
    async def whisper(
        self, ixn: Interaction[Madeline], target: app_commands.Transform[Player, PlayerTransformer], message: str
    ):
        """
        Send a private message to a specific player in the same room (alerts others that you're whispering).

        Parameters
        ----------
        target : Player
            The target Player to whisper to.
        message : str
            The message to whisper.
        """
        # if this command takes more than 3 seconds, uncomment the deferral
        # it's commented rn because it will make the ephemeral error messages no longer ephemeral
        # await ixn.response.defer(thinking=True)

        player = await Player.from_interaction(ixn)

        roommate, msg = player.is_roommate(target, action="whisper to")
        if not roommate:
            return await ixn.send(msg, ephemeral=True)

        # if this command starts taking more than 3 seconds to respond,
        # COMMENT OUT THIS ONE #
        # and uncomment the above deferral
        await ixn.response.defer(thinking=True)

        await player.rp(ixn, message, message_type="whisper", target=target)

    @app_commands.command(name="shout")
    @app_commands.guild_only()
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_game_channel)
    async def shout(self, ixn: Interaction[Madeline], message: str):
        """
        Broadcast the given dialogue to the occupied and adjacent rooms.

        Parameters
        ----------
        message : str
            The message to broadcast.
        """
        await ixn.response.defer(thinking=True)
        player = await Player.from_interaction(ixn)
        await player.rp(ixn, message, message_type="shout")

    @app_commands.guild_only()
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_game_channel)
    async def context_edit_roleplay_message(self, ixn: Interaction[Madeline], message: Message):
        player = await Player.from_interaction(ixn)
        rpm_cache = self.bot.cache.get_cache(RoleplayMessage)
        example_msg = rpm_cache.get_first(original_message_id=message.id)
        if example_msg is None:
            raise app_commands.CheckFailure("This is not a roleplay message.", ephemeral=True)
        await ixn.response.send_modal(EditRoleplayMessageModal(player, message, example_msg.message_type))

    @app_commands.guild_only()
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_game_channel)
    async def context_delete_roleplay_message(self, ixn: Interaction[Madeline], message: Message):
        player = await Player.from_interaction(ixn)
        rpm_cache = ixn.client.cache.get_cache(RoleplayMessage)
        found_messages = rpm_cache.get_many(original_message_id=message.id, sent_by=player)
        if not found_messages:
            raise app_commands.CheckFailure("This is not a roleplay message.", ephemeral=True)
        c = DPyUtils.Confirmation(ixn, timeout=30, ephemeral=True)
        await ixn.send("Are you sure you want to delete this message?", view=c, ephemeral=True)
        if not await c.run():
            return

        await message.delete()
        for msg in found_messages:
            try:
                to_delete = await msg.sent_to.channel.fetch_message(msg.received_message_id)
                await to_delete.delete()
            except Exception as e:
                log.warning(f"Failed to delete message {msg.received_message_id} for {msg.sent_to.pretty_name}: {e}")
        await rpm_cache.delete_many(found_messages)
        await ixn.edit_original_response(content="Roleplay message deleted.", view=None, embed=None)


async def setup(bot: Madeline) -> None:
    await bot.add_cog(CommunicationCog(bot))
