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

    def predict(self, issue_query: str) -> list[dict]:
        member_inputs = get_vote_prediction_input(issue_query)
        prompt = build_vote_prediction_prompt(issue_query, member_inputs)
        result = self.llm_client.complete(prompt, VotePredictionResult)
        return [prediction.model_dump() for prediction in result.predictions]
