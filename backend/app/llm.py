from __future__ import annotations

import json
import os
from typing import Type, TypeVar

from anthropic import Anthropic
from pydantic import BaseModel, ValidationError


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMClient:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
    ) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        self.max_retries = max_retries
        self.client = Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=base_url or os.getenv("ANTHROPIC_BASE_URL"),
        )

    def complete(self, prompt: str, schema: Type[SchemaT]) -> SchemaT:
        repair_note = ""
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=True)

        for attempt in range(1, self.max_retries + 1):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0,
                system="Respond with valid JSON only. Never include markdown, commentary, or extra text.",
                messages=[
                    {"role": "user", "content": f"{prompt}\n\n{repair_note}".strip()},
                ],
            )
            print(response)

            content = self._extract_text(response).strip()
            content = self._strip_code_fences(content)

            try:
                data = json.loads(content)
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
