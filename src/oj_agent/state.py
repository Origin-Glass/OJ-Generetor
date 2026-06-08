from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import AgentState, TaskSlot, dump_model, utc_now_iso
from .utils import read_json, worker_id, write_json


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

    def rotate_retry_slot_to_back(self, state: AgentState, slot_id: str) -> None:
        """Avoid retry-failed starvation by moving a failed retry to the queue tail."""
        remaining = [item for item in state.retry_queue if item != slot_id]
        if slot_id in state.retry_queue:
            remaining.append(slot_id)
        state.retry_queue = remaining

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
                if slot_id and not self._is_expired_lock(lock):
                    state.active_locks[slot_id] = lock

    def next_available_slot(
        self,
        slots: list[TaskSlot],
        state: AgentState,
        levels: set[int] | None = None,
        retry_failed: bool = False,
    ) -> TaskSlot | None:
        completed = set(state.completed_slots)
        failed = set(state.failed_slots)
        current_worker_id = worker_id()
        slot_by_id = {slot.slot_id: slot for slot in slots}
        if retry_failed:
            for slot_id in state.retry_queue:
                slot = slot_by_id.get(slot_id)
                if slot is None:
                    continue
                if levels and slot.level not in levels:
                    continue
                lock = state.active_locks.get(slot.slot_id)
                locked_by_other = lock is not None and lock.get("worker_id") != current_worker_id
                if slot.slot_id in completed or locked_by_other:
                    continue
                return slot
        for slot in slots:
            if levels and slot.level not in levels:
                continue
            lock = state.active_locks.get(slot.slot_id)
            locked_by_other = lock is not None and lock.get("worker_id") != current_worker_id
            if slot.slot_id in completed or slot.slot_id in failed or locked_by_other:
                continue
            return slot
        return None

    def _is_expired_lock(self, lock: dict) -> bool:
        try:
            expires_at = datetime.fromisoformat(str(lock["expires_at"]))
        except Exception:
            return True
        return expires_at < datetime.now(timezone.utc)
