from __future__ import annotations

import json
from typing import Iterable


def build_meeting_analysis_prompt(meeting: dict, councilmembers: Iterable[dict]) -> str:
    names = [m["name"] for m in councilmembers]
    return (
        "You are the Meeting Analysis Agent for CivicMemory.\n"
        "Extract only evidence grounded in the transcript. Do not hallucinate facts, speakers, quotes, "
        "commitments, or vote intent. If evidence is weak, lower confidence or leave fields empty.\n"
        "Rules:\n"
        "- Use only the provided councilmember list.\n"
        "- Include every listed councilmember once, even if they barely spoke.\n"
        "- Keep issues short and normalized.\n"
        "- Quotes must be copied or lightly cleaned from the transcript, not invented.\n\n"
        f"Councilmembers: {', '.join(names)}\n\n"
        f"Meeting date: {meeting['date']}\n\n"
        f"Transcript:\n{meeting['transcript']}"
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
        "- `evidence_meetings` must reference only meeting dates from the input.\n"
        "- Confidence and commitment_reliability must be between 0 and 1.\n"
        "- Themes and ideology_dimensions should be concise phrases.\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
    )


def build_vote_prediction_prompt(issue_query: str, member_profiles: list[dict]) -> str:
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
        f"Member profiles:\n{json.dumps(member_profiles, ensure_ascii=True, separators=(',', ':'))}\n\n"
        f"Issue:\n{issue_query}"
    )
