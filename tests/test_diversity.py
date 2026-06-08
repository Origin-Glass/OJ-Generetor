import unittest

from oj_agent.models import GeneratedProblem, SampleCase, TaskSlot
from oj_agent.prompts import generator_prompt
from oj_agent.tag_planner import TagPlanner
from oj_agent.task_planner import TaskPlanner
from oj_agent.verifier import ProblemVerifier


class _SimilarityResult:
    blocked = False
    reason = ""
    score = 0.0
    matched_title = None


class _SimilarityStub:
    def check(self, title: str, statement: str) -> _SimilarityResult:
        return _SimilarityResult()


class DiversityPlanningTest(unittest.TestCase):
    def test_low_level_slots_have_distinct_topic_hints(self) -> None:
        slots = TagPlanner().apply(TaskPlanner(bonus_levels=()).build_plan())
        level_one = [slot for slot in slots if slot.level == 1][:8]

        hints = [slot.topic_hint for slot in level_one]

        self.assertEqual(len(hints), len(set(hints)))
        self.assertIn("string", " ".join(hints).lower())
        self.assertIn("comparison", " ".join(hints).lower())

    def test_generator_prompt_includes_diversity_guardrails(self) -> None:
        slot = TaskSlot(
            slot_id="L01-002",
            level=1,
            tier="Bronze V",
            index=2,
            bonus=False,
            tags=["arithmetic"],
            topic_hint="comparison of two numbers",
            avoid_topics=["two-number sum", "A+B", "두 수의 합"],
        )

        prompt = generator_prompt(slot)

        self.assertIn("comparison of two numbers", prompt)
        self.assertIn("두 수의 합", prompt)
        self.assertIn("Do not generate", prompt)


class LocalDiversityVerifierTest(unittest.TestCase):
    def test_rejects_duplicate_low_level_sum_problem(self) -> None:
        slot = TaskSlot(
            slot_id="L01-002",
            level=1,
            tier="Bronze V",
            index=2,
            bonus=False,
            tags=["arithmetic"],
            topic_hint="comparison of two numbers",
            avoid_topics=["two-number sum", "A+B", "두 수의 합"],
        )
        problem = GeneratedProblem(
            title="두 수의 합",
            slug="two-sum-again",
            difficulty_level=1,
            tier="Bronze V",
            tags=["arithmetic"],
            is_bonus=False,
            problem_statement="두 정수 A와 B가 주어질 때, A+B를 출력하시오.",
            input_description="첫째 줄에 A와 B가 주어진다.",
            output_description="A+B를 출력한다.",
            constraints=["1 <= A, B <= 100"],
            samples=[SampleCase(input="1 2\n", output="3\n")],
            intended_solution="A와 B를 입력받아 더한다.",
            correctness_argument="합을 직접 계산하므로 정답이다.",
            time_complexity="O(1)",
            memory_complexity="O(1)",
            reference_solution_cpp17="#include <iostream>\nusing namespace std;\nint main(){int A,B;cin>>A>>B;cout<<A+B<<'\\n';}\n",
            hidden_test_generator_python="print('1 2')\n",
        )

        issues = ProblemVerifier(None, None, _SimilarityStub())._round1(problem, slot).issues

        self.assertTrue(any("avoid" in issue.lower() or "divers" in issue.lower() for issue in issues))


if __name__ == "__main__":
    unittest.main()
