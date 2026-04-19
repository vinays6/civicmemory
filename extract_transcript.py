"""
Extract LA City Council meeting transcripts from YouTube videos, trimmed to
start at the actual meeting rather than the city-channel filler that often
precedes it.

Usage:
    python extract_transcript.py URL [URL ...] [--json] [--keep-preamble]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass
from typing import Iterable

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/)([\w-]{11})")

TRIGGERS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:call(?:ed)?|come)\s+to\s+order\b", re.I), "call to order"),
    (re.compile(r"\broll\s*call\b", re.I), "roll call"),
    (re.compile(r"\bpledge\s+of\s+allegiance\b", re.I), "pledge of allegiance"),
    (re.compile(r"\binvocation\b", re.I), "invocation"),
    (re.compile(r"\b(?:madam|mr\.?)\s+clerk[, ]+\s+let'?s\s+begin\b", re.I), "clerk begin"),
    (re.compile(r"\blet'?s\s+begin\s+our\s+proceedings\b", re.I), "begin proceedings"),
    (re.compile(r"\bmembers?\s+present\b", re.I), "members present"),
    (re.compile(r"\b(?:a\s+)?quorum\b", re.I), "quorum"),
    (re.compile(r"\breuni[oó]n\s+del\s+consejo\b", re.I), "reunion del consejo"),
    (re.compile(r"\bprimera\s+orden\s+del\s+d[ií]a\b", re.I), "primera orden del dia"),
    (re.compile(r"\bmiembros\s+presentes\b", re.I), "miembros presentes"),
]

SOFT_START_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgood\s+(?:morning|afternoon)\s+and\s+welcome\b", re.I), "welcome"),
    (re.compile(r"\bwelcome\s+to\s+the\s+(?:regular|special)\s+meeting\b", re.I), "meeting welcome"),
    (re.compile(r"\blet'?s\s+open\s+the\s+meeting\b", re.I), "open meeting"),
]

PROCEDURAL_CONTEXT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:madam|mr\.?)\s+clerk\b", re.I),
    re.compile(r"\bproceedings\b", re.I),
    re.compile(r"\bquorum\b", re.I),
    re.compile(r"\bmembers?\s+present\b", re.I),
    re.compile(r"\bpledge\s+of\s+allegiance\b", re.I),
    re.compile(r"\bitems?\s+(?:are\s+)?available\b", re.I),
    re.compile(r"\bspecial\s+meeting\b", re.I),
    re.compile(r"\bregular\s+meeting\b", re.I),
]

FILLER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bwelcome\s+to\s+la\s+this\s+week\b", re.I),
    re.compile(r"\bcitybeat\b", re.I),
    re.compile(r"\binside\s+city\s+hall\b", re.I),
    re.compile(r"\bthese\s+stories\s+up\s+next\b", re.I),
    re.compile(r"\bcentral\s+library\b", re.I),
    re.compile(r"\bgolden\s+dragon\s+parade\b", re.I),
]

MIN_START_SECONDS = 60.0
WINDOW = 3
WINDOW_MAX_GAP = 5.0
CONTEXT_WINDOW = 12


@dataclass
class Segment:
    text: str
    start: float
    duration: float


@dataclass
class TranscriptResult:
    url: str
    video_id: str
    trim_start_seconds: float
    trigger_phrase: str | None
    segments: list[Segment]
    warning: str | None = None


def extract_video_id(url: str) -> str:
    m = VIDEO_ID_RE.search(url)
    if not m:
        if re.fullmatch(r"[\w-]{11}", url):
            return url
        raise ValueError(f"Could not extract video id from: {url}")
    return m.group(1)


def _window_text(segments: list[Segment], i: int, window: int = WINDOW) -> str:
    """Join up to `window` segments starting at i, stopping if a gap > WINDOW_MAX_GAP."""
    parts = [segments[i].text]
    for j in range(i + 1, min(i + window, len(segments))):
        if segments[j].start - (segments[j - 1].start + segments[j - 1].duration) > WINDOW_MAX_GAP:
            break
        parts.append(segments[j].text)
    return " ".join(parts)


def _looks_like_filler(text: str) -> bool:
    return any(pat.search(text) for pat in FILLER_PATTERNS)


def _has_procedural_context(text: str) -> bool:
    return any(pat.search(text) for pat in PROCEDURAL_CONTEXT_PATTERNS)


def find_meeting_start(segments: list[Segment]) -> tuple[int, str | None]:
    """Return (index, matched_phrase) or (0, None) if no meeting-start cue matched."""
    best_idx: int | None = None
    best_phrase: str | None = None
    soft_idx: int | None = None
    soft_phrase: str | None = None

    for i, seg in enumerate(segments):
        if seg.start < MIN_START_SECONDS:
            continue

        joined = _window_text(segments, i, WINDOW)
        context = _window_text(segments, i, CONTEXT_WINDOW)

        for pat, label in TRIGGERS:
            if pat.search(joined) or pat.search(context):
                if _looks_like_filler(context):
                    continue
                if best_idx is None or seg.start < segments[best_idx].start:
                    best_idx = i
                    best_phrase = label
                break

        if best_idx is not None:
            continue

        if _looks_like_filler(context):
            continue

        for pat, label in SOFT_START_PATTERNS:
            if (pat.search(joined) or pat.search(context)) and _has_procedural_context(context):
                if soft_idx is None or seg.start < segments[soft_idx].start:
                    soft_idx = i
                    soft_phrase = label
                break

    if best_idx is not None:
        return best_idx, best_phrase
    if soft_idx is not None:
        return soft_idx, soft_phrase
    return 0, None


def _fetch_sync(video_id: str) -> list[Segment]:
    fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US"])
    return [Segment(text=s.text, start=s.start, duration=s.duration) for s in fetched]


async def process_url(url: str, keep_preamble: bool) -> TranscriptResult:
    video_id = extract_video_id(url)
    try:
        segments = await asyncio.to_thread(_fetch_sync, video_id)
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
        return TranscriptResult(
            url=url,
            video_id=video_id,
            trim_start_seconds=0.0,
            trigger_phrase=None,
            segments=[],
            warning=f"{type(exc).__name__}: {exc}",
        )

    if keep_preamble:
        return TranscriptResult(url, video_id, 0.0, None, segments)

    idx, phrase = find_meeting_start(segments)
    trimmed = segments[idx:]
    start_s = trimmed[0].start if trimmed else 0.0
    warning = None if phrase else "no trigger matched; returning full transcript"
    return TranscriptResult(url, video_id, start_s, phrase, trimmed, warning)


async def run(urls: Iterable[str], keep_preamble: bool, concurrency: int) -> list[TranscriptResult]:
    sem = asyncio.Semaphore(concurrency)

    async def bounded(url: str) -> TranscriptResult:
        async with sem:
            return await process_url(url, keep_preamble)

    return await asyncio.gather(*(bounded(url) for url in urls))


def _fmt_ts(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:d}:{sec:02d}"


def emit_text(results: list[TranscriptResult], out=sys.stdout) -> None:
    for i, result in enumerate(results):
        if i:
            out.write("\n\n")
        header = f"# {result.video_id} - trimmed at {_fmt_ts(result.trim_start_seconds)}"
        if result.trigger_phrase:
            header += f' (trigger: "{result.trigger_phrase}")'
        if result.warning:
            header += f"  [!] {result.warning}"
        out.write(header + "\n")
        for seg in result.segments:
            out.write(f"[{_fmt_ts(seg.start)}] {seg.text}\n")


def emit_json(results: list[TranscriptResult], out=sys.stdout) -> None:
    for result in results:
        out.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--json", action="store_true", help="emit JSONL instead of text")
    ap.add_argument("--keep-preamble", action="store_true", help="don't trim")
    ap.add_argument("--concurrency", type=int, default=20)
    args = ap.parse_args()

    results = asyncio.run(run(args.urls, args.keep_preamble, args.concurrency))
    (emit_json if args.json else emit_text)(results)
    return 0 if all(not result.warning or result.segments for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
