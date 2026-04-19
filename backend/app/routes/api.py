from __future__ import annotations

from urllib.parse import unquote

from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

from app.agents.member_memory import MemberMemoryAgent
from app.agents.vote_prediction import VotePredictionAgent
from app.llm import LLMClient
from app.schemas import PredictVoteRequest


api_bp = Blueprint("api", __name__)

llm_client = LLMClient()
member_memory_agent = MemberMemoryAgent(llm_client=llm_client)
vote_prediction_agent = VotePredictionAgent(llm_client=llm_client, member_memory_agent=member_memory_agent)


@api_bp.errorhandler(BadRequest)
def handle_bad_request(error: BadRequest):
    return jsonify({"error": "Request body must be valid JSON", "details": str(error)}), 400


@api_bp.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError):
    return jsonify({"error": "Invalid request payload", "details": error.errors()}), 400


@api_bp.errorhandler(ValueError)
def handle_value_error(error: ValueError):
    return jsonify({"error": str(error)}), 400


@api_bp.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    return jsonify({"error": "Internal server error", "details": str(error)}), 500


@api_bp.post("/members/<path:member_name>/build-profile")
def build_member_profile(member_name: str):
    decoded_name = unquote(member_name)
    profile = member_memory_agent.build_profile(decoded_name)
    return jsonify(profile.model_dump()), 200


@api_bp.post("/predict-vote")
def predict_vote():
    payload = PredictVoteRequest.model_validate(request.get_json(force=True))
    predictions = vote_prediction_agent.predict(payload.issue)
    return jsonify(predictions), 200
