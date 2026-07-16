from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


@dataclass
class LLMSettings:
    enabled: bool = False
    provider: str = "mock"
    base_url: str = ""
    api_key: str = ""
    model: str = "mock-model"
    temperature: float = 0.7
    max_tokens: int = 300
    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_delay_seconds: float = 0.35

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            enabled=_env_bool("ENABLE_LLM", False),
            provider=os.getenv("LLM_PROVIDER", "mock").strip().lower() or "mock",
            base_url=os.getenv("LLM_BASE_URL", "").strip(),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            model=os.getenv("LLM_MODEL", "mock-model").strip() or "mock-model",
            temperature=_env_float("LLM_TEMPERATURE", 0.7, 0.0, 2.0),
            max_tokens=_env_int("LLM_MAX_TOKENS", 300, 32, 2000),
            timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 30.0, 1.0, 120.0),
            max_retries=_env_int("LLM_MAX_RETRIES", 1, 0, 4),
            retry_delay_seconds=_env_float(
                "LLM_RETRY_DELAY_SECONDS", 0.35, 0.0, 5.0
            ),
        )

    def is_configured(self) -> bool:
        if self.provider == "mock":
            return True
        return bool(self.base_url and self.api_key and self.model)


@dataclass
class LLMGeneration:
    text: str
    used_llm: bool
    provider: str
    model: str
    fallback_reason: str = ""
    raw_response_text: str = ""
    validation_attempts: list[dict[str, object]] = field(default_factory=list)
    validation_failure_id: str = ""


class LLMClient:
    def __init__(
        self,
        settings: Optional[LLMSettings] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self._transport = transport

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.settings.enabled,
            "provider": self.settings.provider,
            "model": self.settings.model,
            "configured": self.settings.is_configured(),
            "base_url": self.settings.base_url,
        }

    def generate_json_text(
        self,
        system_prompt: str,
        context: dict[str, object],
        fallback_text: str,
        max_attempts: Optional[int] = None,
    ) -> LLMGeneration:
        if not self.settings.enabled:
            return self._fallback(fallback_text, "LLM is disabled")
        if self.settings.provider == "mock":
            return self._fallback(fallback_text, "mock provider uses deterministic rule text")
        if not self.settings.is_configured():
            return self._fallback(fallback_text, "LLM provider is not fully configured")

        attempts = (
            max(1, max_attempts)
            if max_attempts is not None
            else self.settings.max_retries + 1
        )
        last_error = "unknown LLM error"
        attempts_made = 0
        raw_response_text = ""
        for attempt in range(attempts):
            attempts_made = attempt + 1
            try:
                response_data = self._request_chat_completion(system_prompt, context)
                content = _extract_response_content(response_data)
                raw_response_text = content
                parsed = _parse_json_object(content)
                generated_text = str(parsed.get("text", "")).strip()
                if not generated_text:
                    raise ValueError("LLM JSON did not contain text")
                if "\ufffd" in generated_text:
                    raise ValueError("LLM text contained a replacement character")
                return LLMGeneration(
                    text=generated_text,
                    used_llm=True,
                    provider=self.settings.provider,
                    model=self.settings.model,
                    raw_response_text=content,
                )
            except (
                httpx.HTTPError,
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt + 1 >= attempts or not _is_retryable_error(exc):
                    break
                delay = self.settings.retry_delay_seconds * (2**attempt)
                if delay > 0:
                    time.sleep(delay)

        return self._fallback(
            fallback_text,
            f"{last_error} after {attempts_made} attempt(s)",
            raw_response_text,
        )

    def _request_chat_completion(
        self,
        system_prompt: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }
        if self.settings.provider == "deepseek":
            payload["thinking"] = {"type": "disabled"}
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(
            timeout=self.settings.timeout_seconds,
            transport=self._transport,
        ) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
        if not isinstance(response_data, dict):
            raise TypeError("LLM response must be a JSON object")
        return response_data

    def _fallback(
        self,
        text: str,
        reason: str,
        raw_response_text: str = "",
    ) -> LLMGeneration:
        return LLMGeneration(
            text=text,
            used_llm=False,
            provider=self.settings.provider,
            model=self.settings.model,
            fallback_reason=reason,
            raw_response_text=raw_response_text,
        )


def _extract_response_content(response_data: dict[str, object]) -> str:
    choices = response_data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise KeyError("LLM response did not contain choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise TypeError("LLM choice must be a JSON object")
    if first_choice.get("finish_reason") == "length":
        raise ValueError("LLM output reached the token limit")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise TypeError("LLM choice did not contain a message")
    content = message.get("content")
    if not isinstance(content, str):
        raise TypeError("LLM message content must be text")
    return content


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code in {408, 409, 425, 429} or status_code >= 500
    if isinstance(exc, httpx.HTTPError):
        return True
    return isinstance(exc, (json.JSONDecodeError, KeyError, TypeError, ValueError))


def _parse_json_object(content: str) -> dict[str, object]:
    normalized = content.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()
    parsed = json.loads(normalized)
    if not isinstance(parsed, dict):
        raise TypeError("LLM content must decode to a JSON object")
    return parsed


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


LLM_CLIENT = LLMClient()
