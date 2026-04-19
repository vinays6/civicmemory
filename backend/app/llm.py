from __future__ import annotations

import json
import os
import time
from typing import Type, TypeVar

from anthropic import Anthropic, RateLimitError
from pydantic import BaseModel, ValidationError


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMRateLimitExceeded(RuntimeError):
    """Raised when the configured LLM provider rate limit is exceeded."""


class LLMClient:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        max_output_tokens: int | None = None,
    ) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        self.max_retries = max_retries
        self.max_output_tokens = max_output_tokens or int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1200"))
        self.client = Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=base_url or os.getenv("ANTHROPIC_BASE_URL"),
        )

    def complete(self, prompt: str, schema: Type[SchemaT]) -> SchemaT:
        repair_note = ""
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=True)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_output_tokens,
                    temperature=0,
                    system="Respond with valid JSON only. Never include markdown, commentary, or extra text.",
                    messages=[
                        {"role": "user", "content": f"{prompt}\n\n{repair_note}".strip()},
                    ],
                )
            except RateLimitError as exc:
                if attempt == self.max_retries:
                    raise LLMRateLimitExceeded(
                        "Anthropic rate limit exceeded. Retry in about a minute, reduce transcript size, "
                        "or lower chunk size/output token settings."
                    ) from exc
                time.sleep(min(60, 10 * attempt))
                continue

            content = self._extract_text(response).strip()
            content = self._strip_code_fences(content)

            try:
                data = self._parse_json_payload(content)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == self.max_retries:
                    raise ValueError(
                        f"LLM returned invalid structured output after {self.max_retries} attempts."
                    ) from exc

                error_detail = str(exc)
                repair_note = (
                    "Your previous answer did not validate.\n"
                    f"Validation error:\n{error_detail}\n"
                    "Return JSON only that matches the target schema exactly, with no additional keys and "
                    "with all confidence fields in the 0 to 1 range.\n"
                    f"Target JSON schema:\n{schema_hint}"
                )

        raise RuntimeError("LLM completion loop exited unexpectedly.")

    @staticmethod
    def _extract_text(response) -> str:
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts)

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        if content.startswith("```"):
            lines = content.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip()
        return content

    @classmethod
    def _parse_json_payload(cls, content: str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = content.find(start_char)
            end = content.rfind(end_char)
            if start == -1 or end == -1 or end <= start:
                continue
            candidate = content[start : end + 1].strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        return json.loads(content)
