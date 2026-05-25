from __future__ import annotations

import argparse
import tempfile
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .answer_writer import AnswerWriter
from .config import AppConfig, load_config
from .distributed_lock import DistributedLockManager
from .generator import ProblemGenerator
from .github_committer import GithubCommitter
from .llm_client import LLMClient
from .markdown_writer import save_problem_bundle
from .models import LLMPromptRecord, ProblemMetadata, TaskSlot, dump_model, utc_now_iso
from .revision import ProblemReviser
from .similarity import SimilarityChecker
from .state import StateStore
from .tag_planner import TagPlanner
from .task_planner import TaskPlanner, level_to_tier
from .utils import ensure_dir, read_json, slugify, stable_hash, write_json
from .verifier import ProblemVerifier

console = Console()


def build_slots(config: AppConfig) -> list[TaskSlot]:
    planner = TaskPlanner(config.generation.total_per_level, tuple(config.generation.bonus_levels))
    slots = planner.build_plan()
    return TagPlanner(config.generation.seed).apply(slots)


def cmd_plan(config: AppConfig) -> None:
    slots = build_slots(config)
    table = Table(title="Generation plan")
    table.add_column("Total")
    table.add_column("Standard")
    table.add_column("Bonus")
    table.add_row(str(len(slots)), str(sum(not s.bonus for s in slots)), str(sum(s.bonus for s in slots)))
    console.print(table)
    plan_path = config.project_root / config.generation.metadata_dir / "plan.json"
    write_json(plan_path, [dump_model(slot) for slot in slots])
    console.print(f"Wrote {plan_path}")


def cmd_status(config: AppConfig) -> None:
    slots = build_slots(config)
    state = StateStore(config.project_root / config.generation.metadata_dir).load(slots)
    table = Table(title="oj-problem-agent status")
    table.add_column("planned")
    table.add_column("completed")
    table.add_column("failed")
    table.add_column("retry")
    table.add_column("locks")
    table.add_row(
        str(len(state.planned_slots)),
        str(len(state.completed_slots)),
        str(len(state.failed_slots)),
        str(len(state.retry_queue)),
        str(len(state.active_locks)),
    )
    console.print(table)


def cmd_dry_run_one(config: AppConfig, level: int) -> None:
    slots = [slot for slot in build_slots(config) if slot.level == level]
    if not slots:
        raise ValueError(f"No slots for level {level}")
    console.print_json(json.dumps(dump_model(slots[0]), ensure_ascii=False))


def cmd_generate_one(config: AppConfig, level: int, tags: str | None, force: bool = False, dry_run: bool = False) -> None:
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
    index = 1
    slot = TaskSlot(
        slot_id=f"L{level:02d}-{index:03d}",
        level=level,
        tier=level_to_tier(level),
        index=index,
        bonus=False,
        tags=tag_list or TagPlanner(config.generation.seed).pool_for_level(level)[:1],
    )
    if dry_run:
        console.print_json(json.dumps(dump_model(slot), ensure_ascii=False))
        return
    lock = DistributedLockManager(config, GithubCommitter(config)).claim(slot)
    if lock is None:
        raise RuntimeError(f"Could not claim {slot.slot_id}")
    run_slot(config, slot, force=force)


def cmd_generate(config: AppConfig, max_problems: int | None, levels: set[int] | None) -> None:
    committer = GithubCommitter(config)
    committer.configure_identity()
    slots = build_slots(config)
    state_store = StateStore(config.project_root / config.generation.metadata_dir)
    count = 0
    while max_problems is None or count < max_problems:
        committer.pull_rebase()
        state = state_store.load(slots)
        slot = state_store.next_available_slot(slots, state, levels)
        if slot is None:
            console.print("No available slots.")
            break
        lock = DistributedLockManager(config, committer).claim(slot)
        if lock is None:
            console.print(f"Could not claim {slot.slot_id}; trying next refresh.")
            continue
        accepted = run_slot(config, slot)
        count += 1
        if not accepted:
            console.print(f"{slot.slot_id} queued for retry.")


def cmd_validate_all(config: AppConfig) -> None:
    root = config.project_root / config.generation.output_dir
    missing = []
    for metadata_path in root.glob("level_*/*/metadata.json"):
        folder = metadata_path.parent
        for rel in ["problem.md", "answer.md", "verification.json", "solutions/reference.cpp", "solutions/generator.py"]:
            if not (folder / rel).exists():
                missing.append(str(folder / rel))
    if missing:
        console.print("Missing files:")
        for path in missing:
            console.print(path)
        raise SystemExit(1)
    console.print("Validation passed.")


