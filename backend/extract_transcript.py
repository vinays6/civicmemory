"""
Extract LA City Council meeting transcripts from YouTube videos, trimmed to
start at the actual call-to-order (skipping the ~40min pre-meeting filler).

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
    # Spanish-language equivalents (LA council captions are frequently Spanish).
    (re.compile(r"\breuni[oó]n\s+del\s+consejo\b", re.I), "reunión del consejo"),
    (re.compile(r"\bprimera\s+orden\s+del\s+d[ií]a\b", re.I), "primera orden del día"),
    (re.compile(r"\bmiembros\s+presentes\b", re.I), "miembros presentes"),
    (re.compile(r"\bqu[oó]rum\b", re.I), "quórum"),
]
MIN_START_SECONDS = 60.0


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
        # Allow bare 11-char IDs too.
        if re.fullmatch(r"[\w-]{11}", url):
            return url
        raise ValueError(f"Could not extract video id from: {url}")
    return m.group(1)


WINDOW = 3  # segments joined when trigger-matching (captions split phrases)
WINDOW_MAX_GAP = 5.0  # don't bridge segments more than this many seconds apart


def _window_text(segments: list[Segment], i: int) -> str:
    """Join up to WINDOW segments starting at i, stopping if a gap > WINDOW_MAX_GAP."""
    parts = [segments[i].text]
    for j in range(i + 1, min(i + WINDOW, len(segments))):
        if segments[j].start - (segments[j - 1].start + segments[j - 1].duration) > WINDOW_MAX_GAP:
            break
        parts.append(segments[j].text)
    return " ".join(parts)


def find_meeting_start(segments: list[Segment]) -> tuple[int, str | None]:
    """Return (index, matched_phrase) or (0, None) if no trigger matched.

    Joins consecutive segments (bounded by WINDOW_MAX_GAP) before regex
    matching so triggers split across captions still hit. Returns the
    earliest-by-timestamp match after MIN_START_SECONDS.
    """
    best_idx: int | None = None
    best_phrase: str | None = None
    for i, seg in enumerate(segments):
        if seg.start < MIN_START_SECONDS:
            continue
        joined = _window_text(segments, i)
        for pat, label in TRIGGERS:
            if pat.search(joined):
                if best_idx is None or seg.start < segments[best_idx].start:
                    best_idx = i
                    best_phrase = label
                break
    if best_idx is None:
        return 0, None
    return best_idx, best_phrase


def _fetch_sync(video_id: str) -> list[Segment]:
    fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US"])
    return [Segment(text=s.text, start=s.start, duration=s.duration) for s in fetched]


async def process_url(url: str, keep_preamble: bool) -> TranscriptResult:
    video_id = extract_video_id(url)
    try:
        segments = await asyncio.to_thread(_fetch_sync, video_id)
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
        return TranscriptResult(
            url=url,
            video_id=video_id,
            trim_start_seconds=0.0,
            trigger_phrase=None,
            segments=[],
            warning=f"{type(e).__name__}: {e}",
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

    async def bounded(u: str) -> TranscriptResult:
        async with sem:
            return await process_url(u, keep_preamble)

    return await asyncio.gather(*(bounded(u) for u in urls))


def _fmt_ts(s: float) -> str:
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{sec:02d}" if h else f"{m:d}:{sec:02d}"


def emit_text(results: list[TranscriptResult], out=sys.stdout) -> None:
    for i, r in enumerate(results):
        if i:
            out.write("\n\n")
        header = f"# {r.video_id} — trimmed at {_fmt_ts(r.trim_start_seconds)}"
        if r.trigger_phrase:
            header += f' (trigger: "{r.trigger_phrase}")'
        if r.warning:
            header += f"  [!] {r.warning}"
        out.write(header + "\n")
        for seg in r.segments:
            out.write(f"[{_fmt_ts(seg.start)}] {seg.text}\n")


def emit_json(results: list[TranscriptResult], out=sys.stdout) -> None:
    for r in results:
        d = asdict(r)
        out.write(json.dumps(d, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--json", action="store_true", help="emit JSONL instead of text")
    ap.add_argument("--keep-preamble", action="store_true", help="don't trim")
    ap.add_argument("--concurrency", type=int, default=20)
    args = ap.parse_args()

    results = asyncio.run(run(args.urls, args.keep_preamble, args.concurrency))
    (emit_json if args.json else emit_text)(results)
    return 0 if all(not r.warning or r.segments for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
