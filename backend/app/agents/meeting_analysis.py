from __future__ import annotations

import os
import re

from app.llm import LLMClient
from app.models.db import replace_meeting_member_summaries, upsert_meeting
from app.prompts.templates import build_meeting_analysis_chunk_prompt
from app.schemas import MeetingAnalysisResult, MemberMeetingSummary, TopicSummary


TIMESTAMP_LINE_RE = re.compile(r"^\[\d{1,2}:\d{2}:\d{2}\]\s*")


class MeetingAnalysisAgent:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        chunk_char_limit: int | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.chunk_char_limit = chunk_char_limit or int(os.getenv("MEETING_ANALYSIS_CHUNK_CHARS", "12000"))

    def analyze(self, meeting_transcript: dict, councilmembers: list[dict]) -> MeetingAnalysisResult:
        cleaned_transcript = self._clean_transcript(meeting_transcript["transcript"])
        transcript_chunks = self._chunk_transcript(cleaned_transcript)

        chunk_results = []
        for chunk_index, transcript_chunk in enumerate(transcript_chunks, start=1):
            prompt = build_meeting_analysis_chunk_prompt(
                meeting=meeting_transcript,
                councilmembers=councilmembers,
                transcript_chunk=transcript_chunk,
                chunk_index=chunk_index,
                total_chunks=len(transcript_chunks),
            )
            chunk_results.append(self.llm_client.complete(prompt, MeetingAnalysisResult))

        normalized_result = self._merge_chunk_results(
            meeting_id=meeting_transcript["meeting_id"],
            councilmembers=councilmembers,
            chunk_results=chunk_results,
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

    @staticmethod
    def _clean_transcript(transcript: str) -> str:
        cleaned_lines = []
        for raw_line in transcript.splitlines():
            line = TIMESTAMP_LINE_RE.sub("", raw_line).strip()
            if not line:
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _chunk_transcript(self, transcript: str) -> list[str]:
        if not transcript:
            return [""]

        chunks: list[str] = []
        current_lines: list[str] = []
        current_size = 0

        for line in transcript.splitlines():
            if len(line) > self.chunk_char_limit:
                if current_lines:
                    chunks.append("\n".join(current_lines))
                    current_lines = []
                    current_size = 0
                for start in range(0, len(line), self.chunk_char_limit):
                    chunks.append(line[start:start + self.chunk_char_limit])
                continue

            projected_size = current_size + len(line) + (1 if current_lines else 0)
            if current_lines and projected_size > self.chunk_char_limit:
                chunks.append("\n".join(current_lines))
                current_lines = [line]
                current_size = len(line)
            else:
                current_lines.append(line)
                current_size = projected_size

        if current_lines:
            chunks.append("\n".join(current_lines))

        return chunks or [transcript[: self.chunk_char_limit]]

    def _merge_chunk_results(
        self,
        meeting_id: str,
        councilmembers: list[dict],
        chunk_results: list[MeetingAnalysisResult],
    ) -> MeetingAnalysisResult:
        merged_topics: dict[str, dict[str, dict]] = {member["name"]: {} for member in councilmembers}

        for chunk_result in chunk_results:
            for member_summary in chunk_result.member_summaries:
                if member_summary.member_name not in merged_topics:
                    continue
                for topic in member_summary.topics:
                    issue_key = self._normalize_issue(topic.issue)
                    if not issue_key:
                        continue
                    existing = merged_topics[member_summary.member_name].get(issue_key)
                    if existing is None:
                        merged_topics[member_summary.member_name][issue_key] = {
                            "issue": topic.issue.strip(),
                            "stance": topic.stance,
                            "confidence": topic.confidence,
                            "quotes": self._dedupe_strings(topic.quotes),
                            "commitments": self._dedupe_strings(topic.commitments),
                            "vote_signal": topic.vote_signal,
                        }
                        continue

                    if topic.confidence >= existing["confidence"]:
                        existing["issue"] = topic.issue.strip() or existing["issue"]
                        existing["stance"] = topic.stance
                        existing["vote_signal"] = topic.vote_signal
                    existing["confidence"] = max(existing["confidence"], topic.confidence)
                    existing["quotes"] = self._dedupe_strings(existing["quotes"] + topic.quotes)
                    existing["commitments"] = self._dedupe_strings(existing["commitments"] + topic.commitments)

        completed_summaries = []
        for member in councilmembers:
            member_topics = [
                TopicSummary.model_validate(topic)
                for topic in merged_topics[member["name"]].values()
            ]
            member_topics.sort(key=lambda topic: topic.issue.lower())
            completed_summaries.append(MemberMeetingSummary(member_name=member["name"], topics=member_topics))

        return MeetingAnalysisResult(meeting_id=meeting_id, member_summaries=completed_summaries)

    @staticmethod
    def _normalize_issue(issue: str) -> str:
        return " ".join(issue.lower().split()).strip()

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            normalized = " ".join(value.split()).strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
        return deduped[:6]
