from __future__ import annotations

from app.llm import LLMClient
from app.prompts.templates import build_member_memory_prompt
from app.schemas import MemberProfile
from db import get_member_opinions, upsert_member_profile


class MemberMemoryAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def build_profile(self, member_name: str) -> MemberProfile:
        opinions = get_member_opinions(member_name)
        if not opinions:
            raise ValueError(f"No meeting opinions found for member '{member_name}'.")

        summaries = [
            {"meeting_date": row["meeting_date"], "member_summary": row["opinion"]}
            for row in opinions
        ]

        prompt = build_member_memory_prompt(member_name, summaries)
        profile = self.llm_client.complete(prompt, MemberProfile)
        normalized_profile = profile.model_copy(update={"member_name": member_name})

        upsert_member_profile(member_name, normalized_profile.model_dump())
        return normalized_profile
