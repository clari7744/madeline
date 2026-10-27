from discord import Interaction, Message, TextStyle, ui

from ..helpers import ROLEPLAY_MESSAGE_TYPE, strip_content_header
from ..madeline import Madeline
from ..tables import Player


class EditRoleplayMessageModal(ui.Modal):

    new_content = ui.TextInput(
        label="New Content",
        style=TextStyle.paragraph,
        placeholder="Enter the new content for the roleplay message...",
        required=True,
    )

    def __init__(self, sent_by: Player, original_message: Message, message_type: ROLEPLAY_MESSAGE_TYPE = "rp"):
        super().__init__(title="Edit Roleplay Message")
        self.sent_by = sent_by
        self.original_message = original_message
        self.message_type = message_type
        self.new_content.default = strip_content_header(original_message.content)

    async def on_submit(self, ixn: Interaction[Madeline]):
        """
        Handle the submission of the modal.

        Parameters
        ----------
        ixn : Interaction[Madeline]
            The interaction that triggered the modal submission.
        """
        await ixn.response.defer(thinking=True, ephemeral=True)
        msg = self.new_content.value.strip()
        if not msg:
            await ixn.send("You must provide new content for the roleplay message.", ephemeral=True)
            return

        await self.sent_by.rp(ixn, msg, message_type=self.message_type, src_message=self.original_message)

        await ixn.send("Roleplay message updated.", ephemeral=True)
