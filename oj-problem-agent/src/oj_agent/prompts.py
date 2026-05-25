from __future__ import annotations

import json

from .models import GeneratedProblem, TaskSlot, dump_model


JSON_SCHEMA_FIELDS = [
    "title",
    "slug",
    "difficulty_level",
    "tier",
    "tags",
    "is_bonus",
    "requires_diagram",
    "diagram_svg",
    "problem_statement",
    "input_description",
    "output_description",
    "constraints",
    "samples",
    "intended_solution",
    "correctness_argument",
    "time_complexity",
    "memory_complexity",
    "reference_solution_cpp17",
    "brute_force_solution_python",
    "hidden_test_generator_python",
    "originality_notes",
    "validator_notes",
]


def generator_prompt(slot: TaskSlot) -> str:
    return f"""
You are a Korean online judge problem setter.
Generate one original Korean online judge problem.
Output valid JSON only. No markdown fences. No comments.

Slot:
{json.dumps(dump_model(slot), ensure_ascii=False)}

Rules:
- The problem statement, input, output, constraints, samples, explanations, and notes must be Korean.
- Match difficulty_level exactly: {slot.level}.
- Match tier exactly: {slot.tier}.
- Match tags exactly as the planned set: {slot.tags}.
- is_bonus must be {str(slot.bonus).lower()}.
- Do not copy BOJ, ICPC, Codeforces, AtCoder, or known problem ideas.
- Use a fresh story and constraints that fit the algorithms.
- Include at least one sample.
- Include a complete C++17 reference solution.
- Include a Python brute force solution if feasible; otherwise use an empty string only when genuinely impossible.
- Include a Python hidden test generator that prints test inputs. Prefer JSON list output: [{{"input":"..."}}].
- Include SVG only when useful. If requires_diagram is true, diagram_svg must be complete valid SVG.

Required top-level fields:
{json.dumps(JSON_SCHEMA_FIELDS, ensure_ascii=False)}
""".strip()


def verifier_prompt(problem: GeneratedProblem, slot: TaskSlot) -> str:
    return f"""
You are an adversarial reviewer for Korean online judge problems.
Find ambiguity, underspecified constraints, contradictory examples, impossible outputs, solution bugs,
difficulty mismatch, tag mismatch, copied ideas, and any issue that should block acceptance.
Output valid JSON only with:
{{
  "verdict": "ACCEPT" | "REVISE" | "REJECT",
  "issues": ["..."],
  "required_changes": ["..."],
  "difficulty_assessment": "...",
  "tag_assessment": "..."
}}

Planned slot:
{json.dumps(dump_model(slot), ensure_ascii=False)}

Problem JSON:
{json.dumps(dump_model(problem), ensure_ascii=False)}
""".strip()


def counterexample_prompt(problem: GeneratedProblem, slot: TaskSlot, count: int) -> str:
    return f"""
Generate {count} adversarial test ideas for this online judge problem.
Target edge cases and algorithmic weaknesses: minimum values, maximum values, singleton, empty-like boundary if valid,
disconnected graphs, duplicate values, sorted/reverse sorted, overflow stress, all equal, and impossible cases if relevant.
Output valid JSON only:
{{
  "tests": [
    {{"name": "...", "reason": "...", "input": "concrete input if possible, otherwise empty"}}
  ]
}}

Slot:
{json.dumps(dump_model(slot), ensure_ascii=False)}

Problem:
{json.dumps(dump_model(problem), ensure_ascii=False)}
""".strip()


def revision_prompt(problem: GeneratedProblem, slot: TaskSlot, issues: list[str]) -> str:
    return f"""
Given the issues, revise the problem JSON.
Preserve slot id, difficulty level, tier, bonus flag, and assigned tags.
Output valid JSON only with the same required fields as the generator.

Slot:
{json.dumps(dump_model(slot), ensure_ascii=False)}

Issues:
{json.dumps(issues, ensure_ascii=False)}

Current problem:
{json.dumps(dump_model(problem), ensure_ascii=False)}
""".strip()


def final_review_prompt(problem: GeneratedProblem, slot: TaskSlot, verification_summary: dict) -> str:
    return f"""
Perform final review. Output valid JSON only:
{{
  "verdict": "ACCEPT" | "REVISE" | "REJECT",
  "issues": ["..."],
  "required_changes": ["..."],
  "difficulty_assessment": "...",
  "tag_assessment": "..."
}}

Slot:
{json.dumps(dump_model(slot), ensure_ascii=False)}

Verification summary:
{json.dumps(verification_summary, ensure_ascii=False)}

Problem:
{json.dumps(dump_model(problem), ensure_ascii=False)}
""".strip()


def answer_prompt(problem: GeneratedProblem, slot: TaskSlot, verification_summary: dict) -> str:
    return f"""
Write answer.md content in Korean for this accepted online judge problem.
Output valid JSON only: {{"markdown_content": "..."}}

The markdown must include these headings:
- 접근 방향
- 핵심 관찰
- 알고리즘 설계
- 정당성 증명
- 시간복잡도
- 공간복잡도
- 반례 검토
- reference C++17 solution
- brute force Python solution if available
- hidden test generator explanation
- verification summary

Slot:
{json.dumps(dump_model(slot), ensure_ascii=False)}

Verification summary:
{json.dumps(verification_summary, ensure_ascii=False)}

Problem:
{json.dumps(dump_model(problem), ensure_ascii=False)}
""".strip()
