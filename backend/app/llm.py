from __future__ import annotations

import json
import os
import time
from typing import Sequence, Type, TypeVar

from anthropic import Anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from pydantic import BaseModel


SchemaT = TypeVar("SchemaT", bound=BaseModel)


_UNSUPPORTED_KEYS = {
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength",
    "minItems", "maxItems", "uniqueItems",
    "minProperties", "maxProperties",
}


def _strip_unsupported_constraints(node):
    """Remove JSON Schema keywords the Claude structured-outputs endpoint
    rejects. Pydantic still enforces them client-side on model_validate()."""
    if isinstance(node, dict):
        return {
            k: _strip_unsupported_constraints(v)
            for k, v in node.items()
            if k not in _UNSUPPORTED_KEYS
        }
    if isinstance(node, list):
        return [_strip_unsupported_constraints(x) for x in node]
    return node


class LLMClient:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4000,
    ) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7")
        self.max_tokens = max_tokens
        self.client = Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=base_url or os.getenv("ANTHROPIC_BASE_URL"),
        )

    def _create_params(self, prompt: str, schema: Type[SchemaT]) -> dict:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
            }],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": _strip_unsupported_constraints(schema.model_json_schema()),
                },
            },
        }

    def complete(self, prompt: str, schema: Type[SchemaT]) -> SchemaT:
        """Single request with server-side schema enforcement. No retry loop —
        structured outputs guarantees valid JSON matching the schema. If the
        model returns `refusal` or `max_tokens`, raises ValueError."""
        response = self.client.messages.create(**self._create_params(prompt, schema))
        if response.stop_reason in ("refusal", "max_tokens"):
            raise ValueError(f"LLM stopped with {response.stop_reason}; output may be invalid")
        text = self._extract_text(response).strip()
        return schema.model_validate(json.loads(text))

    def batch_complete(
        self,
        prompts: Sequence[str],
        schema: Type[SchemaT],
        poll_interval: float = 30.0,
    ) -> list[SchemaT | Exception]:
        """Submit many prompts via the Messages Batches API (50% discount,
        separate rate limit pool). Blocks until the batch ends, then returns
        results in input order. Failed items are returned as Exceptions in
        place — caller decides whether to re-run them through complete()."""
        if not prompts:
            return []

        requests = [
            Request(
                custom_id=f"req-{i}",
                params=MessageCreateParamsNonStreaming(**self._create_params(p, schema)),
            )
            for i, p in enumerate(prompts)
        ]
        batch = self.client.messages.batches.create(requests=requests)

        while True:
            batch = self.client.messages.batches.retrieve(batch.id)
            if batch.processing_status == "ended":
                break
            time.sleep(poll_interval)

        by_id: dict[str, SchemaT | Exception] = {}
        for result in self.client.messages.batches.results(batch.id):
            if result.result.type != "succeeded":
                by_id[result.custom_id] = RuntimeError(
                    f"batch item {result.custom_id}: {result.result.type}"
                )
                continue
            msg = result.result.message
            if msg.stop_reason in ("refusal", "max_tokens"):
                by_id[result.custom_id] = ValueError(f"stop_reason={msg.stop_reason}")
                continue
            try:
                text = self._extract_text(msg).strip()
                by_id[result.custom_id] = schema.model_validate(json.loads(text))
            except Exception as exc:
                by_id[result.custom_id] = exc

        return [by_id[f"req-{i}"] for i in range(len(prompts))]

    @staticmethod
    def _extract_text(response) -> str:
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts)
