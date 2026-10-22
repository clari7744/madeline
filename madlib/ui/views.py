import random
from logging import getLogger

from discord import ButtonStyle, Interaction, ui

from ..config import LOCAL_DEBUG
from ..madeline import Madeline
from ..tables import Player

log = getLogger(__name__)


class DiceRollView(ui.View):
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
        log.log(
            LOCAL_DEBUG,
            f"Initializing DiceRollView with triggered_by={triggered_by}, target={target}, check_type={check_type}, goal={goal}, bonus_dice={bonus_dice}, penalty_dice={penalty_dice}",
        )
        self.triggered_by = triggered_by
        self.target = target
        self.check_type = check_type
        self.goal = goal
        self.bonus_dice = bonus_dice
        self.penalty_dice = penalty_dice

    @ui.button(emoji="🎲", label="Roll Dice", style=ButtonStyle.primary)
    async def roll_dice(self, ixn: Interaction[Madeline], button: ui.Button):
        await ixn.response.defer()
        # Logic to roll the dice and update the result
        tens = random.randint(0, 9) * 10
        ones = random.randint((1 if tens == 0 else 0), 10)
        res_info = f"Goal: {self.goal}\nRolled **{tens + ones}**.\n"
        for i in range(self.bonus_dice):
            bonus_tens = random.randint(1, 10) * 10
            tens = min(tens, bonus_tens)
            res_info += f"After bonus #{i + 1}: **{tens + ones}**.\n"
        for i in range(self.penalty_dice):
            penalty_tens = random.randint(1, 10) * 10
            tens = max(tens, penalty_tens)
            res_info += f"After penalty #{i + 1}: **{tens + ones}**.\n"
        roll = tens + ones
        result = "success" if roll <= self.goal else "failure"
        await ixn.edit_original_response(
            content=f"{res_info}\nYou rolled **{roll}** for your **{self.check_type} check**, which is a **{result}**.",
            view=None,
        )
        await self.triggered_by.followup.send(
            f"{self.target.pretty_name} rolled **{roll}** for their **{self.check_type} check**, which is a **{result}**.",
        )
