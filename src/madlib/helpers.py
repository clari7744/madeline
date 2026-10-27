from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Literal

from discord import Interaction, app_commands
from DPyUtils import strfdur

from madlib.config import EAVESDROP_COOLDOWN, LOCAL_DEBUG

from .tables import Player, Room

if TYPE_CHECKING:
    from .madeline import Madeline

log = getLogger(__name__)

FLIP_DIRECTION = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "down",
    "down": "up",
}
DIRECTION = Literal["north", "south", "east", "west", "up", "down"]

ROLEPLAY_MESSAGE_TYPE = Literal["whisper", "rp", "shout"]


async def is_game_channel(ixn: Interaction[Madeline]) -> bool:
    """
    Check if the interaction is in a game channel.

    Parameters
    ----------
    ixn : Interaction[Madeline]
        The interaction to check.

    Returns
    -------
    bool
        True if the interaction is in a game channel.

    Raises
    ------
    app_commands.CheckFailure
        If the interaction is not in a game channel.
    """

    if ixn.client.cache.get_cache(Player).get(ixn.channel_id) is None:
        raise app_commands.CheckFailure("You are not in a game channel.")
    return True


def strip_content_header(content: str) -> str:
    """
    Strip the header from a roleplay message content.

    Parameters
    ----------
    content : str
        The content of the roleplay message.

    Returns
    -------
    str
        The content without the header.
    """
    log.log(LOCAL_DEBUG, f"Stripping header from content: {content}")
    header, _, body = content.partition(":*")
    log.log(LOCAL_DEBUG, f"Header: {header}, Body: {body}")
    if body.startswith("*"):
        body = body[1:]
        log.log(LOCAL_DEBUG, f"Stripped leading asterisk from body: {body}")
    return body.strip()


class Actions:
    WHISPER = "whisper to"
    LOOK_AT = "look at"
    FOLLOW = "follow"


class FailedTransform(app_commands.AppCommandError):
    def __init__(self, message: str):
        super().__init__(message)


class EavesdropCooldown(app_commands.CommandOnCooldown):
    def __init__(self, retry_after: float, room: Room, cooldown: app_commands.Cooldown):
        self.message = f"You can only eavesdrop on a room once every {strfdur(EAVESDROP_COOLDOWN)}. You can eavesdrop on **{room}** again in `{strfdur(retry_after)}`."
        super().__init__(cooldown, retry_after)
