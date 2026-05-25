from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .config import LLMConfig
from .models import ChatMessage
from .utils import extract_json_object


class LLMClient:
    def __init__(self, config: LLMConfig, retries: int = 3) -> None:
        self.config = config
        self.retries = retries
        self.api_key = os.getenv(config.api_key_env, "")

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if self.config.api_base.startswith("fake://"):
            return self._fake_chat(messages)
        url = self._endpoint_url()
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [self._message_payload(m) for m in messages],
            "temperature": self.config.temperature if temperature is None else temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif not self._is_local_endpoint():
            raise RuntimeError(f"Missing API key in {self.config.api_key_env}")

        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                self._log_request(url, payload, attempt)
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout,
                )
                if response.status_code >= 500:
                    raise RuntimeError(f"LLM server error {response.status_code}: {response.text[:500]}")
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:
                last_error = exc
                if attempt == self.retries:
                    break
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"LLM request failed after {self.retries} attempts: {last_error}") from last_error

    def json_chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        try:
            text = self.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except RuntimeError as exc:
            if "400" not in str(exc) and "response_format" not in str(exc):
                raise
            text = self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        try:
            return extract_json_object(text)
        except Exception:
            repaired = self.chat(
                [
                    ChatMessage(role="system", content="Return valid JSON only. No markdown."),
                    ChatMessage(role="user", content=f"Repair this into one valid JSON object:\n{text}"),
                ],
                temperature=0.0,
                max_tokens=max_tokens,
            )
            return extract_json_object(repaired)

    def _endpoint_url(self) -> str:
        base = self.config.api_base.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def _message_payload(self, message: ChatMessage) -> dict[str, Any]:
        if isinstance(message.content, str):
            return {"role": message.role, "content": message.content}
        parts: list[dict[str, Any]] = []
        for part in message.content:
            if part.type == "text":
                parts.append({"type": "text", "text": part.text or ""})
            elif part.type == "image_url":
                parts.append({"type": "image_url", "image_url": {"url": part.url or ""}})
            else:
                parts.append({"type": "text", "text": f"[image_path:{part.path}]"})
        return {"role": message.role, "content": parts}

    def _is_local_endpoint(self) -> bool:
        host = urlparse(self.config.api_base).hostname or ""
        return host in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

    def _log_request(self, url: str, payload: dict[str, Any], attempt: int) -> None:
        safe_payload = {
            "model": payload.get("model"),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
            "message_count": len(payload.get("messages", [])),
            "attempt": attempt,
        }
        print(f"LLM request {self._sanitize_url(url)} {json.dumps(safe_payload, ensure_ascii=False)}")

    def _sanitize_url(self, url: str) -> str:
        parsed = urlparse(url)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        safe_query = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if any(word in key.lower() for word in ("key", "token", "secret", "password")):
                safe_query.append((key, "***"))
            else:
                safe_query.append((key, value))
        return urlunparse((parsed.scheme, netloc, parsed.path, "", urlencode(safe_query), ""))

    def _fake_chat(self, messages: list[ChatMessage]) -> str:
        content = "\n".join(str(message.content) for message in messages)
        if "Write answer.md content" in content:
            return json.dumps(
                {
                    "markdown_content": "\n".join(
                        [
                            "# 풀이",
                            "",
                            "## 접근 방향",
                            "두 정수를 읽어 합을 출력한다.",
                            "",
                            "## 핵심 관찰",
                            "필요한 값은 A+B 하나뿐이다.",
                            "",
                            "## 알고리즘 설계",
                            "입력된 두 수를 더한다.",
                            "",
                            "## 정당성 증명",
                            "덧셈 정의에 따라 출력값은 요구한 합과 같다.",
                            "",
                            "## 시간복잡도",
                            "O(1)",
                            "",
                            "## 공간복잡도",
                            "O(1)",
                            "",
                            "## 반례 검토",
                            "음수와 0을 포함한 경계 입력을 확인했다.",
                            "",
                            "## reference C++17 solution",
                            "본문의 reference.cpp를 사용한다.",
                            "",
                            "## brute force Python solution if available",
                            "본문의 brute_force.py를 사용한다.",
                            "",
                            "## hidden test generator explanation",
                            "작은 정수 쌍을 생성한다.",
                            "",
                            "## verification summary",
                            "5단계 검증을 통과했다.",
                        ]
                    )
                },
                ensure_ascii=False,
            )
        if "Generate" in content and "adversarial test" in content:
            return json.dumps(
                {
                    "tests": [
                        {"name": "zero", "reason": "0 경계", "input": "0 0\n"},
                        {"name": "negative", "reason": "음수", "input": "-5 7\n"},
                        {"name": "large", "reason": "큰 값", "input": "1000000000 -1000000000\n"},
                    ]
                },
                ensure_ascii=False,
            )
        if "adversarial reviewer" in content or "Perform final review" in content:
            return json.dumps(
                {
                    "verdict": "ACCEPT",
                    "issues": [],
                    "required_changes": [],
                    "difficulty_assessment": "level matches",
                    "tag_assessment": "tags match",
                },
                ensure_ascii=False,
            )
        slot = self._extract_slot_from_prompt(content)
        return json.dumps(
            {
                "title": "두 수의 조용한 합",
                "slug": "quiet-sum",
                "difficulty_level": slot.get("level", 1),
                "tier": slot.get("tier", "Bronze V"),
                "tags": slot.get("tags", ["implementation"]),
                "is_bonus": slot.get("bonus", False),
                "requires_diagram": False,
                "diagram_svg": "",
                "problem_statement": "정수 A와 B가 주어진다. 두 정수의 합을 출력하라.",
                "input_description": "첫째 줄에 정수 A와 B가 공백으로 구분되어 주어진다.",
                "output_description": "A+B를 출력한다.",
                "constraints": ["-1,000,000,000 <= A, B <= 1,000,000,000"],
                "samples": [{"input": "3 4\n", "output": "7\n", "explanation": "3과 4의 합은 7이다."}],
                "intended_solution": "두 정수를 읽고 합을 출력한다.",
                "correctness_argument": "프로그램은 입력된 A와 B를 그대로 더하므로 출력은 A+B이다.",
                "time_complexity": "O(1)",
                "memory_complexity": "O(1)",
                "reference_solution_cpp17": "#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(false);cin.tie(nullptr);long long a,b;if(!(cin>>a>>b)) return 0;cout<<a+b<<'\\n';return 0;}\n",
                "brute_force_solution_python": "a,b=map(int,input().split())\nprint(a+b)\n",
                "hidden_test_generator_python": "import json\nprint(json.dumps([{'input':'0 0\\n'},{'input':'-5 7\\n'},{'input':'1000000000 -1000000000\\n'}], ensure_ascii=False))\n",
                "originality_notes": "기본 입출력 검증용 신규 문제이다.",
                "validator_notes": "정수 두 개만 입력된다.",
            },
            ensure_ascii=False,
        )

    def _extract_slot_from_prompt(self, content: str) -> dict[str, Any]:
        marker = "Slot:"
        idx = content.find(marker)
        if idx == -1:
            return {}
        snippet = content[idx + len(marker) :]
        try:
            return extract_json_object(snippet)
        except Exception:
            return {}
