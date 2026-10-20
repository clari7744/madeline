import random
from logging import getLogger

import DPyUtils
from discord import ButtonStyle, Interaction, ui

from ..madeline import Madeline
from ..tables import Player, RoleplayMessage
from .modals import EditRoleplayMessageModal

log = getLogger(__name__)


class DiceRollView(ui.LayoutView):
    def __init__(
        self,
        *,
        triggered_by: Interaction[Madeline],
        target: Player,
        check_type: str,
        goal: int,
        bonus_dice: int,
        penalty_dice: int,
    ):
        super().__init__()
        self.triggered_by = triggered_by
        self.target = target
        self.check_type = check_type
        self.goal = goal
        self.bonus_dice = bonus_dice
        self.penalty_dice = penalty_dice

    @ui.button(emoji="🎲", label="Roll Dice", style=ButtonStyle.primary)
    async def roll_dice(self, ixn: Interaction[Madeline], button: ui.Button):
        # Logic to roll the dice and update the result
        tens = random.randint(0, 9) * 10
        ones = random.randint((1 if tens == 0 else 0), 10)
        res_info = f"Rolled **{tens + ones}**.\n"
        for _ in range(self.bonus_dice):
            bonus_tens = random.randint(1, 10) * 10
            tens = min(tens, bonus_tens)
            res_info += f"After bonus: **{tens + ones}**.\n"
        for _ in range(self.penalty_dice):
            penalty_tens = random.randint(1, 10) * 10
            tens = max(tens, penalty_tens)
            res_info += f"After penalty: **{tens + ones}**.\n"
        roll = tens + ones
        result = "success" if roll <= self.goal else "failure"
        await ixn.send(
            f"{res_info}\nYou rolled **{roll}** for your **{self.check_type} check**, which is a **{result}**.",
        )
        await self.triggered_by.followup.send(
            f"{self.target.pretty_name} rolled **{roll}** for their **{self.check_type} check**, which is a **{result}**.",
        )
