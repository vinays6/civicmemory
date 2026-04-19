from __future__ import annotations

import os
import re

from app.llm import LLMClient, LLMRateLimitExceeded
from app.models.db import replace_meeting_member_summaries, upsert_meeting
from app.prompts.templates import build_meeting_analysis_chunk_prompt
from app.schemas import MeetingAnalysisResult, MemberMeetingSummary, TopicSummary


TIMESTAMP_LINE_RE = re.compile(r"^\[\d{1,2}:\d{2}:\d{2}\]\s*")
MEETING_START_RE = re.compile(
    r"(regularly scheduled meeting|special meeting|let'?s begin our proceedings|members present|madam clerk)",
    re.I,
)
MEETING_END_RE = re.compile(
    r"(this meeting is adjourned|meeting is adjourned|go forth and serve the city)",
    re.I,
)
PUBLIC_COMMENT_RE = re.compile(r"\b(public comment|next speaker|general public comment)\b", re.I)
HIGH_SIGNAL_RE = re.compile(
    r"\b(madam clerk|mr\.? clerk|council member|councilmember|item\s+\d+|motion|amendment|separate vote|"
    r"receive and file|continue item|public hearing|open the roll|close the roll|tabulate the vote|"
    r"pledge of allegiance|quorum|members present|approve|adopt)\b",
    re.I,
)
KEEP_WINDOW_AFTER_MATCH = 2
MAX_INITIAL_LINES = 180
MAX_COMPRESSED_CHARS = 24000
MAX_DIGEST_PROCEDURAL_LINES = 120
MAX_DIGEST_MEMBER_LINES = 8
MAX_DIGEST_MEMBER_WINDOWS = 4
MEMBER_CONTEXT_RADIUS = 2
DEFAULT_MAX_LLM_INPUT_TOKENS = 6500
ITEM_NUMBER_RE = re.compile(r"\bitems?\s+(\d+[a-z]?)\b", re.I)
ITEM_LIST_RE = re.compile(r"\bitems?\s+((?:\d+[a-z]?(?:\s*(?:,|and)\s*)?)+)\b", re.I)
ISSUE_HINT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bunarmed crisis response\b|\bcare ?first\b|\bcommunity safety\b|\bcrisis response\b", re.I), "unarmed crisis response"),
    (re.compile(r"\bfire commissioner\b|\bYolanda Regalado\b", re.I), "Yolanda Regalado fire commission appointment"),
    (re.compile(r"\bfire chief Jamie Moore\b|\bsalary for fire chief\b", re.I), "Fire Chief Jamie Moore compensation"),
    (re.compile(r"\blong ?covid awareness day\b", re.I), "Long COVID awareness day recognition"),
    (re.compile(r"\bliens?\b|\bleans?\b|\babatement\b", re.I), "property lien case"),
    (re.compile(r"\btenant protections?\b", re.I), "tenant protections"),
]


