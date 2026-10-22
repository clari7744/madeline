from __future__ import annotations

from dataclasses import KW_ONLY, asdict, dataclass, field
from datetime import datetime
from logging import INFO, getLogger
from typing import TYPE_CHECKING, Optional

from discord import Interaction, Message, TextChannel
from discord.abc import Messageable
from discord.utils import MISSING, utcnow

from .config import LOCAL_DEBUG

if TYPE_CHECKING:
    from .helpers import DIRECTION, ROLEPLAY_MESSAGE_TYPE
    from .madeline import Madeline

log = getLogger(__name__)

DbValueT = str | int | bool  # The types that can be stored in the database


class Table:
    """A base class for all database tables."""

    table_name: str = None
    """The name of the table in the database."""
    primary_key: tuple[str] = None
    """The primary key(s) of the table."""
    composite_key: bool = False
    """Whether the primary key is composite (i.e., consists of multiple fields)."""
    foreign_keys: dict[str, type[Table]] = field(default_factory=dict)
    """A mapping of field names to the corresponding Table classes for foreign keys."""

    bot: Madeline

    def __init_subclass__(cls, *, primary_key: str | tuple[str], name: str = None):
        # LOG DOESN'T WORK BECAUSE THIS IS BEFORE UTILS.SETUP_LOGGING BECAUSE THIS RUNS ON IMPORT
        # IS THIS FIXABLE??? IDK AND IDC! JUST USE PRINT TO DEBUG IG
        # print(f"Initializing subclass {cls.__name__} of Table with name={name}, primary_key={primary_key}")

        cls.table_name = name or f"{cls.__name__.lower()}s"  # Player -> players
        cls.primary_key = primary_key if isinstance(primary_key, tuple) else (primary_key,)
        cls.composite_key = len(cls.primary_key) > 1
        cls.__hash__ = Table.__hash__

    def __hash__(self):
        return hash(self.get_primary_key_values())

    def __eq__(self, other: Table):
        if not isinstance(other, self.__class__):
            raise NotImplementedError(f"Cannot compare {self.__class__.__name__} with {other.__class__.__name__}")

        return all(getattr(self, key) == getattr(other, key) for key in self.primary_key)

    def __gt__(self, other: Table):
        if not isinstance(other, self.__class__):
            raise NotImplementedError(f"Cannot compare {self.__class__.__name__} with {other.__class__.__name__}")
        return str(self) > str(other)  # Compare string representations for ordering

    def __ge__(self, other: Table):
        if not isinstance(other, self.__class__):
            raise NotImplementedError(f"Cannot compare {self.__class__.__name__} with {other.__class__.__name__}")
        return str(self) >= str(other)  # Compare string representations for ordering

    def flatten(self) -> dict[str, DbValueT]:
        """
        Flatten the dataclass into a dictionary, converting nested Table objects to their primary key values.

        Returns
        -------
        dict[str, str|int|bool]
            A dictionary representation of the dataclass.
        """
        fields = asdict(self)
        for field_name, field_value in fields.items():
            log.log(LOCAL_DEBUG, f"Flattening field '{field_name}': {repr(field_value)}")
            table_item = getattr(self, field_name, None)
            # handle tables
            if isinstance(field_value, dict) and isinstance(table_item, Table):
                if table_item.composite_key:
                    # theoretically shouldn't happen because a composite key will never get set as a Table in our OOP design.
                    raise ValueError("Can't flatten a Table with a composite primary key into a single value.")
                fields[field_name] = field_value.get(table_item.primary_key[0])
            # handle objects like channels
            if isinstance(table_item, object) and hasattr(table_item, "id"):
                fields[field_name] = getattr(table_item, "id")

        return fields

    def get_primary_key_values(self) -> tuple[DbValueT]:
        """
        Get the values of the primary key fields for this instance.

        Returns
        -------
        tuple[str|int|bool]
            A tuple of primary key values.
        """
        values = []
        for key in self.primary_key:
            value = getattr(self, key)
            log.log(LOCAL_DEBUG, f"Getting primary key value for field '{key}': {repr(value)}")
            # unupack nested Table objects to their primary key values
            if isinstance(value, Table):
                if value.composite_key:
                    raise ValueError(
                        f"Cannot get primary key value for field '{key}' of type '{type(value).__name__}' because it has a composite primary key."
                    )
                value = value.get_primary_key_values()[0]
            # raise error if value is still an object, we don't really know how to handle a primary key of any other type
            elif not isinstance(value, (str, int, bool)):
                raise ValueError(f"Cannot get primary key value for field '{key}' of type '{type(value).__name__}'")
            values.append(value)
        return tuple(values)

    async def save(self, bot: Madeline = None):
        """
        Save the reference to the cache and the database.

        Parameters
        ----------
        bot : Madeline
            The bot instance to use for database access. If not provided, the instance's `bot` attribute will be used.

        Raises
        ------
        ValueError
            If neither the `bot` parameter nor the instance's `bot` attribute is set.
        """
        bot = bot or getattr(self, "bot", None)
        if bot is None:
            raise ValueError("Cannot save Table instance without a bot reference. Please set the 'bot' attribute.")
        self.bot = bot
        log.log(LOCAL_DEBUG, f"Saving {repr(self)}")
        return await self.bot.cache.get_cache(type(self)).write(self)

    async def delete(self):
        """
        Delete the reference from the cache and the database.

        Raises
        ------
        AttributeError
            If the instance's `bot` attribute is not set.
        """
        log.log(LOCAL_DEBUG, f"Deleting {repr(self)}")
        return await self.bot.cache.get_cache(type(self)).delete(self)


