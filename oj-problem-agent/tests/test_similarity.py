import tempfile
import unittest
from pathlib import Path

from oj_agent.config import SimilarityConfig
from oj_agent.similarity import SimilarityChecker, jaccard, ngrams


class SimilarityTest(unittest.TestCase):
    def test_jaccard(self) -> None:
        self.assertEqual(jaccard({"a"}, {"a"}), 1.0)
        self.assertEqual(jaccard({"a"}, {"b"}), 0.0)

    def test_missing_dataset_warns_and_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checker = SimilarityChecker(SimilarityConfig(require_dataset=False), Path(tmp))
            result = checker.check("title", "statement")
            self.assertFalse(result.blocked)
            self.assertEqual(result.score, 0.0)

    def test_ngrams(self) -> None:
        self.assertEqual(ngrams("abcd", 2), {"ab", "bc", "cd"})


if __name__ == "__main__":
    unittest.main()
