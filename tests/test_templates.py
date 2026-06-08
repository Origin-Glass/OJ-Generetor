import tempfile
import unittest
from pathlib import Path

from oj_agent.config import AppConfig, GenerationConfig, GitConfig, GithubConfig, LLMConfig, SimilarityConfig, VerificationConfig
from oj_agent.llm_client import LLMClient
from oj_agent.models import TaskSlot
from oj_agent.similarity import SimilarityChecker
from oj_agent.task_planner import level_to_tier
from oj_agent.templates import template_problem_for_slot
from oj_agent.verifier import ProblemVerifier


class TemplateProblemTest(unittest.TestCase):
    def _config(self, root: Path) -> AppConfig:
        return AppConfig(
            llm=LLMConfig(api_base="fake://fixture", model="fake"),
            generation=GenerationConfig(total_per_level=33, bonus_levels=[]),
            verification=VerificationConfig(compare_reference_with_bruteforce=True),
            similarity=SimilarityConfig(enabled=False, require_dataset=False),
            git=GitConfig(enabled=False, commit_each_problem=False, push_after_commit=False),
            github=GithubConfig(),
            project_root=root,
        )

    def test_low_level_template_verifies_without_llm_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slot = TaskSlot(
                slot_id="L01-017",
                level=1,
                tier=level_to_tier(1),
                index=17,
                bonus=False,
                tags=["string", "parsing"],
                topic_hint="string parsing",
                avoid_topics=["A+B", "두 수의 합"],
            )
            config = self._config(Path(tmp))
            problem = template_problem_for_slot(slot)

            report = ProblemVerifier(config, LLMClient(config.llm), SimilarityChecker(config.similarity, config.project_root)).verify(problem, slot)

            self.assertEqual(report.final_verdict, "ACCEPT")
            self.assertTrue(all("LLM" not in round_result.name for round_result in report.rounds))
            self.assertNotIn("A+B", problem.problem_statement)
            self.assertNotIn("두 수의 합", problem.problem_statement)


if __name__ == "__main__":
    unittest.main()