@dataclass
class Room(Table, primary_key="room_name"):
    """
    Represents a room in the game.

    Attributes
    ----------
    room_name : str
        The name of the room.
    zone : str
        The zone the room is in.
    description : str
        A description of the room.
    color : int
        The color of the room.
    locked : bool
        Whether the room is locked.
    """

    room_name: str
    """The name of the room."""
    _: KW_ONLY
    zone: str
    """The zone the room is in."""
    description: str
    """A description of the room."""
    color: int
    """The color of the room."""
    locked: bool
    """Whether the room is locked."""

    def __str__(self) -> str:
        return self.room_name

    async def send(self, message: str, **kwargs):
        """
        Send a message to all players in the room.

        Parameters
        ----------
        message : str
            The message to send.
        **kwargs : dict
            Additional keyword arguments to pass to the send method.
        """
        for member in self.get_members():
            await member.send(message, **kwargs)

    def get_members(self, excludes: Optional[list[Player]] = None) -> list[Player]:
        """
        Get a list of players currently in the room.

        Parameters
        ----------
        excludes : Optional[list[Player]], optional
            A list of players to exclude from the results (default is None).

        Returns
        -------
        list[Player]
            A list of players in the room.
        """
        player_cache = self.bot.cache.get_cache(Player)
        members = player_cache.get_many(location=self)
        if excludes:
            members = [member for member in members if member not in excludes]
        return members

    def get_connected(self, direction: DIRECTION = MISSING, include_hidden: bool = False) -> list[Connection]:
        """
        Get a list of rooms connected to this room.

        Parameters
        ----------
        direction : Optional[DIRECTIONS], optional
            The direction to filter the connected rooms by (default is None).
        include_hidden : bool, optional
            Whether to include hidden connections (default is False).

        Returns
        -------
        list[Connection]
            A list of connections with this room as the primary.
        """
        ccache = self.bot.cache.get_cache(Connection)
        # MISSING returns all, so missing direction or including hidden will return all that match the other attributes
        connections = ccache.get_many(room=self, direction=direction, hidden=MISSING if include_hidden else False)
        return connections

    async def alert(self, message: str, excludes: list[Player] = None):
        """
        Alert all players in the same room as a player of a player's action.

        Parameters
        ----------
        message : str
            The message to send to the room.
        excludes : Optional[list[Player]], optional
            A list of players to exclude from the alert (default is None).
        """
        excludes = excludes or []
        msgs: dict[Player, int] = {}
        for member in self.get_members(excludes=excludes):
            try:
                sent = await member.send(message)
                msgs[member] = sent.id
            except Exception as e:
                log.error(f"Failed to send alert to {member}: {e}", exc_info=e)
        return msgs

    async def alert_including_adjacent(self, message: str, excludes: list[Player] = None) -> None:
        """
        Alert all players in adjacent rooms of a player's action.

        Parameters
        ----------
        message : str
            The message to send to adjacent rooms.
        excludes : Optional[list[Player]], optional
            A list of players to exclude from the alert (default is None).
        """
        rooms = [self] + [conn.connected_to for conn in self.get_connected(include_hidden=True)]
        for room in rooms:
            await room.alert(message, excludes=excludes)


