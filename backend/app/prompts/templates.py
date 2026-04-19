from __future__ import annotations

import json
from typing import Iterable


def build_meeting_analysis_prompt(meeting: dict, councilmembers: Iterable[dict]) -> str:
    names = [m["name"] for m in councilmembers]
    return (
        "Extract council member stances from the transcript.\n"
        "- Only include councilmembers from the provided list who made substantive remarks. "
        "Skip members who did not speak or only made procedural remarks.\n"
        "- `issue` is a GENERAL policy area (e.g. \"Public Safety\", \"Housing\", "
        "\"Transportation\", \"Budget\", \"Labor\", \"Environment\", \"Homelessness\", "
        "\"Infrastructure\", \"Appointments\"). Never a motion title or item number.\n"
        "- `stance` is one sentence describing their position.\n"
        "- `sentiment` is positive (supportive), negative (opposed), neutral, or mixed.\n"
        "- `timestamps` are the exact `[HH:MM:SS]` markers preceding their relevant "
        "speaker turns. Do not invent.\n"
        "- One topic entry per distinct issue per member.\n\n"
        f"Councilmembers: {', '.join(names)}\n\n"
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


def build_vote_prediction_prompt(issue_query: str, member_inputs: list[dict]) -> str:
    payload = {
        "issue_query": issue_query,
        "members": member_inputs,
    }
    return (
        "You are the Vote Prediction Agent for CivicMemory.\n"
        "Predict likely votes using only the supplied campaign profile, finance summary, and actual council voting record. "
        "Treat direct voting evidence as the strongest signal, campaign promises as the next strongest signal, and finance patterns as a weak indirect signal. "
        "Do not invent facts outside this evidence.\n"
        "Return valid JSON only that matches the schema exactly.\n"
        "Rules:\n"
        "- One prediction per member.\n"
        "- `predicted_vote` must be one of yes, no, abstain, unclear.\n"
        "- Confidence must be between 0 and 1.\n"
        "- Prefer `unclear` when evidence is weak, mixed, or off-topic.\n"
        "- Reasoning must be brief and reference the member's relevant votes, campaign priorities, or both in plain language.\n"
        "- `evidence_meetings` must contain only vote references from the input in the form `YYYY-MM-DD#item_number`.\n"
        "- If no relevant vote references are available, return an empty `evidence_meetings` list.\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
    )