class MeetingAnalysisAgent:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        chunk_char_limit: int | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.chunk_char_limit = chunk_char_limit or int(os.getenv("MEETING_ANALYSIS_CHUNK_CHARS", "12000"))

    def analyze(self, meeting_transcript: dict, councilmembers: list[dict]) -> MeetingAnalysisResult:
        meeting_window = self._slice_meeting_window(meeting_transcript["transcript"])
        agenda_item_map = self._build_agenda_item_map(
            meeting_window,
            meeting_transcript.get("agenda_items", {}),
        )
        enriched_meeting = dict(meeting_transcript)
        enriched_meeting["agenda_items"] = agenda_item_map
        compressed_transcript = self._compress_transcript("\n".join(meeting_window), councilmembers)
        evidence_digest = self._build_evidence_digest(meeting_window, councilmembers, agenda_item_map)
        llm_input = evidence_digest or compressed_transcript

        normalized_result: MeetingAnalysisResult
        if os.getenv("MEETING_ANALYSIS_FORCE_HEURISTIC", "0") == "1":
            normalized_result = self._heuristic_analysis(
                meeting_id=meeting_transcript["meeting_id"],
                lines=meeting_window,
                councilmembers=councilmembers,
                agenda_item_map=agenda_item_map,
            )
        elif not self._should_use_llm(llm_input):
            normalized_result = self._heuristic_analysis(
                meeting_id=meeting_transcript["meeting_id"],
                lines=meeting_window,
                councilmembers=councilmembers,
                agenda_item_map=agenda_item_map,
            )
        else:
            try:
                transcript_chunks = self._chunk_transcript(llm_input)
                chunk_results = []
                for chunk_index, transcript_chunk in enumerate(transcript_chunks, start=1):
                    prompt = build_meeting_analysis_chunk_prompt(
                        meeting=enriched_meeting,
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
            except LLMRateLimitExceeded:
                normalized_result = self._heuristic_analysis(
                    meeting_id=meeting_transcript["meeting_id"],
                    lines=meeting_window,
                    councilmembers=councilmembers,
                    agenda_item_map=agenda_item_map,
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

    def _slice_meeting_window(self, transcript: str) -> list[str]:
        lines = []
        for raw_line in transcript.splitlines():
            line = TIMESTAMP_LINE_RE.sub("", raw_line).strip()
            if not line:
                continue
            lines.append(line)

        start_index = 0
        for idx, line in enumerate(lines):
            if MEETING_START_RE.search(line):
                start_index = idx
                break

        end_index = len(lines)
        for idx in range(start_index, len(lines)):
            if MEETING_END_RE.search(lines[idx]):
                end_index = idx + 1
                break

        meeting_lines = lines[start_index:end_index]
        return meeting_lines or lines

    def _compress_transcript(self, transcript: str, councilmembers: list[dict]) -> str:
        lines = []
        for raw_line in transcript.splitlines():
            line = TIMESTAMP_LINE_RE.sub("", raw_line).strip()
            if not line:
                continue
            lines.append(line)
        meeting_lines = lines

        member_tokens = self._member_tokens(councilmembers)
        kept_lines: list[str] = []
        seen: set[str] = set()
        carry = 0

        def add_line(value: str) -> None:
            normalized = " ".join(value.split()).strip()
            if not normalized:
                return
            key = normalized.lower()
            if key in seen:
                return
            seen.add(key)
            kept_lines.append(normalized)

        for line in meeting_lines[:MAX_INITIAL_LINES]:
            add_line(line)

        for line in meeting_lines[MAX_INITIAL_LINES:]:
            lower = line.lower()
            member_hit = any(token in lower for token in member_tokens)
            high_signal = bool(HIGH_SIGNAL_RE.search(line))

            if PUBLIC_COMMENT_RE.search(line) and not (member_hit or high_signal):
                carry = 0
                continue

            if member_hit or high_signal:
                add_line(line)
                carry = KEEP_WINDOW_AFTER_MATCH
                continue

            if carry > 0:
                add_line(line)
                carry -= 1

            if sum(len(item) + 1 for item in kept_lines) >= MAX_COMPRESSED_CHARS:
                break

        compressed = "\n".join(kept_lines).strip()
        return compressed or "\n".join(meeting_lines[:MAX_INITIAL_LINES]).strip()

    def _build_evidence_digest(
        self,
        meeting_lines: list[str],
        councilmembers: list[dict],
        agenda_item_map: dict[str, str],
    ) -> str:
        if not meeting_lines:
            return ""

        sections: list[str] = []
        if agenda_item_map:
            sections.append("Agenda item labels:")
            for item_number in sorted(agenda_item_map, key=self._item_sort_key):
                sections.append(f"- Item {item_number}: {agenda_item_map[item_number]}")
        procedural_lines = self._collect_procedural_lines(meeting_lines)
        if procedural_lines:
            sections.append("Procedural evidence:")
            sections.extend(f"- {line}" for line in procedural_lines)

        for member in councilmembers:
            member_lines = self._collect_member_evidence_lines(meeting_lines, member["name"])
            if not member_lines:
                continue
            sections.append(f"Member evidence: {member['name']}")
            sections.extend(f"- {line}" for line in member_lines)

        digest = "\n".join(sections).strip()
        return digest[:MAX_COMPRESSED_CHARS].strip()

    def _collect_procedural_lines(self, lines: list[str]) -> list[str]:
        collected: list[str] = []
        seen: set[str] = set()
        carry = 0

        for line in lines:
            lower = line.lower()
            if PUBLIC_COMMENT_RE.search(line) and "item " not in lower and carry == 0:
                continue

            is_signal = bool(HIGH_SIGNAL_RE.search(line))
            is_vote_detail = bool(re.search(r"\b(ayes?|eyes|nos?|abstain|adopted|agreed to|approved)\b", line, re.I))
            is_item_detail = bool(re.search(r"\bitem\s+\d+[a-z]?\b", line, re.I))

            if is_signal or is_vote_detail or is_item_detail:
                key = line.lower()
                if key not in seen:
                    collected.append(line)
                    seen.add(key)
                carry = 1
                if len(collected) >= MAX_DIGEST_PROCEDURAL_LINES:
                    break
                continue

            if carry > 0:
                key = line.lower()
                if key not in seen:
                    collected.append(line)
                    seen.add(key)
                carry -= 1
                if len(collected) >= MAX_DIGEST_PROCEDURAL_LINES:
                    break

        return collected

    def _collect_member_evidence_lines(self, lines: list[str], member_name: str) -> list[str]:
        collected: list[str] = []
        seen: set[str] = set()
        windows_added = 0

        for idx, line in enumerate(lines):
            if not self._line_mentions_member(line, member_name):
                continue
            if self._is_roster_or_rollcall_line(line):
                continue

            start = max(0, idx - 1)
            end = min(len(lines), idx + MEMBER_CONTEXT_RADIUS + 1)
            for window_line in lines[start:end]:
                if self._is_roster_or_rollcall_line(window_line):
                    continue
                if PUBLIC_COMMENT_RE.search(window_line) and not self._line_mentions_member(window_line, member_name):
                    continue
                key = window_line.lower()
                if key in seen:
                    continue
                seen.add(key)
                collected.append(window_line)
                if len(collected) >= MAX_DIGEST_MEMBER_LINES:
                    return collected

            windows_added += 1
            if windows_added >= MAX_DIGEST_MEMBER_WINDOWS:
                break

        return collected

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

    def _should_use_llm(self, transcript: str) -> bool:
        if not transcript.strip():
            return False
        if not os.getenv("ANTHROPIC_API_KEY"):
            return False

        max_input_tokens = int(
            os.getenv("MEETING_ANALYSIS_MAX_INPUT_TOKENS", str(DEFAULT_MAX_LLM_INPUT_TOKENS))
        )
        estimated_prompt_tokens = self._estimate_token_count(transcript) + 1800
        return estimated_prompt_tokens <= max_input_tokens

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

    def _heuristic_analysis(
        self,
        meeting_id: str,
        lines: list[str],
        councilmembers: list[dict],
        agenda_item_map: dict[str, str],
    ) -> MeetingAnalysisResult:
        summaries: list[MemberMeetingSummary] = []

        for member in councilmembers:
            topics: list[TopicSummary] = []
            member_name = member["name"]
            member_tokens = self._member_tokens([member])
            for idx, line in enumerate(lines):
                lower = line.lower()
                if not any(token in lower for token in member_tokens):
                    continue
                if self._is_roster_or_rollcall_line(line):
                    continue

                issue = self._infer_issue_from_context(lines, idx, agenda_item_map)
                if not issue and not self._is_member_action_line(line):
                    continue

                quote_lines = [line]
                if idx + 1 < len(lines):
                    quote_lines.append(lines[idx + 1])
                quote = " ".join(quote_lines).strip()

                issue = issue or self._infer_issue(line, agenda_item_map)
                stance = self._infer_stance(line)
                vote_signal = self._infer_vote_signal(line)
                commitment = self._infer_commitment(line)
                topics.append(
                    TopicSummary(
                        issue=issue,
                        stance=stance,
                        confidence=0.55,
                        quotes=self._dedupe_strings([quote])[:1],
                        commitments=self._dedupe_strings([commitment]) if commitment else [],
                        vote_signal=vote_signal,
                    )
                )

            deduped_topics = self._merge_member_topics(topics)
            summaries.append(MemberMeetingSummary(member_name=member_name, topics=deduped_topics))

        return MeetingAnalysisResult(meeting_id=meeting_id, member_summaries=summaries)

    @staticmethod
    def _normalize_issue(issue: str) -> str:
        return " ".join(issue.lower().split()).strip()

    def _build_agenda_item_map(
        self,
        meeting_lines: list[str],
        seeded_items: dict[str, str] | None,
    ) -> dict[str, str]:
        agenda_item_map: dict[str, str] = {}
        for item_number, description in (seeded_items or {}).items():
            cleaned = self._clean_agenda_label(description)
            if cleaned:
                agenda_item_map[str(item_number)] = cleaned

        for item_number, label in self._infer_agenda_items_from_transcript(meeting_lines).items():
            agenda_item_map.setdefault(item_number, label)

        return agenda_item_map

    def _infer_agenda_items_from_transcript(self, meeting_lines: list[str]) -> dict[str, str]:
        discovered_items: dict[str, str] = {}
        item_windows: dict[str, list[str]] = {}

        for idx, line in enumerate(meeting_lines):
            mentioned_items = self._extract_item_numbers(line)
            if len(mentioned_items) != 1:
                continue

            item_number = mentioned_items[0]
            if not self._is_item_discussion_anchor(line, item_number):
                continue

            item_windows.setdefault(item_number, [])
            start = max(0, idx - 1)
            end = min(len(meeting_lines), idx + 18)
            for window_idx in range(start, end):
                window_line = meeting_lines[window_idx]
                if self._is_filler_context(window_line):
                    continue
                if window_idx > idx and self._starts_other_item_discussion(window_line, item_number):
                    break
                item_windows[item_number].append(window_line)

        for item_number, window_lines in item_windows.items():
            label = self._infer_item_label(item_number, window_lines)
            if label:
                discovered_items[item_number] = label

        return discovered_items

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

    @staticmethod
    def _extract_item_numbers(line: str) -> list[str]:
        numbers: list[str] = []
        for match in ITEM_LIST_RE.finditer(line):
            chunk = match.group(1)
            for item_match in re.finditer(r"\d+[a-z]?", chunk, re.I):
                numbers.append(item_match.group(0))
        if numbers:
            return numbers
        single = ITEM_NUMBER_RE.search(line)
        return [single.group(1)] if single else []

    def _infer_item_label(self, item_number: str, window_lines: list[str]) -> str | None:
        joined = " ".join(window_lines)

        for pattern, label in ISSUE_HINT_PATTERNS:
            if pattern.search(joined):
                return label

        name_match = re.search(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b.*?\b(fire commissioner|fire chief|commissioner)\b",
            joined,
        )
        if name_match:
            return self._clean_agenda_label(f"{name_match.group(1)} {name_match.group(2)}")

        reverse_name_match = re.search(
            r"\b(fire commissioner|fire chief|salary for fire chief)\b.*?\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
            joined,
            re.I,
        )
        if reverse_name_match:
            return self._clean_agenda_label(f"{reverse_name_match.group(2)} {reverse_name_match.group(1)}")

        phrase = self._extract_descriptive_phrase(joined)
        if phrase:
            return phrase

        return None

    def _is_item_discussion_anchor(self, line: str, item_number: str) -> bool:
        lower = line.lower()
        if f"item {item_number.lower()}" not in lower:
            return False
        if "public comment on the agenda are items" in lower:
            return False

        anchor_patterns = [
            rf"\bitem\s+{re.escape(item_number)}\b.*\b(before us|special|amendment|comments?|consider|record|regarding|salary|commissioner|public hearing)\b",
            rf"\b(call|continue|approve|receive and file|hold)\b.*\bitem\s+{re.escape(item_number)}\b",
            rf"\bnext would be\b.*\bitem\s+{re.escape(item_number)}\b",
            rf"\blet'?s consider\b.*\bitem\s+{re.escape(item_number)}\b",
        ]
        return any(re.search(pattern, line, re.I) for pattern in anchor_patterns)

    def _starts_other_item_discussion(self, line: str, current_item_number: str) -> bool:
        mentioned_items = self._extract_item_numbers(line)
        if len(mentioned_items) != 1:
            return False
        other_item = mentioned_items[0]
        return other_item != current_item_number and self._is_item_discussion_anchor(line, other_item)

    @staticmethod
    def _extract_descriptive_phrase(text: str) -> str | None:
        candidates = re.findall(
            r"\b(?:regarding|about|for|on)\s+([A-Za-z][A-Za-z0-9,\-\s]{8,90})",
            text,
            re.I,
        )
        for candidate in candidates:
            cleaned = MeetingAnalysisAgent._clean_agenda_label(candidate)
            if cleaned and "item" not in cleaned.lower():
                return cleaned
        return None

    @staticmethod
    def _clean_agenda_label(label: str) -> str:
        cleaned = " ".join(label.split()).strip(" -,:;.")
        cleaned = re.sub(r"\b(called special|special|comments?)\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bfor the record\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bpublic comment\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -,:;.")
        if not cleaned:
            return ""
        return cleaned[:100]

    @staticmethod
    def _is_filler_context(line: str) -> bool:
        lower = line.lower()
        return "general public comment" in lower and "item " not in lower

    @staticmethod
    def _item_sort_key(item_number: str) -> tuple[int, str]:
        match = re.match(r"(\d+)([a-z]?)", item_number, re.I)
        if not match:
            return (9999, item_number)
        return (int(match.group(1)), match.group(2).lower())

    @staticmethod
    def _member_tokens(councilmembers: list[dict]) -> set[str]:
        tokens: set[str] = set()
        for member in councilmembers:
            name = member["name"].lower()
            parts = [part for part in re.split(r"[\s\-]+", name) if part]
            if name:
                tokens.add(name)
            if parts:
                tokens.add(parts[-1])
            if len(parts) >= 2:
                tokens.add(" ".join(parts[-2:]))
        return tokens

    @staticmethod
    def _line_mentions_member(line: str, member_name: str) -> bool:
        escaped = re.escape(member_name)
        if re.search(rf"\b{escaped}\b", line, re.I):
            parts = [part for part in re.split(r"[\s\-]+", member_name) if part]
            if len(parts) == 1 and len(parts[0]) <= 4:
                return bool(
                    re.search(
                        rf"\b(council member|councilmember|member|mr\.|ms\.|miss)\s+{escaped}\b|^{escaped}\b",
                        line,
                        re.I,
                    )
                )
            return True

        parts = [part for part in re.split(r"[\s\-]+", member_name) if part]
        if len(parts) >= 2:
            surname = re.escape(parts[-1])
            if len(parts[-1]) >= 4 and re.search(rf"\b{surname}\b", line, re.I):
                return True
        return False

    def _infer_issue_from_context(
        self,
        lines: list[str],
        idx: int,
        agenda_item_map: dict[str, str],
    ) -> str | None:
        start = max(0, idx - 4)
        end = min(len(lines), idx + 4)
        for context_idx in range(start, end):
            issue = self._infer_issue(lines[context_idx], agenda_item_map)
            if issue != "meeting proceedings":
                return issue
        return None

    @staticmethod
    def _is_member_action_line(line: str) -> bool:
        return bool(
            re.search(
                r"\b(item\s+\d+[a-z]?|move|moves|moved|second|seconds|approve|continue|receive and file|"
                r"amendment|special|comments?|support|oppose|before us|separate vote)\b",
                line,
                re.I,
            )
        )

    @staticmethod
    def _is_roster_or_rollcall_line(line: str) -> bool:
        lower = line.lower()
        if "members present" in lower:
            return True
        if "let's begin our proceedings by calling the role" in lower:
            return True
        if "calling the role" in lower:
            return True
        if re.search(r"\b\d+\s+members?\s+present\b", lower):
            return True
        return False

    @staticmethod
    def _estimate_token_count(text: str) -> int:
        return max(1, len(text) // 4)

    def _merge_member_topics(self, topics: list[TopicSummary]) -> list[TopicSummary]:
        by_issue: dict[str, dict] = {}
        for topic in topics:
            issue_key = self._normalize_issue(topic.issue)
            existing = by_issue.get(issue_key)
            if existing is None:
                by_issue[issue_key] = topic.model_dump()
                continue
            existing["confidence"] = max(existing["confidence"], topic.confidence)
            existing["quotes"] = self._dedupe_strings(existing["quotes"] + topic.quotes)
            existing["commitments"] = self._dedupe_strings(existing["commitments"] + topic.commitments)
            if topic.vote_signal != "unknown":
                existing["vote_signal"] = topic.vote_signal
            if topic.stance != "unclear":
                existing["stance"] = topic.stance
        merged = [TopicSummary.model_validate(topic) for topic in by_issue.values()]
        merged.sort(key=lambda topic: topic.issue.lower())
        return merged[:8]

    @staticmethod
    def _infer_issue(line: str, agenda_item_map: dict[str, str]) -> str:
        item_match = re.search(r"\bitem\s+(\d+[a-z]?)\b", line, re.I)
        if item_match:
            item_number = item_match.group(1)
            if item_number in agenda_item_map:
                return agenda_item_map[item_number]
            return f"agenda item {item_number}"
        if "pledge of allegiance" in line.lower():
            return "pledge of allegiance"
        if "public comment" in line.lower():
            return "public comment process"
        if "amendment" in line.lower():
            return "agenda amendment"
        if "separate vote" in line.lower():
            return "separate vote request"
        if "receive and file" in line.lower():
            return "receive and file motion"
        if "continue item" in line.lower() or "continued" in line.lower():
            return "item continuance"
        return "meeting proceedings"

    @staticmethod
    def _infer_stance(line: str) -> str:
        lower = line.lower()
        if "move" in lower or "moves" in lower or "seconds" in lower or "approve" in lower:
            return "support"
        if "separate vote" in lower or "amendment" in lower or "comments" in lower:
            return "conditional"
        if "continue item" in lower or "continued" in lower:
            return "defer"
        return "unclear"

    @staticmethod
    def _infer_vote_signal(line: str) -> str:
        lower = line.lower()
        if "approve" in lower or "moves" in lower or "seconds" in lower:
            return "yes"
        if "continue item" in lower or "continued" in lower:
            return "unclear"
        return "unknown"

    @staticmethod
    def _infer_commitment(line: str) -> str | None:
        if "continue item" in line.lower() or "continued" in line.lower():
            return "Requested a continuance on an agenda item."
        if "amendment" in line.lower():
            return "Requested an amendment to an agenda item."
        return None
