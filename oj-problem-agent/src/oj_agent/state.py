from __future__ import annotations

from pathlib import Path

from .models import AgentState, TaskSlot, dump_model, utc_now_iso
from .utils import read_json, write_json


class StateStore:
    def __init__(self, metadata_dir: Path) -> None:
        self.metadata_dir = metadata_dir
        self.path = metadata_dir / "state.json"

    def load(self, slots: list[TaskSlot]) -> AgentState:
        state = AgentState(**(read_json(self.path, {}) or {}))
        planned = [slot.slot_id for slot in slots]
        if state.planned_slots != planned:
            state.planned_slots = planned
        self._recover_from_files(state)
        return state

    def save(self, state: AgentState) -> None:
        state.last_updated = utc_now_iso()
        write_json(self.path, dump_model(state))

    def _recover_from_files(self, state: AgentState) -> None:
        root = self.metadata_dir.parent
        problems_root = root / "problems"
        if problems_root.exists():
            for metadata_path in problems_root.glob("level_*/*/metadata.json"):
                try:
                    slot_id = read_json(metadata_path, {}).get("slot_id")
                except Exception:
                    continue
                if slot_id and slot_id not in state.completed_slots:
                    state.completed_slots.append(slot_id)
        locks_root = root / "locks"
        state.active_locks = {}
        if locks_root.exists():
            for lock_path in locks_root.glob("*.lock.json"):
                try:
                    lock = read_json(lock_path, {})
                except Exception:
                    continue
                slot_id = lock.get("slot_id")
                if slot_id:
                    state.active_locks[slot_id] = lock

    def next_available_slot(self, slots: list[TaskSlot], state: AgentState, levels: set[int] | None = None) -> TaskSlot | None:
        completed = set(state.completed_slots)
        failed = set(state.failed_slots)
        locked = set(state.active_locks)
        for slot in slots:
            if levels and slot.level not in levels:
                continue
            if slot.slot_id in completed or slot.slot_id in failed or slot.slot_id in locked:
                continue
            return slot
        return None
