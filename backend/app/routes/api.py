from __future__ import annotations

import re
from urllib.parse import unquote

from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

from app.agents.member_memory import MemberMemoryAgent
from app.agents.vote_prediction import VotePredictionAgent
from app.llm import LLMClient
from app.schemas import PredictVoteRequest
from db import (
    DEFAULT_DB_PATH,
    get_member_opinions,
    get_member_profile,
    get_member_votes,
    list_member_summaries,
)
import numpy as np

from analyze_votes import (
    MIN_OVERLAP,
    _cluster,
    controversial_items,
    kingmaker_score,
    load_votes,
    member_stats,
    precompute_matrices,
)


TIMESTAMP_RE = re.compile(r"\[?(\d{1,2}):(\d{2}):(\d{2})\]?")


def _ts_to_seconds(ts: str) -> int | None:
    m = TIMESTAMP_RE.search(ts)
    if not m:
        return None
    h, mm, s = (int(x) for x in m.groups())
    return h * 3600 + mm * 60 + s


def _youtube_link(video_id: str, ts: str) -> str | None:
    secs = _ts_to_seconds(ts)
    if secs is None:
        return None
    return f"https://www.youtube.com/watch?v={video_id}&t={secs}s"


api_bp = Blueprint("api", __name__)

_votes_cache: dict | None = None


def _votes_bundle() -> dict:
    global _votes_cache
    if _votes_cache is None:
        members, by_item, items_meta = load_votes(DEFAULT_DB_PATH)
        matrices = precompute_matrices(members, by_item)
        _votes_cache = {
            "members": members,
            "by_item": by_item,
            "items_meta": items_meta,
            "matrices": matrices,
        }
    return _votes_cache


llm_client = LLMClient()
member_memory_agent = MemberMemoryAgent(llm_client=llm_client)
vote_prediction_agent = VotePredictionAgent(llm_client=llm_client)


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


@api_bp.get("/members")
def list_members_route():
    """List all councilmembers with aggregate counts across opinions, votes,
    and attendance, plus the set of issues each has spoken on."""
    return jsonify(list_member_summaries()), 200


@api_bp.get("/members/<path:member_name>/votes")
def get_member_votes_route(member_name: str):
    """Full per-item voting history for a canonical member (alias-aware)."""
    decoded_name = unquote(member_name)
    return jsonify(get_member_votes(decoded_name)), 200


@api_bp.get("/members/<path:member_name>/opinions")
def get_member_opinions_route(member_name: str):
    """Return one entry per topic the member has spoken on, across all
    meetings, with timestamped YouTube links back to the source video."""
    decoded_name = unquote(member_name)
    rows = get_member_opinions(decoded_name)

    out = []
    for row in rows:
        video_id = row.get("video_id")
        for topic in row["opinion"].get("topics", []):
            links = []
            if video_id:
                links = [
                    url for ts in topic.get("timestamps", [])
                    if (url := _youtube_link(video_id, ts)) is not None
                ]
            out.append({
                "meeting_date": row["meeting_date"],
                "issue": topic.get("issue"),
                "stance": topic.get("stance"),
                "sentiment": topic.get("sentiment"),
                "youtube_links": links,
            })
    return jsonify(out), 200


@api_bp.get("/members/<path:member_name>/stats")
def get_member_stats_route(member_name: str):
    """Per-member voting analytics: counts, rates, lone-wolf items,
    top co-dissent partners, alignment row, and kingmaker flips."""
    decoded_name = unquote(member_name)
    bundle = _votes_bundle()
    stats = member_stats(
        decoded_name,
        bundle["members"],
        bundle["by_item"],
        bundle["items_meta"],
        bundle["matrices"],
    )
    kingmaker = kingmaker_score(decoded_name, bundle["members"], bundle["by_item"])
    return jsonify({**stats, "kingmaker": kingmaker}), 200


@api_bp.get("/members/<path:member_name>/profile")
def get_member_profile_route(member_name: str):
    """Read-only fetch of a stored MemberProfile. 404 if not built yet."""
    decoded_name = unquote(member_name)
    row = get_member_profile(decoded_name)
    if row is None:
        return jsonify({"error": "No profile built yet for this member."}), 404
    return jsonify({
        "member_canonical": row["member_canonical"],
        "profile": row["profile"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }), 200


@api_bp.get("/voting-network")
def get_voting_network_route():
    """Return a graph of councilmembers linked by contested-vote agreement.

    Query params:
      - k (int, default 3): number of blocs for hierarchical clustering
      - min_n (int, default MIN_OVERLAP): minimum co-participation for an edge
    """
    try:
        k = int(request.args.get("k", 3))
    except ValueError:
        k = 3
    try:
        min_n = int(request.args.get("min_n", MIN_OVERLAP))
    except ValueError:
        min_n = MIN_OVERLAP

    bundle = _votes_bundle()
    members: list[str] = bundle["members"]
    matrices = bundle["matrices"]
    rate = matrices["agreement_contested"]
    total = matrices["agreement_contested_total"]

    try:
        blocs = _cluster(members, rate, total, k)
    except ValueError:
        # Fall back to non-contested matrices if contested-only has sparse overlap.
        rate = matrices["agreement"]
        total = matrices["agreement_total"]
        blocs = _cluster(members, rate, total, k)

    edges = []
    n = len(members)
    for i in range(n):
        for j in range(i + 1, n):
            r = rate[i, j]
            t = int(total[i, j])
            if t < min_n or np.isnan(r):
                continue
            edges.append({
                "a": members[i],
                "b": members[j],
                "rate": float(r),
                "n": t,
            })

    return jsonify({
        "members": members,
        "blocs": blocs,
        "edges": edges,
    }), 200


@api_bp.get("/controversial-items")
def get_controversial_items_route():
    """Closest-margin items across the dataset."""
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10
    bundle = _votes_bundle()
    return jsonify(controversial_items(bundle["by_item"], bundle["items_meta"], limit=limit)), 200


@api_bp.post("/members/<path:member_name>/build-profile")
def build_member_profile(member_name: str):
    decoded_name = unquote(member_name)
    profile = member_memory_agent.build_profile(decoded_name)
    return jsonify(profile.model_dump()), 200


@api_bp.post("/predict-vote")
def predict_vote():
    payload = PredictVoteRequest.model_validate(request.get_json(force=True))
    prediction = vote_prediction_agent.predict(payload.issue, payload.member_name)
    return jsonify(prediction), 200
