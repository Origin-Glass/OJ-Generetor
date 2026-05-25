from __future__ import annotations

from .llm_client import LLMClient
from .models import ChatMessage, GeneratedProblem, TaskSlot
from .prompts import generator_prompt
from .utils import slugify


class ProblemGenerator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate(self, slot: TaskSlot, max_tokens: int | None = None) -> GeneratedProblem:
        data = self.llm.json_chat(
            [
                ChatMessage(role="system", content="You generate original Korean OJ problems. Return JSON only."),
                ChatMessage(role="user", content=generator_prompt(slot)),
            ],
            max_tokens=max_tokens,
        )
        data["difficulty_level"] = int(data.get("difficulty_level", slot.level))
        if not data.get("slug"):
            data["slug"] = slugify(str(data.get("title", slot.slot_id)), slot.slot_id.lower())
        return GeneratedProblem(**data)
