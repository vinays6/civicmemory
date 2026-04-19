from __future__ import annotations

from app.llm import LLMClient
from app.prompts.templates import build_meeting_analysis_prompt
from app.schemas import MeetingAnalysisResult, MemberMeetingSummary
from db import members_for_meeting, replace_member_opinions, upsert_meeting


MEETING_ANALYSIS_MODEL = "claude-haiku-4-5"


class MeetingAnalysisAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient(model=MEETING_ANALYSIS_MODEL)

    def _normalize(
        self,
        meeting_date: str,
        result: MeetingAnalysisResult,
        names: list[str],
    ) -> MeetingAnalysisResult:
        by_name = {s.member_name: s for s in result.member_summaries}
        completed = [
            by_name.get(n) or MemberMeetingSummary(member_name=n, topics=[])
            for n in names
        ]
        return MeetingAnalysisResult(meeting_date=meeting_date, member_summaries=completed)

    def _persist(self, meeting_transcript: dict, result: MeetingAnalysisResult) -> None:
        upsert_meeting(
            meeting_date=result.meeting_date,
            transcript=meeting_transcript["transcript"],
        )
        replace_member_opinions(
            meeting_date=result.meeting_date,
            opinions=[s.model_dump() for s in result.member_summaries],
            model=self.llm_client.model,
        )

    def analyze(self, meeting_transcript: dict) -> MeetingAnalysisResult:
        names = members_for_meeting(meeting_transcript["date"])
        councilmembers = [{"name": n} for n in names]
        prompt = build_meeting_analysis_prompt(meeting_transcript, councilmembers)
        raw = self.llm_client.complete(prompt, MeetingAnalysisResult)
        result = self._normalize(meeting_transcript["date"], raw, names)
        self._persist(meeting_transcript, result)
        return result

    def analyze_batch(
        self,
        meeting_transcripts: list[dict],
    ) -> list[MeetingAnalysisResult | Exception]:
        """Submit many meetings via the Messages Batches API. Blocks until the
        batch ends (typically <1h; max 24h). 50% discount and a separate rate
        limit pool from sync calls — use this for backlog ingestion to avoid
        hitting TPM limits. Failed items are returned as Exceptions in place."""
        names_by_date = {m["date"]: members_for_meeting(m["date"]) for m in meeting_transcripts}
        prompts = [
            build_meeting_analysis_prompt(m, [{"name": n} for n in names_by_date[m["date"]]])
            for m in meeting_transcripts
        ]
        raw_results = self.llm_client.batch_complete(prompts, MeetingAnalysisResult)

        out: list[MeetingAnalysisResult | Exception] = []
        for meeting, raw in zip(meeting_transcripts, raw_results):
            if isinstance(raw, Exception):
                out.append(raw)
                continue
            try:
                result = self._normalize(meeting["date"], raw, names_by_date[meeting["date"]])
                self._persist(meeting, result)
                out.append(result)
            except Exception as exc:
                out.append(exc)
        return out
