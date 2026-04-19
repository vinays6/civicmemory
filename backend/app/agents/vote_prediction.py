from __future__ import annotations

from app.llm import LLMClient
from app.models.source_db import get_vote_prediction_input
from app.prompts.templates import build_vote_prediction_prompt
from app.schemas import VotePredictionResult


class VotePredictionAgent:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()

    def predict(self, issue_query: str, member_name: str) -> dict:
        member_input = get_vote_prediction_input(issue_query, member_name)
        prompt = build_vote_prediction_prompt(issue_query, member_input)
        result = self.llm_client.complete(prompt, VotePredictionResult)
        return result.prediction.model_dump()
