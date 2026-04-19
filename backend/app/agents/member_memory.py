from __future__ import annotations

import json

from app.llm import LLMClient
from app.models.db import get_member_summaries, upsert_member_profile
from app.prompts.templates import build_member_memory_prompt
from app.schemas import MemberProfile


class MemberMemoryAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def build_profile(self, member_name: str) -> MemberProfile:
        summary_rows = get_member_summaries(member_name)
        if not summary_rows:
            raise ValueError(f"No meeting summaries found for member '{member_name}'.")

        summaries = []
        for row in summary_rows:
            summary = json.loads(row.summary_json)
            summaries.append(
                {
                    "meeting_id": row.meeting_id,
                    "member_summary": summary,
                }
            )

        prompt = build_member_memory_prompt(member_name, summaries)
        profile = self.llm_client.complete(prompt, MemberProfile)
        normalized_profile = profile.model_copy(update={"member_name": member_name})

        upsert_member_profile(member_name, normalized_profile.model_dump())
        return normalized_profile

