from __future__ import annotations

import re

from .llm_client import LLMClient
from .models import ChatMessage, GeneratedProblem, TaskSlot
from .prompts import generator_prompt
from .utils import slugify


class ProblemGenerator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate(self, slot: TaskSlot, max_tokens: int | None = None) -> GeneratedProblem:
        last_error: Exception | None = None
        repair_notes = ""
        for attempt in range(3):
            data = self.llm.json_chat(
                [
                    ChatMessage(
                        role="system",
                        content=(
                            "You generate original Korean OJ problems. Return JSON only. "
                            "Do not include reasoning, analysis, markdown fences, or prose outside JSON."
                        ),
                    ),
                    ChatMessage(role="user", content=generator_prompt(slot) + repair_notes),
                ],
                max_tokens=max_tokens,
                temperature=0.2 if attempt == 0 else 0.0,
                json_schema=generated_problem_schema(),
                schema_name="GeneratedProblem",
            )
            data["difficulty_level"] = int(data.get("difficulty_level", slot.level))
            if not data.get("slug"):
                data["slug"] = slugify(str(data.get("title", slot.slot_id)), slot.slot_id.lower())
            try:
                problem = GeneratedProblem(**data)
                _normalize_code_fields(problem)
                _validate_required_content(problem)
                return problem
            except Exception as exc:
                last_error = exc
                repair_notes = (
                    "\n\nPrevious JSON failed validation. Regenerate from scratch. "
                    "Every required string field except diagram_svg, brute_force_solution_python, "
                    "originality_notes, and validator_notes must be non-empty. "
                    "constraints must be a JSON array of strings. "
                    f"Validation error: {exc}"
                )
        raise RuntimeError(f"Generator produced invalid JSON after repairs: {last_error}") from last_error


def _validate_required_content(problem: GeneratedProblem) -> None:
    required = {
        "title": problem.title,
        "slug": problem.slug,
        "problem_statement": problem.problem_statement,
        "input_description": problem.input_description,
        "output_description": problem.output_description,
        "intended_solution": problem.intended_solution,
        "correctness_argument": problem.correctness_argument,
        "time_complexity": problem.time_complexity,
        "memory_complexity": problem.memory_complexity,
        "reference_solution_cpp17": problem.reference_solution_cpp17,
        "hidden_test_generator_python": problem.hidden_test_generator_python,
    }
    empty = [name for name, value in required.items() if not str(value).strip()]
    if empty:
        raise ValueError(f"required fields are empty: {', '.join(empty)}")
    if not problem.constraints:
        raise ValueError("constraints are empty")
    if not problem.samples:
        raise ValueError("samples are empty")


def _normalize_code_fields(problem: GeneratedProblem) -> None:
    problem.reference_solution_cpp17 = _normalize_cpp(problem.reference_solution_cpp17)
    if problem.brute_force_solution_python and "\n" not in problem.brute_force_solution_python:
        problem.brute_force_solution_python = ""
    problem.hidden_test_generator_python = _sample_based_generator(problem)


def _normalize_cpp(source: str) -> str:
    source = source.strip()
    source = re.sub(r"\s+(#include\s*<)", r"\n\1", source)
    source = re.sub(r"(#include\s*<[^>]+>)\s*", r"\1\n", source)
    source = re.sub(r"\s*(using\s+namespace\s+std\s*;)", r"\n\1\n", source)
    source = re.sub(r"\s*(int\s+main\s*\()", r"\n\1", source)
    return source + ("\n" if not source.endswith("\n") else "")


def _sample_based_generator(problem: GeneratedProblem) -> str:
    cases = [{"input": sample.input} for sample in problem.samples]
    return "import json\nprint(json.dumps(" + repr(cases) + ", ensure_ascii=False))\n"


def generated_problem_schema() -> dict:
    schema = GeneratedProblem.model_json_schema()
    props = schema.get("properties", {})
    max_lengths = {
        "title": 80,
        "slug": 100,
        "tier": 20,
        "diagram_svg": 2000,
        "problem_statement": 1200,
        "input_description": 600,
        "output_description": 600,
        "intended_solution": 900,
        "correctness_argument": 900,
        "time_complexity": 120,
        "memory_complexity": 120,
        "reference_solution_cpp17": 3000,
        "brute_force_solution_python": 2500,
        "hidden_test_generator_python": 2500,
        "originality_notes": 300,
        "validator_notes": 300,
    }
    for name, limit in max_lengths.items():
        if name in props:
            props[name]["maxLength"] = limit
    non_empty = [
        "title",
        "slug",
        "tier",
        "problem_statement",
        "input_description",
        "output_description",
        "intended_solution",
        "correctness_argument",
        "time_complexity",
        "memory_complexity",
        "reference_solution_cpp17",
        "hidden_test_generator_python",
    ]
    for name in non_empty:
        if name in props:
            props[name]["minLength"] = 1
    if "tags" in props:
        props["tags"]["minItems"] = 1
        props["tags"]["maxItems"] = 4
    if "constraints" in props:
        props["constraints"]["minItems"] = 1
        props["constraints"]["maxItems"] = 8
        props["constraints"]["items"] = {"type": "string", "maxLength": 160}
    if "samples" in props:
        props["samples"]["minItems"] = 1
        props["samples"]["maxItems"] = 3
    sample = schema.get("$defs", {}).get("SampleCase", {}).get("properties", {})
    if "input" in sample:
        sample["input"]["maxLength"] = 1000
    if "output" in sample:
        sample["output"]["maxLength"] = 1000
    if "explanation" in sample:
        sample["explanation"]["maxLength"] = 400
    return schema
