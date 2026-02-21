import os
import time
from dataclasses import dataclass

import requests


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    backup_base_url: str = ""
    backup_api_key: str = ""
    backup_model: str = ""
    timeout_seconds: int = 120
    max_retries: int = 2


class OpenAICompatibleClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        base_url = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "")
        backup_base_url = os.getenv("OPENAI_BASE_URL_BACKUP", "").rstrip("/")
        backup_api_key = os.getenv("OPENAI_API_KEY_BACKUP", "")
        backup_model = os.getenv("OPENAI_MODEL_BACKUP", "")
        if not base_url or not api_key or not model:
            raise ValueError("Missing OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL")
        return cls(
            LLMConfig(
                base_url=base_url,
                api_key=api_key,
                model=model,
                backup_base_url=backup_base_url,
                backup_api_key=backup_api_key,
                backup_model=backup_model,
            )
        )

    @staticmethod
    def _endpoint(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    def _request_once(self, base_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
        url = self._endpoint(base_url)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return self._request_once(
                    self.config.base_url,
                    self.config.api_key,
                    self.config.model,
                    system_prompt,
                    user_prompt,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.config.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                else:
                    break

        if self.config.backup_api_key and self.config.backup_model:
            try:
                backup_url = self.config.backup_base_url or self.config.base_url
                return self._request_once(
                    backup_url,
                    self.config.backup_api_key,
                    self.config.backup_model,
                    system_prompt,
                    user_prompt,
                )
            except Exception as backup_exc:  # noqa: BLE001
                raise RuntimeError(f"LLM request failed on primary and backup: {backup_exc}") from backup_exc

        raise RuntimeError(f"LLM request failed: {last_error}")
