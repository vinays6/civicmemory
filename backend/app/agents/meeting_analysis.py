from __future__ import annotations

from app.llm import LLMClient
from app.preprocess import preprocess_transcript
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
        roster = set(names)
        merged: dict[str, MemberMeetingSummary] = {}
        for s in result.member_summaries:
            if s.member_name not in roster or not s.topics:
                continue
            # LLM sometimes emits the same member twice when they speak on
            # multiple sub-issues; merge topics into a single row so the
            # (meeting_date, member) primary key stays unique.
            if s.member_name in merged:
                merged[s.member_name] = MemberMeetingSummary(
                    member_name=s.member_name,
                    topics=merged[s.member_name].topics + s.topics,
                )
            else:
                merged[s.member_name] = s
        return MeetingAnalysisResult(
            meeting_date=meeting_date,
            member_summaries=list(merged.values()),
        )

    def _persist(self, meeting_transcript: dict, result: MeetingAnalysisResult) -> None:
        upsert_meeting(
            meeting_date=result.meeting_date,
            transcript=meeting_transcript["transcript"],
            video_id=meeting_transcript.get("video_id"),
        )
        replace_member_opinions(
            meeting_date=result.meeting_date,
            opinions=[s.model_dump() for s in result.member_summaries],
            model=self.llm_client.model,
        )

    def _prepped(self, meeting_transcript: dict, names: list[str]) -> dict:
        """Return a copy of meeting_transcript with transcript regex-preprocessed."""
        return {
            **meeting_transcript,
            "transcript": preprocess_transcript(meeting_transcript["transcript"], names),
        }

    def analyze(self, meeting_transcript: dict) -> MeetingAnalysisResult:
        names = members_for_meeting(meeting_transcript["date"])
        councilmembers = [{"name": n} for n in names]
        prepped = self._prepped(meeting_transcript, names)
        prompt = build_meeting_analysis_prompt(prepped, councilmembers)
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
            build_meeting_analysis_prompt(
                self._prepped(m, names_by_date[m["date"]]),
                [{"name": n} for n in names_by_date[m["date"]]],
            )
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
