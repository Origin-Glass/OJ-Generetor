from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    api_base: str
    api_key_env: str = "OPENAI_API_KEY"
    model: str
    temperature: float = 0.75
    top_p: float = 0.9
    max_tokens: int = 8192
    timeout: int = 300


class GenerationConfig(BaseModel):
    total_per_level: int = 33
    bonus_levels: list[int] = Field(default_factory=lambda: list(range(22, 31)))
    language: str = "ko"
    output_dir: str = "generated/problems"
    metadata_dir: str = "generated/metadata"
    max_revision_attempts: int = 3
    verification_rounds: int = 5
    same_level_unique_primary_tag_combo: bool = True
    multimodal_ready: bool = True
    text_only_first_version: bool = True
    generate_svg: bool = True
    generate_hidden_tests: bool = True
    seed: int = 20260525


class VerificationEffort(BaseModel):
    random_tests: int
    llm_counterexample_tests: int
    max_hidden_tests: int
    verifier_max_tokens: int


class VerificationConfig(BaseModel):
    random_test_count_default: int = 100
    llm_counterexample_count_default: int = 20
    max_input_bytes: int = 200000
    compile_timeout_sec: int = 20
    run_timeout_sec: int = 3
    high_difficulty_run_timeout_sec: int = 8
    compare_reference_with_bruteforce: bool = True
    effort_by_level: dict[str, VerificationEffort] = Field(default_factory=dict)

    def effort_for_level(self, level: int) -> VerificationEffort:
        for key, effort in self.effort_by_level.items():
            lo, hi = [int(x) for x in key.split("-", 1)]
            if lo <= level <= hi:
                return effort
        return VerificationEffort(
            random_tests=self.random_test_count_default,
            llm_counterexample_tests=self.llm_counterexample_count_default,
            max_hidden_tests=self.random_test_count_default,
            verifier_max_tokens=8192,
        )


class SimilarityConfig(BaseModel):
    enabled: bool = True
    dataset_path: str = "data/boj_problems_indexed.jsonl"
    max_allowed_jaccard: float = 0.35
    title_exact_match_block: bool = True
    ngram_size: int = 5
    require_dataset: bool = False
    sample_size: int = 50000


class GitConfig(BaseModel):
    enabled: bool = True
    commit_each_problem: bool = True
    push_after_commit: bool = True
    remote: str = "origin"
    branch: str = "main"
    lock_ttl_minutes: int = 120
    max_push_retries: int = 5


class GithubConfig(BaseModel):
    token_env: str = "GITHUB_TOKEN"
    username_env: str = "GITHUB_USERNAME"
    email_env: str = "GITHUB_EMAIL"


class AppConfig(BaseModel):
    llm: LLMConfig
    generation: GenerationConfig
    verification: VerificationConfig
    similarity: SimilarityConfig
    git: GitConfig
    github: GithubConfig
    project_root: Path = Path(".")


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    load_dotenv()
    config_path = Path(path)
    data: dict[str, Any] = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    cfg = AppConfig(**data)
    cfg.project_root = config_path.resolve().parent
    return cfg
