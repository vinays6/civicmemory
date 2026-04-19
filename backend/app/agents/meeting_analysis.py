from __future__ import annotations

from app.llm import LLMClient
from app.models.db import replace_meeting_member_summaries, upsert_meeting
from app.prompts.templates import build_meeting_analysis_prompt
from app.schemas import MeetingAnalysisResult, MemberMeetingSummary


class MeetingAnalysisAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def analyze(self, meeting_transcript: dict, councilmembers: list[dict]) -> MeetingAnalysisResult:
        prompt = build_meeting_analysis_prompt(meeting_transcript, councilmembers)
        result = self.llm_client.complete(prompt, MeetingAnalysisResult)
        print(result)

        normalized_by_name = {summary.member_name: summary for summary in result.member_summaries}
        completed_summaries = []
        for member in councilmembers:
            summary = normalized_by_name.get(member["name"])
            if summary is None:
                summary = MemberMeetingSummary(member_name=member["name"], topics=[])
            completed_summaries.append(summary)

        normalized_result = MeetingAnalysisResult(
            meeting_id=meeting_transcript["meeting_id"],
            member_summaries=completed_summaries,
        )

        upsert_meeting(
            meeting_id=meeting_transcript["meeting_id"],
            date=meeting_transcript["date"],
            transcript=meeting_transcript["transcript"],
        )
        replace_meeting_member_summaries(
            meeting_id=meeting_transcript["meeting_id"],
            member_summaries=[summary.model_dump() for summary in normalized_result.member_summaries],
        )

        return normalized_result

