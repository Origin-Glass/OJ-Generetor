from __future__ import annotations

from .llm_client import LLMClient
from .models import AnswerContent, ChatMessage, GeneratedProblem, TaskSlot
from .prompts import answer_prompt


class AnswerWriter:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def write(self, problem: GeneratedProblem, slot: TaskSlot, verification_summary: dict, max_tokens: int) -> str:
        data = self.llm.json_chat(
            [
                ChatMessage(role="system", content="You write accepted online judge solution documents. JSON only."),
                ChatMessage(role="user", content=answer_prompt(problem, slot, verification_summary)),
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return AnswerContent(**data).markdown_content
