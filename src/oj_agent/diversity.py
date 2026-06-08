from __future__ import annotations

import re
from dataclasses import dataclass

from .models import GeneratedProblem, TaskSlot


LOW_LEVEL_TOPIC_HINTS = [
    "input/output formatting with one or two small values; no arithmetic sum as the core task",
    "comparison of two numbers or words with a conditional output",
    "unit conversion using one simple formula, not A+B",
    "string length, repetition, prefix/suffix, or character access",
    "minimum/maximum/median among a few values",
    "counting selected characters or digits in a short string",
    "conditional pricing, score, or grade classification",
    "sum or average of N values where N is part of the input; not exactly two-number sum",
    "coordinate movement on a line or grid after simple commands",
    "date, clock, or duration arithmetic with carry/borrow",
    "pattern printing with a small loop",
    "sorting a few values and reporting an order statistic",
    "parsing a simple formatted string",
    "remainder, quotient, parity, or divisibility classification",
    "simple simulation over a short sequence of events",
    "set membership or duplicate detection in a tiny input",
    "table lookup from a small fixed rule set",
    "rounding, absolute difference, or distance on a number line",
    "string case conversion or vowel/consonant counting",
    "grid cell color, checkerboard, or coordinate quadrant classification",
    "bounded brute force over one small integer range",
    "prefix running total over a short list",
    "find first/last occurrence in a sequence",
    "merge or compare two short strings",
    "simple greedy choice among given options",
    "small combinatorics count by direct formula",
    "number decomposition into digits",
    "validate a password, code, or ticket by local rules",
    "simulate queue-like arrivals with very small constraints",
    "choose winner under deterministic game scoring rules",
    "translate symbols according to a mapping table",
    "measure rectangle/triangle perimeter or area with integer inputs",
    "classify an input into named buckets using multiple conditions",
]

COMMON_LOW_LEVEL_AVOID_TOPICS = [
    "A+B",
    "A + B",
    "two-number sum",
    "sum of two numbers",
    "두 수의 합",
    "두 정수 A와 B",
    "A와 B의 합",
    "A와 B를 더",
]

LOW_LEVEL_HINT_BY_TAG = {
    "implementation": "input/output formatting, simple branching, or direct simulation; no arithmetic sum as the core task",
    "arithmetic": "comparison, parity, quotient/remainder, or absolute difference; not two-number sum",
    "math": "unit conversion, divisibility classification, digit decomposition, or simple formula; not A+B",
    "sorting": "sort a few values and report order, minimum, maximum, median, or ranking",
    "greedy": "choose the best option under a small deterministic rule such as pricing or scoring",
    "string": "string length, repetition, prefix/suffix, case conversion, or character counting",
    "parsing": "parse a simple formatted string such as time, code, coordinate, or symbol sequence",
    "brute force": "bounded brute force over a tiny integer/string range with small constraints",
}

LOW_LEVEL_TAG_HINT_PRIORITY = [
    "string",
    "parsing",
    "brute force",
    "sorting",
    "greedy",
    "math",
    "arithmetic",
    "implementation",
]


@dataclass(frozen=True)
class DiversityIssue:
    message: str


def topic_hint_for_slot(slot: TaskSlot) -> str:
    if slot.level <= 5:
        ordered_tags = sorted(
            slot.tags,
            key=lambda tag: LOW_LEVEL_TAG_HINT_PRIORITY.index(tag) if tag in LOW_LEVEL_TAG_HINT_PRIORITY else 999,
        )
        for tag in ordered_tags:
            if tag in LOW_LEVEL_HINT_BY_TAG:
                return LOW_LEVEL_HINT_BY_TAG[tag]
        offset = (slot.level - 1) * 7
        return LOW_LEVEL_TOPIC_HINTS[(slot.index - 1 + offset) % len(LOW_LEVEL_TOPIC_HINTS)]
    return _advanced_topic_hint(slot.tags)


def avoid_topics_for_slot(slot: TaskSlot) -> list[str]:
    if slot.level <= 5:
        return list(COMMON_LOW_LEVEL_AVOID_TOPICS)
    return []


def apply_diversity_to_slot(slot: TaskSlot) -> TaskSlot:
    topic_hint = topic_hint_for_slot(slot)
    avoid_topics = avoid_topics_for_slot(slot)
    if hasattr(slot, "model_copy"):
        return slot.model_copy(update={"topic_hint": topic_hint, "avoid_topics": avoid_topics})
    return slot.copy(update={"topic_hint": topic_hint, "avoid_topics": avoid_topics})


def diversity_issues(problem: GeneratedProblem, slot: TaskSlot) -> list[str]:
    issues: list[str] = []
    text = _problem_text(problem)
    normalized = _normalize(text)
    for topic in slot.avoid_topics:
        if _normalize(topic) and _normalize(topic) in normalized:
            issues.append(f"diversity guardrail violated: avoid topic '{topic}'")
            break

    if slot.level <= 5 and _looks_like_two_number_sum(problem):
        issues.append("diversity guardrail violated: low-level problem degenerates to two-number sum/A+B")

    return issues


def _advanced_topic_hint(tags: list[str]) -> str:
    return "combine the assigned tags into a fresh problem idea with a distinct story and input/output structure"


def _problem_text(problem: GeneratedProblem) -> str:
    return "\n".join(
        [
            problem.title,
            problem.slug,
            problem.problem_statement,
            problem.input_description,
            problem.output_description,
            problem.intended_solution,
            problem.originality_notes,
            problem.validator_notes,
        ]
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def _looks_like_two_number_sum(problem: GeneratedProblem) -> bool:
    text = _normalize(_problem_text(problem))
    code = _normalize(problem.reference_solution_cpp17)
    title = _normalize(problem.title)
    if any(marker in text for marker in ["두수의합", "a+b", "a와b의합", "두정수a와b"]):
        return True
    if "sum" in title and any(marker in code for marker in ["cout<<a+b", "cout<<(a+b)", "print(a+b)"]):
        return True
    return False



