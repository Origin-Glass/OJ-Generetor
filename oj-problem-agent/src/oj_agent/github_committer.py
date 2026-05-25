from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig


@dataclass
class GitResult:
    ok: bool
    stdout: str
    stderr: str
    commit_hash: str | None = None


class GithubCommitter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.root = config.project_root

    def enabled(self) -> bool:
        return self.config.git.enabled and (self.root / ".git").exists()

    def pull_rebase(self) -> GitResult:
        if not self.enabled():
            return GitResult(True, "git disabled or not a repository", "")
        return self._git(["pull", "--rebase", self.config.git.remote, self.config.git.branch])

    def add_commit_push(self, paths: list[Path], subject: str, body_lines: list[str]) -> GitResult:
        if not self.enabled():
            return GitResult(True, "git disabled or not a repository", "")
        rel_paths = [str(path.resolve().relative_to(self.root.resolve())) for path in paths]
        if rel_paths:
            add = self._git(["add", *rel_paths])
            if not add.ok:
                return add
        msg_args = ["commit", "-m", subject]
        for line in body_lines:
            msg_args.extend(["-m", line])
        commit = self._git(msg_args)
        if not commit.ok and "nothing to commit" not in commit.stdout.lower() + commit.stderr.lower():
            return commit
        commit_hash = self.current_commit_hash()
        if self.config.git.push_after_commit:
            push = self.push()
            if not push.ok:
                return push
        return GitResult(True, commit.stdout, commit.stderr, commit_hash=commit_hash)

    def push(self) -> GitResult:
        remote = self.config.git.remote
        token = os.getenv(self.config.github.token_env, "")
        url = self._authenticated_remote_url(remote, token)
        target = url or remote
        return self._git(["push", target, self.config.git.branch])

    def current_commit_hash(self) -> str | None:
        result = self._git(["rev-parse", "HEAD"])
        if result.ok:
            return result.stdout.strip()
        return None

    def configure_identity(self) -> None:
        username = os.getenv(self.config.github.username_env, "")
        email = os.getenv(self.config.github.email_env, "")
        if username:
            self._git(["config", "user.name", username])
        if email:
            self._git(["config", "user.email", email])

    def _authenticated_remote_url(self, remote: str, token: str) -> str | None:
        if not token:
            return None
        result = self._git(["remote", "get-url", remote])
        if not result.ok:
            return None
        url = result.stdout.strip()
        if not url.startswith("https://"):
            return None
        return url.replace("https://", f"https://x-access-token:{token}@", 1)

    def _git(self, args: list[str]) -> GitResult:
        safe_args = ["git", *args]
        display_args = ["***TOKEN***" if "x-access-token:" in item else item for item in safe_args]
        try:
            completed = subprocess.run(
                safe_args,
                cwd=str(self.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            return GitResult(False, "", str(exc))
        stdout = completed.stdout.replace(os.getenv(self.config.github.token_env, "__none__"), "***TOKEN***")
        stderr = completed.stderr.replace(os.getenv(self.config.github.token_env, "__none__"), "***TOKEN***")
        if completed.returncode != 0:
            stderr = f"{stderr}\ncommand: {' '.join(display_args)}"
        return GitResult(completed.returncode == 0, stdout, stderr)
