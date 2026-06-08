from __future__ import annotations

from .llm_client import LLMClient
from .generator import _normalize_code_fields, _validate_required_content, generated_problem_schema
from .models import ChatMessage, GeneratedProblem, TaskSlot
from .prompts import revision_prompt


class ProblemReviser:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def revise(self, problem: GeneratedProblem, slot: TaskSlot, issues: list[str], max_tokens: int) -> GeneratedProblem:
        last_error: Exception | None = None
        repair_notes = ""
        for attempt in range(3):
            data = self.llm.json_chat(
                [
                    ChatMessage(
                        role="system",
                        content=(
                            "You revise OJ problem JSON. Return JSON only. "
                            "Do not include reasoning, analysis, markdown fences, or prose outside JSON."
                        ),
                    ),
                    ChatMessage(role="user", content=revision_prompt(problem, slot, issues) + repair_notes),
                ],
                temperature=0.2 if attempt == 0 else 0.0,
                max_tokens=max_tokens,
                json_schema=generated_problem_schema(),
                schema_name="GeneratedProblem",
            )
            if "is_bonus" not in data and "bonus" in data:
                data["is_bonus"] = data["bonus"]
            try:
                revised = GeneratedProblem(**data)
                _normalize_code_fields(revised)
                _validate_required_content(revised)
                return revised
            except Exception as exc:
                last_error = exc
                repair_notes = (
                    "\n\nPrevious revised JSON failed validation. Regenerate the full problem JSON from scratch. "
                    "Use the exact GeneratedProblem schema. Use is_bonus, not bonus. "
                    "Do not leave required text/code fields empty. "
                    f"Validation error: {exc}"
                )
        raise RuntimeError(f"Reviser produced invalid JSON after repairs: {last_error}") from last_error
