from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dump_model(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class ChatContentPart(BaseModel):
    type: Literal["text", "image_path", "image_url"]
    text: str | None = None
    path: str | None = None
    url: str | None = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[ChatContentPart]


class LLMPromptRecord(BaseModel):
    kind: str
    prompt_hash: str
    created_at: str = Field(default_factory=utc_now_iso)


class TaskSlot(BaseModel):
    slot_id: str
    level: int
    tier: str
    index: int
    bonus: bool
    tags: list[str] = Field(default_factory=list)


class SampleCase(BaseModel):
    input: str
    output: str
    explanation: str = ""


class GeneratedProblem(BaseModel):
    title: str
    slug: str
    difficulty_level: int
    tier: str
    tags: list[str]
    is_bonus: bool
    requires_diagram: bool = False
    diagram_svg: str = ""
    problem_statement: str
    input_description: str
    output_description: str
    constraints: list[str]
    samples: list[SampleCase]
    intended_solution: str
    correctness_argument: str
    time_complexity: str
    memory_complexity: str
    reference_solution_cpp17: str
    brute_force_solution_python: str = ""
    hidden_test_generator_python: str
    originality_notes: str = ""
    validator_notes: str = ""


class VerificationIssue(BaseModel):
    round: int
    severity: Literal["info", "warning", "error"]
    message: str


class RoundResult(BaseModel):
    round: int
    name: str
    verdict: Literal["ACCEPT", "REVISE", "REJECT"]
    issues: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class VerificationReport(BaseModel):
    slot_id: str
    rounds: list[RoundResult] = Field(default_factory=list)
    final_verdict: Literal["ACCEPT", "REVISE", "REJECT"] = "REVISE"
    revision_attempts: int = 0
    summary: str = ""


class LLMReview(BaseModel):
    verdict: Literal["ACCEPT", "REVISE", "REJECT"]
    issues: list[str] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
    difficulty_assessment: str = ""
    tag_assessment: str = ""


class CounterexamplePlan(BaseModel):
    tests: list[dict[str, Any]] = Field(default_factory=list)


class AnswerContent(BaseModel):
    markdown_content: str


class RunResult(BaseModel):
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_sec: float = 0.0


class TestRunResult(BaseModel):
    accepted: bool
    compile_result: RunResult | None = None
    sample_results: list[dict[str, Any]] = Field(default_factory=list)
    hidden_results: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class LockRecord(BaseModel):
    slot_id: str
    worker_id: str
    hostname: str
    process_id: int
    created_at: str
    expires_at: str
    tags: list[str]
    level: int


class ProblemMetadata(BaseModel):
    slot_id: str
    title: str
    slug: str
    level: int
    tier: str
    tags: list[str]
    bonus: bool
    model_info: dict[str, Any]
    prompts_used: list[LLMPromptRecord] = Field(default_factory=list)
    verification_rounds: int
    revision_attempts: int
    final_status: str
    git_commit_hash: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    similarity_score: float | None = None
    generated_files: list[str] = Field(default_factory=list)
    lock_owner: str | None = None


class AgentState(BaseModel):
    version: int = 1
    planned_slots: list[str] = Field(default_factory=list)
    completed_slots: list[str] = Field(default_factory=list)
    failed_slots: list[str] = Field(default_factory=list)
    retry_queue: list[str] = Field(default_factory=list)
    active_locks: dict[str, dict[str, Any]] = Field(default_factory=dict)
    last_updated: str = Field(default_factory=utc_now_iso)
    worker_history: list[dict[str, Any]] = Field(default_factory=list)
    commit_history: list[dict[str, Any]] = Field(default_factory=list)


class SaveResult(BaseModel):
    root: Path
    files: list[Path]
