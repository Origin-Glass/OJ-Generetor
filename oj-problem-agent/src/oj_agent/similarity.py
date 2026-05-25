from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import SimilarityConfig


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def ngrams(text: str, n: int) -> set[str]:
    norm = normalize_text(text)
    if len(norm) <= n:
        return {norm} if norm else set()
    return {norm[i : i + n] for i in range(len(norm) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class SimilarityResult:
    blocked: bool
    score: float
    reason: str
    matched_title: str | None = None


class SimilarityChecker:
    def __init__(self, config: SimilarityConfig, root: Path) -> None:
        self.config = config
        self.root = root
        self.records: list[dict[str, str]] = []
        self.warning: str | None = None
        self._load()

    def _load(self) -> None:
        path = self.root / self.config.dataset_path
        if not self.config.enabled:
            return
        if not path.exists():
            self.warning = f"Similarity dataset missing: {path}"
            if self.config.require_dataset:
                raise FileNotFoundError(self.warning)
            return
        with path.open("r", encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i >= self.config.sample_size:
                    break
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                title = str(row.get("title", ""))
                statement = str(row.get("problem_statement") or row.get("description") or row.get("statement") or "")
                self.records.append({"title": title, "statement": statement})

    def check(self, title: str, statement: str) -> SimilarityResult:
        if not self.config.enabled or not self.records:
            return SimilarityResult(False, 0.0, self.warning or "similarity disabled or empty dataset")
        title_norm = normalize_text(title)
        generated = ngrams(statement, self.config.ngram_size)
        best_score = 0.0
        best_title: str | None = None
        for record in self.records:
            candidate_title = normalize_text(record["title"])
            if self.config.title_exact_match_block and title_norm and title_norm == candidate_title:
                return SimilarityResult(True, 1.0, "exact title match", record["title"])
            score = jaccard(generated, ngrams(record["statement"], self.config.ngram_size))
            if score > best_score:
                best_score = score
                best_title = record["title"]
        if best_score > self.config.max_allowed_jaccard:
            return SimilarityResult(True, best_score, "statement too similar", best_title)
        return SimilarityResult(False, best_score, "ok", best_title)
