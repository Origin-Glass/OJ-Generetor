import tempfile
import unittest
from pathlib import Path

from oj_agent.state import StateStore
from oj_agent.tag_planner import TagPlanner
from oj_agent.task_planner import TaskPlanner


class StateTest(unittest.TestCase):
    def test_load_initializes_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slots = TagPlanner().apply(TaskPlanner().build_plan())
            store = StateStore(Path(tmp) / "generated" / "metadata")
            state = store.load(slots)
            self.assertEqual(len(state.planned_slots), 999)
            store.save(state)
            self.assertTrue(store.path.exists())

    def test_next_available_skips_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slots = TagPlanner().apply(TaskPlanner().build_plan())
            store = StateStore(Path(tmp) / "generated" / "metadata")
            state = store.load(slots)
            state.completed_slots.append("L01-001")
            nxt = store.next_available_slot(slots, state)
            self.assertIsNotNone(nxt)
            self.assertEqual(nxt.slot_id, "L01-002")

    def test_next_available_can_prioritize_retry_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slots = TagPlanner().apply(TaskPlanner().build_plan())
            store = StateStore(Path(tmp) / "generated" / "metadata")
            state = store.load(slots)
            state.failed_slots.extend(["L01-001", "L01-002"])
            state.retry_queue.extend(["L01-002", "L01-001"])

            nxt = store.next_available_slot(slots, state, retry_failed=True)

            self.assertIsNotNone(nxt)
            self.assertEqual(nxt.slot_id, "L01-002")

    def test_retry_failure_rotates_slot_to_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slots = TagPlanner().apply(TaskPlanner().build_plan())
            store = StateStore(Path(tmp) / "generated" / "metadata")
            state = store.load(slots)
            state.retry_queue.extend(["L01-002", "L01-001", "L01-003"])

            store.rotate_retry_slot_to_back(state, "L01-002")

            self.assertEqual(state.retry_queue, ["L01-001", "L01-003", "L01-002"])


if __name__ == "__main__":
    unittest.main()
