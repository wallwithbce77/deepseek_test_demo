from __future__ import annotations
import json
import random
import time
from . import dataset
from .client import ChatResult

_SAMPLE_VALUES = {
    "string": "示例值",
    "integer": 1,
    "number": 1.5,
    "boolean": True,
    "array": [],
    "object": {},
    "null": None,
}

class FakeClient:
    mode = "fake"
    model = "fake-oracle"
    base_url = "fake://local"

    def __init__(self, error_rate: float = 0.0, seed: int = 7) -> None:
        self.error_rate = max(0.0, min(1.0, float(error_rate)))
        self._random = random.Random(seed)
        self._cases = dataset.load_all()

    def ask(self, question: str, *, system: str | None = None,
            response_format: dict | None = None, case_id: str | None = None,
            temperature: float | None = None, max_tokens: int | None = None,
            model: str | None = None) -> ChatResult:
        started = time.perf_counter()
        content = self._answer(case_id, response_format)
        if self.error_rate and self._random.random() < self.error_rate:#随机破坏
            content = self._corrupt(content)
        elapsed = time.perf_counter() - started + 0.05 + (len(content) % 10) / 100.0
        return ChatResult(
            status_code=200,
            content=content,
            elapsed=round(elapsed, 3),
            finish_reason="stop",
            usage={"prompt_tokens": 120, "completion_tokens": max(4, len(content) // 2),
                   "total_tokens": 120 + max(4, len(content) // 2)},
            request_id="fake-request",
            body={"object": "chat.completion"},
        )

    def _answer(self, case_id: str | None, response_format: dict | None) -> str:
        entry = self._cases.get(case_id or "")
        if entry is None:
            if response_format and response_format.get("type") == "json_object":
                return '{"status": "ok"}'
            return "好的，我明白了。"

        if entry["kind"] == "extraction":
            return json.dumps(entry["case"]["expected"], ensure_ascii=False)
        case = entry["case"]
        checks = case.get("checks") or []
        expected = case.get("expected")

        if "refusal" in checks:
            return "抱歉，我不能提供这个信息。"
        if "json_fields" in checks and isinstance(expected, dict):
            payload = {key: _SAMPLE_VALUES.get(str(kind), "示例值") for key, kind in expected.items()}
            return json.dumps(payload, ensure_ascii=False)
        if "numbered_steps" in checks:
            count = expected if isinstance(expected, int) else 3
            return "\n".join(f"{index}. 第{index}步的操作说明" for index in range(1, count + 1))
        if "length_at_most" in checks or "length_less_than_30" in checks:
            return "这是一个简短的回答。"
        if "grounded_answer" in checks or "contains_expected" in checks:
            if isinstance(expected, list):
                return str(expected[0])
            return str(expected)
        if isinstance(expected, (str, int, float)):
            return str(expected)
        return "好的，我明白了。"

    def _corrupt(self, content: str) -> str:
        if self._random.random() < 0.5:
            if content.lstrip().startswith("{"):
                return content[: max(1, len(content) // 2)]
            return "（本次回答被截断）"

        try:
            data = json.loads(content)
        except ValueError:
            return "（本次回答被截断）"

        if isinstance(data, dict) and data:
            key = self._random.choice(list(data))
            data[key] = None
            return json.dumps(data, ensure_ascii=False)

        return "（本次回答被截断）"

    def close(self) -> None:
        return None
