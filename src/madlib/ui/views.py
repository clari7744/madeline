import random
from asyncio import sleep
from logging import getLogger
from typing import AsyncGenerator

from discord import ButtonStyle, Interaction, Message, ui

from ..config import CURRENT_DEBUG, LOCAL_DEBUG
from ..madeline import Madeline
from ..tables import Player

log = getLogger(__name__)


class DiceRollView(ui.View):
    message: Message
    ROLL_DELAY = 1

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
        super().__init__(timeout=10 * 60)  # 10 minutes
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
        if self.bonus_dice and self.penalty_dice:
            raise ValueError("Cannot have both bonus and penalty dice.")

    async def on_timeout(self):
        log.log(LOCAL_DEBUG, "DiceRollView timed out.")
        for child in self.children:
            child.disabled = True
        await self.message.edit(content=self.message.content + "\n\n***The dice roll has timed out.***", view=self)

    async def d10(self, mult: int = 1):
        await sleep(self.ROLL_DELAY)
        return random.randint(0, 9) * mult

    async def _roll(self) -> AsyncGenerator[tuple[str, int, bool, bool, bool], None]:
        """
        Roll the dice, yielding information at each step.

        Yields
        ------
        tuple[str, int, bool, bool, bool]
            A tuple containing:
            - msg (str): A message describing the roll.
            - res (int): The result of the roll.
            - save (bool): Whether to save the message.
            - edit (bool): Whether to actually edit on this message
            - done (bool): Whether the roll is complete.
        """

        def _c(n: int):
            return "" if n == 1 else "c"

        def _0to100(dice_left: int = 0, dice_type: str = None):
            return (
                f"💥 {f'You have {dice_left} {dice_type} di{_c(dice_left)}e left, but y' if dice_left else 'Y'}ou rolled a 0 on both dice, which is an automatic 100!",
                100,
                True,
                True,
                True,
            )

        tens = await self.d10(10)
        ones = await self.d10()
        yield f"🎲 Rolled **{tens + ones}**.\n", tens + ones, True, False, False

        if ones == tens == 0 and not (self.bonus_dice or self.penalty_dice):
            # don't need to return, outer loop will break for us when it detects done=True
            yield _0to100()

        for i in range(self.bonus_dice):
            n = i + 1
            bonus_left = self.bonus_dice - n

            if ones == tens == 0:
                yield _0to100(bonus_left, "bonus")
            if tens == 0:
                yield f"You have {bonus_left} bonus di{_c(bonus_left)}e remaining, but you rolled a 0 on the tens die, so there's no reason to keep rolling :)", tens + ones, True, True, True

            yield f"🎲 Rolling bonus die #{n}/{self.bonus_dice}...", tens + ones, False, True, False
            bonus_tens = await self.d10(10)
            tens = min(tens, bonus_tens)
            yield f"🎲 Bonus Die #{n}: **{bonus_tens}**\n✨ After bonus #{n}: **{tens + ones}**.", tens + ones, True, False, False

        for i in range(self.penalty_dice):
            n = i + 1
            penalty_left = self.penalty_dice - n

            if ones + tens == 99:
                yield f"You have {penalty_left} penalty di{_c(penalty_left)}e remaining, but you rolled a 99 which is the highest you can get with penalty dice.", tens + ones, True, True, True
            if tens == 9:
                yield f"You have {penalty_left} penalty di{_c(penalty_left)}e remaining, but you rolled a 9 on the tens die, so there's no reason to keep rolling :(", tens + ones, True, True, True

            yield f"🎲 Rolling penalty die #{n}/{self.penalty_dice}...", tens + ones, False, True, False
            penalty_tens = await self.d10(10)
            tens = max(tens, penalty_tens)
            yield f"🎲 Penalty Die #{n}: **{penalty_tens}**\n💥 After penalty #{n}: **{tens + ones}**.", tens + ones, True, False, False

    @ui.button(emoji="🎲", label="Roll Dice", style=ButtonStyle.primary)
    async def roll_dice(self, ixn: Interaction[Madeline], button: ui.Button):
        self.stop()
        # Logic to roll the dice and update the result
        res_info = f"**Goal**: {self.goal}\n**Roll Details**:\n"
        log.log(CURRENT_DEBUG, f"Starting dice roll for {self.target.pretty_name} with goal {self.goal}.")
        await ixn.response.edit_message(content=res_info + "Rolling...", view=None)
        async for msg, roll, save, edit, done in self._roll():
            log.log(
                CURRENT_DEBUG,
                f"Dice roll step: msg='{msg}', roll={roll}, save={save}, edit={edit}, done={done}.".replace(
                    "\n", "\\n"
                ),
            )
            prt = res_info + msg
            if save:
                res_info += msg + "\n"
            if done:
                break
            if not edit:
                continue
            await ixn.edit_original_response(content=prt)

        e = "✅"
        result = "success"
        if roll > self.goal:
            e = "❌"
            result = "failure"
        await ixn.edit_original_response(
            content=f"{res_info}\n{e} You rolled **{roll}** for your **{self.check_type} check**, which is a **{result}**."
        )
        await self.triggered_by.followup.send(
            f"{e} {self.target.pretty_name} rolled **{roll}** for their **{self.check_type} check**, which is a **{result}**."
        )
