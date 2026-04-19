"""
Regex-based transcript preprocessing to shrink what goes to the LLM.

Public entry point: `preprocess_transcript(raw, member_names)`.

Passes (in order):
  1. Slice the meeting window: from first "meeting starts" marker to first
     "meeting adjourned" marker. Reduces warm-up/outro noise.
  2. Drop public-comment sections unless a council member is speaking in them.
  3. Drop always-procedural lines (roll-call responses, vote tallies).
  4. Collapse blank lines and deduplicate consecutive identical lines.

Timestamps like `[14:03:21]` are preserved so the LLM can cite them as
pointers back into the transcript.

Ported from the regex constants on origin/vinay. The heavier digest/chunking
pipeline is intentionally NOT ported — Haiku + structured outputs handles
full transcripts fine, and batching solves the rate-limit side.
"""

from __future__ import annotations

import re


TIMESTAMP_LINE_RE = re.compile(r"^\s*\[\d{1,2}:\d{2}:\d{2}\]\s*")

MEETING_START_RE = re.compile(
    r"(regularly scheduled meeting|special meeting|let'?s begin our proceedings|"
    r"members present|madam clerk|mr\.? clerk)",
    re.I,
)
MEETING_END_RE = re.compile(
    r"(this meeting is adjourned|meeting is adjourned|go forth and serve the city)",
    re.I,
)
PUBLIC_COMMENT_RE = re.compile(
    r"\b(public comment|next speaker|general public comment)\b",
    re.I,
)

# "Always drop" — lines that are pure procedural noise regardless of who's
# speaking. A roll-call response like "Hernandez: Present." still has a member
# name in it, but has no analytical content.
ALWAYS_DROP_PATTERNS = [
    # "Name: Present." / "Name: Here." / "Name: Aye." / "Name, present." etc.
    re.compile(
        r"^\s*(mr\.?|ms\.?|madam)?\s*[\w\-'.]+\s*[:,]?\s*"
        r"(present|here|aye|nay|absent|no|yes)\.?\s*$",
        re.I,
    ),
    # Vote tallies — already in the votes DB.
    re.compile(r"^\s*ayes?\s*[:\-]\s*\d+", re.I),
    re.compile(r"^\s*nays?\s*[:\-]\s*\d+", re.I),
    re.compile(r"^\s*motion\s+(carries|passes|fails|adopted)\b", re.I),
]

# "Drop unless a member is on the line" — procedural noise, but if a member
# is mentioned we keep it so the model can see context.
DROP_LINE_PATTERNS = [
    re.compile(r"\bplease\s+call\s+the\s+roll\b", re.I),
    re.compile(r"^\s*members?\s+present\b", re.I),
    re.compile(r"^\s*without\s+objection(,?\s+so\s+ordered)?\.?\s*$", re.I),
    re.compile(r"^\s*(the\s+)?pledge\s+of\s+allegiance\b", re.I),
    re.compile(r"^\s*(invocation|moment\s+of\s+silence)\b", re.I),
    re.compile(r"^\s*(i\s+move|second|seconded)\s+(the\s+)?(motion|adjournment)\.?\s*$", re.I),
    re.compile(r"^\s*thank\s+you\.?\s*$", re.I),
]


def _content(line: str) -> str:
    """Line body with any leading timestamp prefix stripped, for pattern-matching."""
    return TIMESTAMP_LINE_RE.sub("", line).strip()


def _slice_window(lines: list[str]) -> list[str]:
    start = 0
    for i, ln in enumerate(lines):
        if MEETING_START_RE.search(ln):
            start = i
            break
    end = len(lines)
    for i in range(start, len(lines)):
        if MEETING_END_RE.search(lines[i]):
            end = i + 1
            break
    return lines[start:end] or lines


def _name_pattern(names: list[str]) -> re.Pattern | None:
    """Match any councilmember surname (or full name) as a whole word."""
    tokens = {t for n in names for t in n.split() if len(t) >= 3}
    if not tokens:
        return None
    escaped = sorted((re.escape(t) for t in tokens), key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.I)


def _drop_public_comment(lines: list[str], name_re: re.Pattern | None) -> list[str]:
    """Drop lines inside a public-comment section unless a council member
    is mentioned on the line."""
    in_public = False
    out: list[str] = []
    for ln in lines:
        body = _content(ln)
        if PUBLIC_COMMENT_RE.search(body):
            in_public = True
            out.append(ln)
            continue
        if in_public:
            if name_re and name_re.search(body):
                in_public = False
                out.append(ln)
            continue
        out.append(ln)
    return out


def _drop_boilerplate(lines: list[str], name_re: re.Pattern | None) -> list[str]:
    """Drop roll-call mechanics, vote tallies, and canned procedural lines.
    ALWAYS_DROP runs first (catches roll-call responses even if they mention a
    member). DROP_LINE runs second with a name-preserve guard — a procedural
    line that also mentions a speaking member is kept for context."""
    out: list[str] = []
    for ln in lines:
        body = _content(ln)
        if any(p.search(body) for p in ALWAYS_DROP_PATTERNS):
            continue
        if name_re and name_re.search(body):
            out.append(ln)
            continue
        if any(p.search(body) for p in DROP_LINE_PATTERNS):
            continue
        out.append(ln)
    return out


def _collapse(lines: list[str]) -> list[str]:
    out: list[str] = []
    prev = None
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln == prev:
            continue
        out.append(ln)
        prev = ln
    return out


def preprocess_transcript(raw: str, member_names: list[str]) -> str:
    name_re = _name_pattern(member_names)
    lines = [ln.strip() for ln in raw.splitlines()]
    lines = _slice_window(lines)
    lines = _drop_public_comment(lines, name_re)
    lines = _drop_boilerplate(lines, name_re)
    lines = _collapse(lines)
    return "\n".join(lines)