@dataclass
class Player(Table, primary_key="channel_id"):
    """
    Represents a player in the game.

    Attributes
    ----------
    channel_id : int
        The ID of the Discord channel associated with the player.
    short_name : str
        The short name of the player.
    full_name : str
        The full name of the player.
    emoji_id : int
        The ID of the player's icon.
    notifications_enabled : bool
        Whether the player has notifications enabled.
    location : Room
        The current location of the player.
    appearance : str
        The appearance description of the player.
    action : str
        The action description of the player.
    subtle : str
        The subtle description of the player.
    following : Player
        The player that this player is following.
    """

    channel_id: TextChannel
    """The ID of the Discord channel associated with the player."""
    _: KW_ONLY
    short_name: str
    """The short name of the player."""
    full_name: str
    """The full name of the player."""
    notifications_enabled: bool = True
    """Whether the player has notifications enabled."""
    emoji_id: Optional[int] = None
    """The ID of the player's icon."""
    appearance: Optional[str] = None
    """The appearance tag of the player."""
    action: Optional[str] = None
    """The action tag of the player."""
    subtle: Optional[str] = None
    """The subtle tag of the player."""
    location: Room
    """The current location of the player."""
    following: Optional[Player] = None
    """The player that this player is following, if any."""

    def __str__(self) -> str:
        return self.short_name

    @staticmethod
    async def from_interaction(ixn: Interaction[Madeline]):
        """
        Create an instance of the Player dataclass from a Discord interaction.

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The Discord interaction object.

        Returns
        -------
        Player
            An instance of the Player dataclass.
        """
        return await ixn.client.cache.get_cache(Player).fetch(ixn.channel_id)

    @property
    def emoji(self) -> str:
        """
        Get the emoji representation of the player.

        Returns
        -------
        str
            The emoji representation of the player, or an empty string if no emoji is set.
        """
        return f"<:icon:{self.emoji_id}>" if self.emoji_id else "[MISSING_ICON]"

    @property
    def pretty_name(self) -> str:
        """
        Get a pretty representation of the player's name, including their emoji if available.

        Returns
        -------
        str
            A string representation of the player's name with emoji if available.
        """
        return f"{self.emoji} {self.short_name}" if self.emoji_id else self.short_name

    @property
    def channel(self) -> TextChannel | None:
        """
        Get the Discord channel associated with the player.

        Returns
        -------
        TextChannel | None
            The Discord channel associated with the player, or None if the channel is not found.
        """
        channel = self.bot.get_channel(self.channel_id)
        if not isinstance(channel, TextChannel):
            log.error(f"Channel with ID {self.channel_id} is not a TextChannel (got {channel.__class__.__name__}).")
            return None

        return channel

    def is_roommate(self, other: Player, *, action: str) -> tuple[bool, str]:
        """
        Check if a player is not you but is in the same room as you.

        Parameters
        ----------
        other : Player
            The other player to check.

        Returns
        -------
        tuple[bool, str]
            A tuple containing a boolean indicating if the other player is in the same room and a message.
        """
        if not isinstance(other, Player):
            raise ValueError(f"Cannot compare Player with {type(other).__name__}")
        if self == other:
            return (False, f"*You can't {action} yourself.*")
        if self.location != other.location:
            return (False, f"*You can't {action} someone who isn't in the same room as you.*")
        return (True, "")

    async def send(self, message: str, *, fallback: Messageable | Interaction[Madeline] = None, **kwargs):
        """
        Send a message to the player's associated Discord channel.

        Parameters
        ----------
        message : str
            The message to send.
        fallback : Messagable | Interaction[Madeline]
            The Discord interaction object that triggered this or a channel. Required as a fallback.
        **kwargs : dict
            Additional keyword arguments to pass to the send method.

        Returns
        -------
        discord.Message
            The sent message object.
        """
        if (channel := self.channel) is not None:
            return await channel.send(message, **kwargs)
        if fallback is None:
            raise ValueError("No fallback provided for sending message.")
        return await fallback.send(
            f"Failed to send message to {self} because their channel was not found.\n## Original Message\n{message}",
            **kwargs,
        )

    async def _get_followers_recursive(self, known_followers: list[Player]) -> list[Player]:
        """
        Recursively get a set of players who are following this player.

        Parameters
        ----------
        known_followers : list[Player]
            A list of players already known to be followers, used to prevent infinite loops.

        Returns
        -------
        list[Player]
            A list of players following this player.
        """
        log.log(LOCAL_DEBUG, f"Recursively getting followers for {self} (known so far: {len(known_followers)})")
        followers = self.bot.cache.get_cache(Player).get_many(following=self)
        new_followers = [f for f in followers if f not in known_followers]
        log.log(LOCAL_DEBUG, f"Found {len(new_followers)} new followers for {self}")
        known_followers += new_followers
        for follower in new_followers:
            log.log(LOCAL_DEBUG, f"Recursing into follower {follower}")
            known_followers += [
                f for f in await follower._get_followers_recursive(known_followers) if f not in known_followers
            ]
        return known_followers

    async def get_followers(self, recursive=True) -> list[Player]:
        # TODO: i think this has to be recursive
        # if this is recursive then move_followers can be non-recursive.
        # maybe a flag?
        # anyways it needs recursion for admin teleport to recurse properly
        """
        Get a list of players who are following this player.

        Returns
        -------
        list[Player]
            A list of players following this player.
        """
        log.log(LOCAL_DEBUG, f"Getting followers for {self}")
        if recursive:
            return list(await self._get_followers_recursive([]))
        return self.bot.cache.get_cache(Player).get_many(following=self)

    async def move_to(self, new_location: Room) -> Player | None:
        """
        Move the player to a new location.

        Parameters
        ----------
        new_location : Room
            The new location to move the player to. Not validated.

        Returns
        -------
        Player | None
            The player that this player was following, if any. Returns None if the player was not following anyone.
        """
        self.location = new_location
        was_following = self.following
        if self.following is not None:
            self.following = None
        await self.bot.cache.get_cache(Player).write(self)  # Update the cache and database
        return was_following

    async def _edit_or_send_rp(
        self,
        ixn: Interaction[Madeline],
        msg: str,
        target: Player,
        src_message: Message,
        message_type: ROLEPLAY_MESSAGE_TYPE,
        edit: bool,
    ) -> RoleplayMessage:
        """
        Edit an existing roleplay message or send a new one to a target player.

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The interaction that triggered the command.
        msg : str
            The message to send or edit.
        target : Player
            The player to whom the message is being sent.
        src_message : Message
            The original message sent by the sender. Required to link the new or edited message to the original.
        message_type : ROLEPLAY_MESSAGE_TYPE
            The type of roleplay message (e.g., "whisper", "shout", "rp").
        edit : bool
            Whether to edit the original message if it exists.

        Returns
        -------
        RoleplayMessage
            The roleplay message object representing the sent or edited message.
        """
        if not edit:
            # we know we're not editing so just go for it o7
            sent_msg = await target.send(msg, fallback=ixn)
            return RoleplayMessage(
                original_message_id=src_message.id,
                received_message_id=sent_msg.id,
                sent_by=self,
                sent_to=target,
                sent_in_room=self.location,
                updated_at=utcnow().isoformat(),
                message_type=message_type,
                message_content=msg,
            )

        # We are in edit mode! #
        # try to get RoleplayMessage from cache that was sent to this user
        rp_msg = self.bot.cache.get_cache(RoleplayMessage).get_first(
            original_message_id=src_message.id,  # most important - it's the root msg
            sent_to=target,  # next-most important, finds the right one to edit
            sent_by=self,  # this is probably redundant but it's a good sanity check
        )

        # No message was originally sent to this user; let's send a new one
        if rp_msg is None:
            log.log(LOCAL_DEBUG, f"No existing RP message found for {target} to edit.")
            return await self._edit_or_send_rp(
                ixn, msg, target, src_message=src_message, message_type=message_type, edit=False
            )

        # Found original cross-posted message
        if rp_msg.received_message_id == 0:
            log.log(
                LOCAL_DEBUG,
                f"Found existing RP message for {target} to edit, but it has no received_message_id (user was alone in channel at time of sending).",
            )
            return await self._edit_or_send_rp(
                ixn, msg, target, src_message=src_message, message_type=message_type, edit=False
            )
        try:
            # Try to get and edit it!
            log.log(LOCAL_DEBUG, f"Found existing RP message for {target} to edit: {rp_msg}")
            received_msg = await target.channel.fetch_message(rp_msg.received_message_id)
            await received_msg.edit(content=msg)

            # At this point it should have succeeded, it's just in the try block..because
            log.log(LOCAL_DEBUG, f"Edited RP message for {target}: {msg}")
            rp_msg.last_updated = received_msg.edited_at or utcnow()
            rp_msg.message_content = msg
            return rp_msg
        except Exception as e:
            # It broke! Clean up...
            log.error(f"Failed to edit RP message for {target}: {e}", exc_info=e)
            # Delete the old RP message from the cache and database
            await rp_msg.delete()
            # Try again but don't edit
            return await self._edit_or_send_rp(
                ixn, msg, target, src_message=src_message, message_type=message_type, edit=False
            )

    async def rp(
        self,
        ixn: Interaction[Madeline],
        message: str,
        *,
        message_type: ROLEPLAY_MESSAGE_TYPE = "rp",
        src_message: Message = None,
        target: Optional[Player] = None,
    ) -> list[RoleplayMessage]:
        """
        Send or edit a roleplay message to one or more players in the same room.

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The interaction that triggered the command.
        message : str
            The message to send or edit.
        message_type : Literal["whisper", "shout", "rp"], optional
            The type of roleplay message (default is "rp").
        src_message : Message, optional
            The original message sent by the sender to edit & base the search for target messages on. Implies edit mode.
            If not provided or can't be found, a new message will be created (default is None).
        target : Optional[Player], optional
            The player to whom the message is being sent. Required for whispers (default is None).
        """
        rpm_cache = self.bot.cache.get_cache(RoleplayMessage)
        if not ixn.response.is_done():
            # MUST BE DEFERRED otherwise ixn.send returns an interactioncallbackresponse and i did not handle those properly
            await ixn.response.defer(thinking=True)

        you_say = f"**You:** {message}"
        targets: dict[Player, str] = {
            m: f"**{self.pretty_name}:** {message}" for m in self.location.get_members(excludes=[self])
        }
        addl_recipients: dict[Player, str] = {}

        if message_type == "whisper":
            # check for target or try to get from og for edit
            if target is None:
                if not src_message:
                    raise ValueError("Target must be specified for whispers.")
                old_rpm = rpm_cache.get_first(original_message_id=src_message.id, sent_by=self, message_type="whisper")
                if old_rpm is None:
                    raise ValueError("Target must be specified for whispers (+ could not be found in cache for edit).")
                target = old_rpm.sent_to

            you_say = f"*You whisper to **{target.pretty_name}**:* {message}"
            targets = {target: f"***{self.pretty_name}** whispers to you:* {message}"}
            addl_recipients = {
                m: f"***{self.pretty_name}** whispers something to **{target.pretty_name}***"
                for m in self.location.get_members(excludes=[self, target])
            }
        elif message_type == "shout":
            you_say = f"*You shout:* {message}"
            # Fix message to room members
            for t in targets:
                targets[t] = f"***{self.pretty_name}** shouts from {self.location}:* {message}"
            # Set message to adjacent room members based on hidden status
            for conn in self.location.get_connected(include_hidden=True):
                log.log(
                    LOCAL_DEBUG,
                    f"{self.short_name} is shouting to connected room {conn.connected_to} from {self.location}",
                )
                for mem in conn.connected_to.get_members(excludes=[self]):
                    rev = conn.reversed
                    loc = self.location.room_name
                    if rev is None:
                        log.warning(
                            f"Connection from {self.location} to {conn.connected_to} has no reversed connection!"
                        )
                    elif rev.hidden:
                        loc = f"somewhere to the {rev.direction}"

                    targets[mem] = f"***{self.pretty_name}** shouts from {loc}:* {message}"

        edit = False
        if src_message is not None:
            try:
                await src_message.edit(content=you_say)
                edit = True
                addl_recipients.clear()  # don't renotify for whisper edits
            except Exception as e:
                log.error(f"Failed to edit original message for {message_type} from {self}: {e}", exc_info=e)
                # delete any rp messages that used this original message id from the cache, we're starting from scratch
                await rpm_cache.delete_many(rpm_cache.get_many(original_message_id=src_message.id))
                src_message = None
            except Exception as e:  # rip
                log.error(f"Failed to delete old roleplay messages for {message_type} from {self}: {e}", exc_info=e)

        # src_message is either the message or None if it failed to edit.
        # if none treat is like new.
        if src_message is None:
            log.log(LOCAL_DEBUG, f"Sending new roleplay message for {message_type} from {self}")
            edit = False
            src_message = await ixn.send(you_say)

        rp_msgs: list[RoleplayMessage] = []
        for member, receives in targets.items():
            rp_msgs.append(
                await self._edit_or_send_rp(
                    ixn, receives, target=member, src_message=src_message, message_type=message_type, edit=edit
                )
            )

        for member, receives in addl_recipients.items():
            await member.send(receives, fallback=ixn)
        if not targets and not addl_recipients:
            log.log(LOCAL_DEBUG, f"{self} is alone in {self.location}, saving dummy message {src_message}")
            rp_msgs.append(
                RoleplayMessage(
                    original_message_id=src_message.id,
                    received_message_id=0,
                    sent_by=self,
                    sent_to=self,
                    sent_in_room=self.location,
                    updated_at=utcnow().isoformat(),
                    message_type=message_type,
                    message_content=message,
                )
            )
            log.log(
                LOCAL_DEBUG,
                f"Saved dummy message for {self} in {self.location} with original_message_id={src_message.id}",
            )

        log.log(
            INFO,
            f"Sent {len(rp_msgs)} roleplay messages for {message_type} from {self} to {[m.sent_to.short_name for m in rp_msgs]}",
        )
        await self.bot.cache.get_cache(RoleplayMessage).write_many(rp_msgs)
        return rp_msgs


