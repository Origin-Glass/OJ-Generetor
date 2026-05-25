from __future__ import annotations

from pathlib import Path

import yaml

from .models import GeneratedProblem, ProblemMetadata, SaveResult, dump_model, utc_now_iso
from .svg_generator import is_valid_svg
from .utils import ensure_dir, safe_relative, write_json


def render_problem_md(problem: GeneratedProblem, metadata: ProblemMetadata) -> str:
    front = {
        "id": metadata.slot_id,
        "title": problem.title,
        "difficulty_level": problem.difficulty_level,
        "tier": problem.tier,
        "tags": problem.tags,
        "bonus": problem.is_bonus,
        "status": "accepted",
        "generated_at": metadata.created_at,
        "model": metadata.model_info.get("model", ""),
        "verification_rounds": metadata.verification_rounds,
    }
    lines = ["---", yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip(), "---", ""]
    lines.extend(
        [
            f"# {problem.title}",
            "",
            f"- Difficulty level: {problem.difficulty_level}",
            f"- Tier: {problem.tier}",
            f"- Tags: {', '.join(problem.tags)}",
            f"- Bonus: {str(problem.is_bonus).lower()}",
            "",
        ]
    )
    if problem.requires_diagram and problem.diagram_svg.strip():
        lines.extend(["![diagram](assets/diagram.svg)", ""])
    lines.extend(
        [
            "## 문제",
            problem.problem_statement.strip(),
            "",
            "## 입력",
            problem.input_description.strip(),
            "",
            "## 출력",
            problem.output_description.strip(),
            "",
            "## 제한",
        ]
    )
    for constraint in problem.constraints:
        lines.append(f"- {constraint}")
    lines.append("")
    for i, sample in enumerate(problem.samples, start=1):
        lines.extend(
            [
                f"## 예제 {i}",
                "",
                "### 입력",
                "",
                "```text",
                sample.input.rstrip(),
                "```",
                "",
                "### 출력",
                "",
                "```text",
                sample.output.rstrip(),
                "```",
                "",
            ]
        )
        if sample.explanation.strip():
            lines.extend(["### 설명", "", sample.explanation.strip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def save_problem_bundle(
    root: Path,
    problem: GeneratedProblem,
    metadata: ProblemMetadata,
    verification: dict,
    answer_markdown: str,
) -> SaveResult:
    slug = metadata.slug
    problem_root = root / f"level_{problem.difficulty_level:02d}" / f"{metadata.slot_id}_{slug}"
    ensure_dir(problem_root)
    paths = {
        "problem": problem_root / "problem.md",
        "answer": problem_root / "answer.md",
        "metadata": problem_root / "metadata.json",
        "verification": problem_root / "verification.json",
        "reference": problem_root / "solutions" / "reference.cpp",
        "brute": problem_root / "solutions" / "brute_force.py",
        "generator": problem_root / "solutions" / "generator.py",
    }
    for path in paths.values():
        ensure_dir(path.parent)
    if problem.requires_diagram and problem.diagram_svg.strip():
        if not is_valid_svg(problem.diagram_svg):
            raise ValueError("Invalid SVG")
        diagram = problem_root / "assets" / "diagram.svg"
        ensure_dir(diagram.parent)
        diagram.write_text(problem.diagram_svg, encoding="utf-8")
        paths["diagram"] = diagram
    for i, sample in enumerate(problem.samples, start=1):
        sample_in = problem_root / "tests" / "samples" / f"sample_{i:02d}.in"
        sample_out = problem_root / "tests" / "samples" / f"sample_{i:02d}.out"
        ensure_dir(sample_in.parent)
        sample_in.write_text(sample.input, encoding="utf-8")
        sample_out.write_text(sample.output, encoding="utf-8")
        paths[f"sample_{i}_in"] = sample_in
        paths[f"sample_{i}_out"] = sample_out
    ensure_dir(problem_root / "tests" / "hidden")
    ensure_dir(problem_root / "tests" / "counterexamples")
    paths["problem"].write_text(render_problem_md(problem, metadata), encoding="utf-8")
    paths["answer"].write_text(answer_markdown, encoding="utf-8")
    paths["reference"].write_text(problem.reference_solution_cpp17, encoding="utf-8")
    paths["brute"].write_text(problem.brute_force_solution_python, encoding="utf-8")
    paths["generator"].write_text(problem.hidden_test_generator_python, encoding="utf-8")
    files = list(paths.values())
    metadata.generated_files = [safe_relative(path, root.parent.parent) for path in files]
    metadata.updated_at = utc_now_iso()
    write_json(paths["metadata"], dump_model(metadata))
    write_json(paths["verification"], verification)
    return SaveResult(root=problem_root, files=files)