def cmd_smoke_test(config: AppConfig) -> None:
    with tempfile.TemporaryDirectory(prefix="oj-agent-smoke-") as tmp:
        smoke = _clone_config(config)
        smoke.project_root = Path(tmp)
        smoke.llm = _clone_model(smoke.llm, api_base="fake://fixture", api_key_env="OPENAI_API_KEY", model="fake-oj-model")
        smoke.git = _clone_model(smoke.git, enabled=False, push_after_commit=False)
        smoke.similarity = _clone_model(smoke.similarity, enabled=False, require_dataset=False)
        slot = TaskSlot(
            slot_id="L01-001",
            level=1,
            tier=level_to_tier(1),
            index=1,
            bonus=False,
            tags=["implementation"],
        )
        if not run_slot(smoke, slot):
            raise RuntimeError("fake LLM smoke test failed")
        expected = smoke.project_root / smoke.generation.output_dir / "level_01" / "L01-001_quiet-sum" / "problem.md"
        if not expected.exists():
            raise RuntimeError(f"smoke output missing: {expected}")
        console.print("Smoke test passed with fake LLM.")


def run_slot(config: AppConfig, slot: TaskSlot, force: bool = False) -> bool:
    output_root = config.project_root / config.generation.output_dir
    metadata_dir = config.project_root / config.generation.metadata_dir
    ensure_dir(output_root)
    ensure_dir(metadata_dir)

    llm = LLMClient(config.llm)
    generator = ProblemGenerator(llm)
    reviser = ProblemReviser(llm)
    verifier = ProblemVerifier(config, llm, SimilarityChecker(config.similarity, config.project_root))
    answer_writer = AnswerWriter(llm)
    committer = GithubCommitter(config)
    lock_manager = DistributedLockManager(config, committer)
    state_store = StateStore(metadata_dir)
    slots = build_slots(config)

    existing = list(output_root.glob(f"level_{slot.level:02d}/{slot.slot_id}_*/metadata.json"))
    if existing and not force:
        console.print(f"{slot.slot_id} already exists; skipping.")
        return True

    problem = generator.generate(slot, max_tokens=config.llm.max_tokens)
    all_issues: list[str] = []
    report = None
    for attempt in range(config.generation.max_revision_attempts + 1):
        report = verifier.verify(problem, slot, revision_attempts=attempt)
        if report.final_verdict == "ACCEPT":
            effort = config.verification.effort_for_level(slot.level)
            answer = answer_writer.write(problem, slot, {"rounds": [dump_model(r) for r in report.rounds]}, effort.verifier_max_tokens)
            similarity_score = report.rounds[0].data.get("similarity_score") if report.rounds else None
            metadata = ProblemMetadata(
                slot_id=slot.slot_id,
                title=problem.title,
                slug=slugify(problem.slug, slot.slot_id.lower()),
                level=slot.level,
                tier=slot.tier,
                tags=slot.tags,
                bonus=slot.bonus,
                model_info={"api_base": config.llm.api_base, "model": config.llm.model},
                prompts_used=[LLMPromptRecord(kind="generator", prompt_hash=stable_hash(slot.slot_id))],
                verification_rounds=len(report.rounds),
                revision_attempts=attempt,
                final_status="accepted",
                similarity_score=similarity_score,
            )
            saved = save_problem_bundle(output_root, problem, metadata, dump_model(report), answer)
            state = state_store.load(slots)
            if slot.slot_id not in state.completed_slots:
                state.completed_slots.append(slot.slot_id)
            state.active_locks.pop(slot.slot_id, None)
            state.commit_history.append({"slot_id": slot.slot_id, "commit": None, "time": utc_now_iso()})
            state_store.save(state)
            lock_path = lock_manager.lock_path(slot.slot_id)
            lock_data = read_json(lock_path, None) if lock_path.exists() else None
            removed_lock_path = lock_manager.release(slot.slot_id)
            paths = saved.files + [state_store.path] + ([removed_lock_path] if removed_lock_path else [])
            commit = committer.add_commit_push(
                paths,
                f"add problem {slot.slot_id}: {problem.title}",
                [
                    f"level: {slot.level}",
                    f"tags: {', '.join(slot.tags)}",
                    "verification status: accepted",
                    f"revision attempts: {attempt}",
                    f"generated files: {len(saved.files)}",
                ],
            )
            if not commit.ok:
                if lock_data is not None:
                    write_json(lock_path, lock_data)
                state.completed_slots = [item for item in state.completed_slots if item != slot.slot_id]
                state.commit_history = [item for item in state.commit_history if item.get("slot_id") != slot.slot_id]
                state_store.save(state)
                raise RuntimeError(f"failed to commit accepted problem {slot.slot_id}: {commit.stderr}")
            return True
        all_issues = [issue for round_result in report.rounds for issue in round_result.issues]
        if attempt < config.generation.max_revision_attempts:
            problem = reviser.revise(problem, slot, all_issues, config.verification.effort_for_level(slot.level).verifier_max_tokens)

    retry_dir = config.project_root / "generated" / "retry_queue"
    retry_path = retry_dir / f"{slot.slot_id}.json"
    write_json(
        retry_path,
        {
            "slot_id": slot.slot_id,
            "level": slot.level,
            "tags": slot.tags,
            "issues": all_issues,
            "updated_at": utc_now_iso(),
        },
    )
    state = state_store.load(slots)
    if slot.slot_id not in state.failed_slots:
        state.failed_slots.append(slot.slot_id)
    if slot.slot_id not in state.retry_queue:
        state.retry_queue.append(slot.slot_id)
    state.active_locks.pop(slot.slot_id, None)
    state_store.save(state)
    lock_path = lock_manager.lock_path(slot.slot_id)
    lock_data = read_json(lock_path, None) if lock_path.exists() else None
    removed_lock_path = lock_manager.release(slot.slot_id)
    paths = [retry_path, state_store.path] + ([removed_lock_path] if removed_lock_path else [])
    commit = committer.add_commit_push(paths, f"queue retry {slot.slot_id}", [f"level: {slot.level}", f"tags: {', '.join(slot.tags)}"])
    if not commit.ok:
        if lock_data is not None:
            write_json(lock_path, lock_data)
        state.failed_slots = [item for item in state.failed_slots if item != slot.slot_id]
        state.retry_queue = [item for item in state.retry_queue if item != slot.slot_id]
        state_store.save(state)
        raise RuntimeError(f"failed to commit retry queue for {slot.slot_id}: {commit.stderr}")
    return False