@dataclass
class Connection(Table, primary_key=("room", "connected_to")):
    """
    Represents a connection between two rooms in the game.

    Attributes
    ----------
    room : Room
        The room from which the connection originates.
    connected_to : Room
        The room to which the connection leads.
    direction : DIRECTIONS
        The direction of the connection (north, south, east, west, up, down).
    hidden : bool
        Whether the connection is hidden.
    """

    room: Room
    """The room from which the connection originates."""
    connected_to: Room
    """The room to which the connection leads."""
    _: KW_ONLY
    direction: DIRECTION
    """The direction of the connection (north, south, east, west, up, down)."""
    hidden: bool
    """Whether the connection is hidden."""

    def __str__(self) -> str:
        return f"{self.room} -> {self.connected_to} ({self.direction})"

    @property
    def reversed(self) -> Connection | None:
        """
        Get the reversed connection (i.e., the connection from the connected room back to this room).

        Returns
        -------
        Connection | None
            The reversed connection if it exists, otherwise None.
        """
        ccache = self.bot.cache.get_cache(Connection)
        return ccache.get_first(room=self.connected_to, connected_to=self.room)


@dataclass
class RoleplayMessage(Table, name="roleplay_messages", primary_key=("original_message_id", "sent_to")):
    """
    Represents a roleplay message sent from one player to another.

    Attributes
    ----------
    original_message_id : int
        The ID of the original message sent by the sender.
    received_message_id : int
        The ID of the message received by the recipient.
    sent_by : Player
        The player who sent the message.
    sent_to : Player
        The player who received the message.
    sent_in_room : Room
        The room in which the message was sent.
    updated_at : str
        The timestamp of the last update to the message (in ISO, timezone-aware format).
    message_type : Literal["whisper", "shout", "rp"]
        The type of the roleplay message.
    message_content : str
        The content of the roleplay message.
    """

    original_message_id: int
    """The ID of the original message sent by the sender."""
    received_message_id: int
    """The ID of the message received by the recipient."""
    _: KW_ONLY
    sent_by: Player
    """The player who sent the message."""
    sent_to: Player
    """The player who received the message."""
    sent_in_room: Room
    """The room in which the message was sent."""
    updated_at: str
    """The timestamp of the last update to the message (in ISO format)."""
    message_type: ROLEPLAY_MESSAGE_TYPE
    """The type of the roleplay message."""
    message_content: str
    """The content of the roleplay message."""

    def __str__(self) -> str:
        return f"Message {self.original_message_id} from {self.sent_by} to {self.sent_to} becoming {self.received_message_id} in {self.sent_in_room} ({self.message_type})"

    def __gt__(self, other: RoleplayMessage):
        if not isinstance(other, self.__class__):
            raise NotImplementedError(f"Cannot compare {self.__class__.__name__} with {other.__class__.__name__}")
        return self.last_updated > other.last_updated

    def __ge__(self, other: RoleplayMessage):
        if not isinstance(other, self.__class__):
            raise NotImplementedError(f"Cannot compare {self.__class__.__name__} with {other.__class__.__name__}")
        return self.last_updated >= other.last_updated

    @property
    def last_updated(self) -> datetime:
        """
        Get the last updated timestamp as a datetime object.

        Returns
        -------
        datetime.datetime
            The last updated timestamp as a datetime object.
        """
        return datetime.fromisoformat(self.updated_at)

    @last_updated.setter
    def last_updated(self, value: datetime):
        """
        Set the last updated timestamp from a datetime object.

        Parameters
        ----------
        value : datetime.datetime
            The new last updated timestamp as a datetime object.
        """
        self.updated_at = value.isoformat()
