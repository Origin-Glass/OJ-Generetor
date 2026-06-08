from __future__ import annotations

from .llm_client import LLMClient
from .models import ChatMessage, CounterexamplePlan, GeneratedProblem, TaskSlot
from .prompts import counterexample_prompt


class CounterexampleSearcher:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate(self, problem: GeneratedProblem, slot: TaskSlot, count: int, max_tokens: int) -> CounterexamplePlan:
        data = self.llm.json_chat(
            [
                ChatMessage(role="system", content="You generate adversarial tests for OJ problems. JSON only."),
                ChatMessage(role="user", content=counterexample_prompt(problem, slot, count)),
            ],
            temperature=0.2,
            max_tokens=max_tokens,
            json_schema=CounterexamplePlan.model_json_schema(),
            schema_name="CounterexamplePlan",
        )
        return CounterexamplePlan(**data)
