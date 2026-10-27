import random
import re
from logging import getLogger

from discord import Interaction, Message, app_commands
from discord.ext import commands
from discord.utils import format_dt, utcnow
from DPyUtils import Confirmation, strfdur

from madlib import (
    Actions,
    AdjacentRoomTransformer,
    Connection,
    Madeline,
    Player,
    RoleplayMessage,
    Room,
    RoommateTransformer,
    SearchTerm,
    is_game_channel,
    strip_content_header,
)
from madlib.config import COMMAND_GUILDS, EAVESDROP_COOLDOWN, EAVESDROP_TIME_LIMIT, LOCAL_DEBUG
from madlib.helpers import EavesdropCooldown
from madlib.ui import EditRoleplayMessageModal

log = getLogger(__name__)


class CommunicationCog(commands.Cog):
    """
    Commands for players to communicate with each other
    """

    def __init__(self, bot: Madeline):
        self.bot = bot
        self.dialog_re = re.compile(r'"(.*?)"', flags=re.I | re.M)
        # 1 use per EAVESDROP_COOLDOWN per room
        self.eavesdrop_cd = commands.CooldownMapping[Room].from_cooldown(
            1, EAVESDROP_COOLDOWN.total_seconds(), lambda room: room.room_name
        )

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

    @app_commands.command(name="eavesdrop")
    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
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

        if wait := self.eavesdrop_cd.update_rate_limit(connection.connected_to):
            raise EavesdropCooldown(wait, connection.connected_to, self.eavesdrop_cd._cooldown)
        # all messages sent in ROOM in the last EAVESDROP_TIME_LIMIT, sorted by last_updated, oldest-first
        await ixn.response.defer(thinking=True)
        player = await Player.from_interaction(ixn)
        log.log(
            LOCAL_DEBUG,
            f"{player} is eavesdropping on {connection.connected_to} from {connection.room}",
        )
        all_msgs = self.bot.cache.get_cache(RoleplayMessage).get_many(
            sent_in_room=SearchTerm(connection.connected_to, ignore_case=True),
            message_type="rp",
            predicate=lambda msg: (utcnow() - msg.last_updated) < EAVESDROP_TIME_LIMIT,
        )

        rp_unique: dict[int, RoleplayMessage] = {}
        for rp_msg in all_msgs:
            rp_unique[rp_msg.original_message_id] = rp_msg
        eavesdroppable = sorted(rp_unique.values())

        if not eavesdroppable:
            return await ixn.send(
                f"No RP messages found in **{connection.connected_to}** within the last {strfdur(EAVESDROP_TIME_LIMIT)}."
            )
        log.log(
            LOCAL_DEBUG,
            f"Found {len(eavesdroppable)} theoretically-eavesdroppable RP messages in {connection.connected_to} to eavesdrop on.",
        )
        # await ixn.send(
        #     f"Found {len(eavesdroppable)} RP message{'' if len(eavesdroppable) == 1 else 's'} in {connection.connected_to.room_name} from the last {strfdur(EAVESDROP_TIME_LIMIT)}:"
        # )
        for rp_msg in eavesdroppable:
            log.log(
                LOCAL_DEBUG,
                f"RP message from {rp_msg.sent_by.pretty_name} in {rp_msg.sent_in_room}: {rp_msg.message_content}",
            )
            txt = strip_content_header(rp_msg.message_content)
            match = self.dialog_re.findall(rp_msg.message_content)
            log.log(
                LOCAL_DEBUG,
                f"Found {len(match)} dialogue lines in RP message {rp_msg.original_message_id}: {match}",
            )
            if match:
                txt = "\n".join(f'"{d}"' for d in match)

            await ixn.send(
                f"*{format_dt(rp_msg.last_updated)} - **{random.choice((rp_msg.sent_by.pretty_name, '[REDACTED]'))}** said:* {txt}",
            )
        await ixn.send(f"End of RP messages from **{connection.connected_to}**.", ephemeral=True)

    @app_commands.command(name="rp")
    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
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
        player = await Player.from_interaction(ixn)
        await player.rp(ixn, message)

    @app_commands.command(name="whisper")
    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def whisper(
        self,
        ixn: Interaction[Madeline],
        target: app_commands.Transform[Player, RoommateTransformer(Actions.WHISPER)],
        message: str,
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
        player = await Player.from_interaction(ixn)
        await player.rp(ixn, message, message_type="whisper", target=target)

    @app_commands.command(name="shout")
    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def shout(self, ixn: Interaction[Madeline], message: str):
        # TODO: shout to specific room
        """
        Broadcast the given dialogue to the occupied and adjacent rooms.

        Parameters
        ----------
        message : str
            The message to broadcast.
        """
        player = await Player.from_interaction(ixn)
        await player.rp(ixn, message, message_type="shout")

    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def context_edit_roleplay_message(self, ixn: Interaction[Madeline], message: Message):
        player = await Player.from_interaction(ixn)
        rpm_cache = self.bot.cache.get_cache(RoleplayMessage)
        log.log(LOCAL_DEBUG, f"Context menu edit roleplay message invoked by {player} on message {message.id}")
        example_msg = rpm_cache.get_first(original_message_id=message.id)
        if example_msg is None:
            raise app_commands.CheckFailure("This is not a roleplay message.")
        await ixn.response.send_modal(EditRoleplayMessageModal(player, message, example_msg.message_type))

    @app_commands.guild_only()
    # @app_commands.guilds(*COMMAND_GUILDS)
    @app_commands.check(is_game_channel)
    async def context_delete_roleplay_message(self, ixn: Interaction[Madeline], message: Message):
        player = await Player.from_interaction(ixn)
        log.log(LOCAL_DEBUG, f"Context menu delete roleplay message invoked by {player} on message {message.id}")
        rpm_cache = ixn.client.cache.get_cache(RoleplayMessage)
        found_messages = rpm_cache.get_many(original_message_id=message.id, sent_by=player)
        if not found_messages:
            raise app_commands.CheckFailure("This is not a roleplay message.")
        c = Confirmation(ixn, timeout=30, ephemeral=True)
        await ixn.send("Are you sure you want to delete this message?", view=c, ephemeral=True)
        if not await c.run():
            return

        await message.delete()
        for msg in found_messages:
            if msg.received_message_id == 0:
                log.log(
                    LOCAL_DEBUG,
                    f"Roleplay message {msg.original_message_id} has no received_message_id, skipping deletion (user was alone in channel at time of sending).",
                )
                continue
            try:
                to_delete = await msg.sent_to.channel.fetch_message(msg.received_message_id)
                await to_delete.delete()
            except Exception as e:
                log.warning(f"Failed to delete message {msg.received_message_id} for {msg.sent_to.pretty_name}: {e}")
        await rpm_cache.delete_many(found_messages)
        await ixn.edit_original_response(content="Roleplay message deleted.", view=None, embed=None)


async def setup(bot: Madeline) -> None:
    await bot.add_cog(CommunicationCog(bot))
