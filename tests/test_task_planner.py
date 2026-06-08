import unittest

from oj_agent.tag_planner import TagPlanner
from oj_agent.task_planner import TaskPlanner, level_to_tier


class TaskPlannerTest(unittest.TestCase):
    def test_builds_default_999_slots_with_bonus(self) -> None:
        slots = TaskPlanner().build_plan()
        self.assertEqual(len(slots), 999)
        self.assertEqual(sum(not slot.bonus for slot in slots), 990)
        self.assertEqual(sum(slot.bonus for slot in slots), 9)
        self.assertEqual(slots[0].slot_id, "L01-001")
        self.assertIn("L22-034", {slot.slot_id for slot in slots})
        self.assertEqual(slots[-1].slot_id, "L30-034")

    def test_builds_exact_990_slots_without_bonus(self) -> None:
        slots = TaskPlanner(bonus_levels=()).build_plan()
        self.assertEqual(len(slots), 990)
        self.assertEqual(sum(not slot.bonus for slot in slots), 990)
        self.assertEqual(sum(slot.bonus for slot in slots), 0)
        self.assertEqual(slots[0].slot_id, "L01-001")
        self.assertEqual(slots[-1].slot_id, "L30-033")

    def test_tier_mapping(self) -> None:
        self.assertEqual(level_to_tier(1), "Bronze V")
        self.assertEqual(level_to_tier(15), "Gold I")
        self.assertEqual(level_to_tier(30), "Ruby I")

    def test_tag_assignments_unique_per_level(self) -> None:
        slots = TagPlanner().apply(TaskPlanner().build_plan())
        for level in range(1, 31):
            combos = [tuple(slot.tags) for slot in slots if slot.level == level]
            self.assertEqual(len(combos), len(set(combos)))


if __name__ == "__main__":
    unittest.main()
