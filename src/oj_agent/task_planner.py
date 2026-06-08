from __future__ import annotations

from dataclasses import dataclass

from .models import TaskSlot


TIER_BY_LEVEL = {
    1: "Bronze V",
    2: "Bronze IV",
    3: "Bronze III",
    4: "Bronze II",
    5: "Bronze I",
    6: "Silver V",
    7: "Silver IV",
    8: "Silver III",
    9: "Silver II",
    10: "Silver I",
    11: "Gold V",
    12: "Gold IV",
    13: "Gold III",
    14: "Gold II",
    15: "Gold I",
    16: "Platinum V",
    17: "Platinum IV",
    18: "Platinum III",
    19: "Platinum II",
    20: "Platinum I",
    21: "Diamond V",
    22: "Diamond IV",
    23: "Diamond III",
    24: "Diamond II",
    25: "Diamond I",
    26: "Ruby V",
    27: "Ruby IV",
    28: "Ruby III",
    29: "Ruby II",
    30: "Ruby I",
}


@dataclass(frozen=True)
class TaskPlanner:
    total_per_level: int = 33
    bonus_levels: tuple[int, ...] = tuple(range(22, 31))

    def build_plan(self) -> list[TaskSlot]:
        slots: list[TaskSlot] = []
        for level in range(1, 31):
            for index in range(1, self.total_per_level + 1):
                slots.append(
                    TaskSlot(
                        slot_id=f"L{level:02d}-{index:03d}",
                        level=level,
                        tier=TIER_BY_LEVEL[level],
                        index=index,
                        bonus=False,
                    )
                )
            if level in self.bonus_levels:
                index = self.total_per_level + 1
                slots.append(
                    TaskSlot(
                        slot_id=f"L{level:02d}-{index:03d}",
                        level=level,
                        tier=TIER_BY_LEVEL[level],
                        index=index,
                        bonus=True,
                    )
                )
        expected = 30 * self.total_per_level + len(self.bonus_levels)
        if len(slots) != expected:
            raise ValueError(f"Expected {expected} slots, got {len(slots)}")
        return slots


def level_to_tier(level: int) -> str:
    return TIER_BY_LEVEL[level]
