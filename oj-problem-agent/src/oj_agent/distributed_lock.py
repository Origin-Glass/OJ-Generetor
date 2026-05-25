from __future__ import annotations

import os
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import AppConfig
from .github_committer import GithubCommitter
from .models import LockRecord, TaskSlot, dump_model, utc_now_iso
from .utils import read_json, worker_id, write_json


class DistributedLockManager:
    def __init__(self, config: AppConfig, committer: GithubCommitter) -> None:
        self.config = config
        self.committer = committer
        self.lock_dir = config.project_root / "generated" / "locks"

    def claim(self, slot: TaskSlot) -> LockRecord | None:
        self.committer.pull_rebase()
        path = self.lock_path(slot.slot_id)
        if path.exists() and not self.is_expired(path):
            return None
        now = datetime.now(timezone.utc).replace(microsecond=0)
        lock = LockRecord(
            slot_id=slot.slot_id,
            worker_id=worker_id(),
            hostname=socket.gethostname(),
            process_id=os.getpid(),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=self.config.git.lock_ttl_minutes)).isoformat(),
            tags=slot.tags,
            level=slot.level,
        )
        write_json(path, dump_model(lock))
        result = self.committer.add_commit_push([path], f"claim slot {slot.slot_id}", [f"level: {slot.level}", f"tags: {', '.join(slot.tags)}"])
        if not result.ok:
            return None
        return lock

    def release(self, slot_id: str) -> Path | None:
        path = self.lock_path(slot_id)
        if path.exists():
            path.unlink()
            return path
        return None

    def lock_path(self, slot_id: str) -> Path:
        return self.lock_dir / f"{slot_id}.lock.json"

    def is_expired(self, path: Path) -> bool:
        try:
            data = read_json(path, {})
            expires_at = datetime.fromisoformat(data["expires_at"])
        except Exception:
            return True
        return expires_at < datetime.now(timezone.utc)
