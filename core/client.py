from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from . import config

@dataclass
class ChatResult:
    status_code: int
    content: str
    elapsed: float
    finish_reason: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    body: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status_code == 200

    @property
    def total_tokens(self) -> int:
        try:
            return int(self.usage.get("total_tokens") or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def error_message(self) -> str:
        error = self.body.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)[:300]
        return str(self.body)[:300]


class DeepseekClient:

    mode = "real"

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None, timeout: float | None = None) -> None:
        self.api_key = api_key if api_key is not None else config.API_KEY
        self.base_url = base_url or config.BASE_URL
        self.model = model or config.MODEL_NAME
        self.timeout = timeout or config.TIMEOUT
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        })

        retry = Retry(
            total=3,
            connect=3,
            read=2,
            status=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=None,
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def ask(self, question: str, *, system: str | None = None,
            response_format: dict | None = None, case_id: str | None = None,
            temperature: float | None = None, max_tokens: int | None = None,
            model: str | None = None) -> ChatResult:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": question})

        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": config.TEMPERATURE if temperature is None else temperature,
            "max_tokens": config.MAX_TOKENS if max_tokens is None else max_tokens,
            "stream": False,
        }
        if response_format:
            payload["response_format"] = response_format
        response = self.session.post(
            self.base_url, json=payload, timeout=(10, self.timeout)
        )

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:300]}
        if not isinstance(body, dict):
            body = {"raw": body}

        choices = body.get("choices") or [{}]
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") or {}

        return ChatResult(
            status_code=response.status_code,
            content=(message.get("content") or "").strip(),
            elapsed=response.elapsed.total_seconds() if response.elapsed else 0.0,
            finish_reason=choice.get("finish_reason"),
            usage=body.get("usage") or {},
            request_id=response.headers.get("x-request-id"),
            body=body,
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "DeepseekClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
