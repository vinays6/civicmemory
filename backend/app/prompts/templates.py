from __future__ import annotations

import json
from typing import Iterable


def build_meeting_analysis_chunk_prompt(
    meeting: dict,
    councilmembers: Iterable[dict],
    transcript_chunk: str,
    chunk_index: int,
    total_chunks: int,
) -> str:
    payload = {
        "meeting": {
            "meeting_id": meeting["meeting_id"],
            "date": meeting["date"],
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
        },
        "councilmembers": list(councilmembers),
        "transcript_chunk": transcript_chunk,
    }
    return (
        "You are the Meeting Analysis Agent for CivicMemory.\n"
        "Analyze only the provided transcript chunk. Extract only evidence grounded in that chunk. "
        "Do not hallucinate facts, speakers, quotes, commitments, or vote intent.\n"
        "Return valid JSON only that matches the schema exactly.\n"
        "Rules:\n"
        "- Use only the provided councilmember list.\n"
        "- Include only councilmembers with evidence in this chunk. If no listed councilmember has evidence, return an empty member_summaries array.\n"
        "- Keep issues short and normalized.\n"
        "- Confidence must be between 0 and 1.\n"
        "- `vote_signal` must be one of yes, no, abstain, unclear, unknown.\n"
        "- Quotes must be copied or lightly cleaned from the transcript, not invented.\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
    )


def build_member_memory_prompt(member_name: str, summaries: list[dict]) -> str:
    payload = {
        "member_name": member_name,
        "meeting_summaries": summaries,
    }
    return (
        "You are the Member Memory Agent for CivicMemory.\n"
        "Build a persistent political memory profile using only the supplied meeting evidence. "
        "Do not hallucinate missing history or ideology. If evidence is mixed, say so in stance/confidence.\n"
        "Return valid JSON only that matches the schema exactly.\n"
        "Rules:\n"
        "- Aggregate recurring issues across meetings.\n"
        "- `issue_positions` keys should be normalized issue names.\n"
        "- `evidence_meetings` must reference only meeting ids from the input.\n"
        "- Confidence and commitment_reliability must be between 0 and 1.\n"
        "- Themes and ideology_dimensions should be concise phrases.\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
    )


def build_vote_prediction_prompt(issue_query: str, member_profiles: list[dict]) -> str:
    payload = {
        "issue_query": issue_query,
        "member_profiles": member_profiles,
    }
    return (
        "You are the Vote Prediction Agent for CivicMemory.\n"
        "Predict likely votes using only the stored member profiles and cited meeting evidence. "
        "Do not invent facts outside this memory. Use issue similarity heuristics conservatively.\n"
        "Return valid JSON only that matches the schema exactly.\n"
        "Rules:\n"
        "- One prediction per member profile.\n"
        "- `predicted_vote` must be one of yes, no, abstain, unclear.\n"
        "- Confidence must be between 0 and 1.\n"
        "- Reasoning must be brief and cite the stored evidence in plain language.\n"
        "- `evidence_meetings` must come from the profile's evidence_meetings values.\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
    )
