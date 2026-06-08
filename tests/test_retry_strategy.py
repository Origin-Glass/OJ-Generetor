import unittest

from oj_agent.main import should_regenerate_after_issues


class RetryStrategyTest(unittest.TestCase):
    def test_regenerates_for_degenerate_sum_and_invalid_json(self) -> None:
        self.assertTrue(should_regenerate_after_issues(["diversity guardrail violated: low-level problem degenerates to two-number sum/A+B"]))
        self.assertTrue(should_regenerate_after_issues(["exception: ValueError: No valid JSON object found"]))

    def test_regenerates_for_execution_failures_after_first_revision(self) -> None:
        self.assertFalse(should_regenerate_after_issues(["sample 1 mismatch or runtime error"], attempt=0))
        self.assertTrue(should_regenerate_after_issues(["sample 1 mismatch or runtime error"], attempt=1))
        self.assertTrue(should_regenerate_after_issues(["C++17 compilation failed"], attempt=1))

    def test_keeps_revision_for_ambiguous_statement(self) -> None:
        self.assertFalse(should_regenerate_after_issues(["Input format is ambiguous and should be clarified"], attempt=0))


if __name__ == "__main__":
    unittest.main()
