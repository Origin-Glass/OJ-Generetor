from __future__ import annotations

from .llm_client import LLMClient
from .models import ChatMessage, GeneratedProblem, TaskSlot
from .prompts import revision_prompt


class ProblemReviser:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def revise(self, problem: GeneratedProblem, slot: TaskSlot, issues: list[str], max_tokens: int) -> GeneratedProblem:
        data = self.llm.json_chat(
            [
                ChatMessage(role="system", content="You revise OJ problem JSON. Return JSON only."),
                ChatMessage(role="user", content=revision_prompt(problem, slot, issues)),
            ],
            temperature=0.4,
            max_tokens=max_tokens,
        )
        return GeneratedProblem(**data)
