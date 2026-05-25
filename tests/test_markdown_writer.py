import tempfile
import unittest
from pathlib import Path

from oj_agent.markdown_writer import render_problem_md, save_problem_bundle
from oj_agent.models import GeneratedProblem, ProblemMetadata, SampleCase


def sample_problem() -> GeneratedProblem:
    return GeneratedProblem(
        title="테스트 문제",
        slug="test-problem",
        difficulty_level=13,
        tier="Gold III",
        tags=["dynamic programming", "greedy"],
        is_bonus=False,
        problem_statement="문제 설명입니다.",
        input_description="입력 설명입니다.",
        output_description="출력 설명입니다.",
        constraints=["1 <= N <= 10"],
        samples=[SampleCase(input="1\n", output="1\n", explanation="설명")],
        intended_solution="풀이",
        correctness_argument="증명",
        time_complexity="O(N)",
        memory_complexity="O(1)",
        reference_solution_cpp17="int main(){return 0;}\n",
        brute_force_solution_python="print(input().strip())\n",
        hidden_test_generator_python="print('[{\"input\":\"1\\\\n\"}]')\n",
    )


class MarkdownWriterTest(unittest.TestCase):
    def test_render_problem_contains_required_sections(self) -> None:
        problem = sample_problem()
        metadata = ProblemMetadata(
            slot_id="L13-001",
            title=problem.title,
            slug=problem.slug,
            level=13,
            tier="Gold III",
            tags=problem.tags,
            bonus=False,
            model_info={"model": "test"},
            verification_rounds=5,
            revision_attempts=0,
            final_status="accepted",
        )
        text = render_problem_md(problem, metadata)
        self.assertIn("## 문제", text)
        self.assertIn("## 입력", text)
        self.assertIn("## 출력", text)
        self.assertIn("## 예제 1", text)

    def test_save_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            problem = sample_problem()
            metadata = ProblemMetadata(
                slot_id="L13-001",
                title=problem.title,
                slug=problem.slug,
                level=13,
                tier="Gold III",
                tags=problem.tags,
                bonus=False,
                model_info={"model": "test"},
                verification_rounds=5,
                revision_attempts=0,
                final_status="accepted",
            )
            result = save_problem_bundle(Path(tmp), problem, metadata, {"ok": True}, "# answer\n")
            self.assertTrue((result.root / "problem.md").exists())
            self.assertTrue((result.root / "solutions" / "reference.cpp").exists())


if __name__ == "__main__":
    unittest.main()