def parse_levels(text: str | None) -> set[int] | None:
    if not text:
        return None
    return {int(part.strip()) for part in text.split(",") if part.strip()}


def _clone_config(config: AppConfig) -> AppConfig:
    if hasattr(config, "model_copy"):
        return config.model_copy(deep=True)
    return config.copy(deep=True)


def _clone_model(obj, **updates):
    if hasattr(obj, "model_copy"):
        return obj.model_copy(update=updates)
    return obj.copy(update=updates)


def main() -> None:
    parser = argparse.ArgumentParser(prog="oj-problem-agent")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--debug", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    sub.add_parser("status")
    gen = sub.add_parser("generate")
    gen.add_argument("--max-problems", type=int)
    gen.add_argument("--levels")
    one = sub.add_parser("generate-one")
    one.add_argument("--level", type=int, required=True)
    one.add_argument("--tags")
    one.add_argument("--force", action="store_true")
    dry = sub.add_parser("dry-run-one")
    dry.add_argument("--level", type=int, required=True)
    sub.add_parser("resume")
    sub.add_parser("retry-failed")
    sub.add_parser("validate-all")
    sub.add_parser("smoke-test")
    args = parser.parse_args()
    config = load_config(args.config)
    try:
        if args.command == "plan":
            cmd_plan(config)
        elif args.command == "status":
            cmd_status(config)
        elif args.command == "generate":
            cmd_generate(config, args.max_problems, parse_levels(args.levels))
        elif args.command == "generate-one":
            cmd_generate_one(config, args.level, args.tags, args.force)
        elif args.command == "dry-run-one":
            cmd_generate_one(config, args.level, None, dry_run=True)
        elif args.command in {"resume", "retry-failed"}:
            cmd_generate(config, None, None)
        elif args.command == "validate-all":
            cmd_validate_all(config)
        elif args.command == "smoke-test":
            cmd_smoke_test(config)
    except Exception:
        if args.debug:
            raise
        console.print_exception(show_locals=False)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
