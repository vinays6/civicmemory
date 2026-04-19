from __future__ import annotations

import json

from app.agents.member_memory import MemberMemoryAgent
from app.llm import LLMClient
from app.models.db import get_all_member_profiles, get_distinct_member_names
from app.prompts.templates import build_vote_prediction_prompt
from app.schemas import VotePredictionResult


class VotePredictionAgent:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        member_memory_agent: MemberMemoryAgent | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.member_memory_agent = member_memory_agent or MemberMemoryAgent(self.llm_client)

    def predict(self, issue_query: str) -> list[dict]:
        profile_rows = get_all_member_profiles()
        member_names = get_distinct_member_names()
        if not member_names and not profile_rows:
            raise ValueError("No member profiles or meeting summaries are available for prediction.")

        existing_profile_names = {row.member_name for row in profile_rows}
        missing_profile_names = [name for name in member_names if name not in existing_profile_names]
        for member_name in missing_profile_names:
            self.member_memory_agent.build_profile(member_name)

        if missing_profile_names:
            profile_rows = get_all_member_profiles()

        if not profile_rows:
            raise ValueError("No member profiles are available for prediction.")

        member_profiles = [json.loads(row.profile_json) for row in profile_rows]
        prompt = build_vote_prediction_prompt(issue_query, member_profiles)
        result = self.llm_client.complete(prompt, VotePredictionResult)
        return [prediction.model_dump() for prediction in result.predictions]
