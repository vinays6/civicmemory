"""
Analyze council meeting transcripts and write per-member opinions to the DB.

Usage:
    python analyze_transcripts.py PATH [--workers N] [--force]

PATH is either a single transcript file or a directory containing many.
Filenames must be formatted as `YYYY-MM-DD_VIDEOID.txt` — the date becomes
`meeting_date`, the chunk between `_` and `.txt` becomes `video_id`.

When PATH is a directory, files are analyzed concurrently with a thread pool
(default: 5 workers). The Anthropic SDK is thread-safe; each worker makes
its own Haiku call. Respects rate limits — keep --workers modest if you hit
429s.
"""

from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from sqlalchemy import select

from app.agents.meeting_analysis import MeetingAnalysisAgent
from db import default_engine, member_opinion


FILENAME_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def already_analyzed(meeting_date: str) -> bool:
    with default_engine().connect() as conn:
        return conn.execute(
            select(member_opinion.c.meeting_date)
            .where(member_opinion.c.meeting_date == meeting_date)
            .limit(1)
        ).first() is not None


def parse_file(path: Path) -> tuple[str, str] | None:
    m = FILENAME_DATE_RE.search(path.name)
    if not m:
        print(f"skip {path.name}: no YYYY-MM-DD in filename", file=sys.stderr)
        return None
    stem = path.stem
    video_id = stem.rsplit("_", 1)[-1] if "_" in stem else None
    if not video_id:
        print(f"skip {path.name}: cannot extract video_id", file=sys.stderr)
        return None
    return m.group(1), video_id


def run_one(agent: MeetingAnalysisAgent, path: Path, force: bool) -> str:
    parsed = parse_file(path)
    if parsed is None:
        return f"SKIP {path.name}: unparseable"
    meeting_date, video_id = parsed

    if already_analyzed(meeting_date) and not force:
        return f"SKIP {meeting_date}: already in DB"

    try:
        result = agent.analyze({
            "date": meeting_date,
            "transcript": path.read_text(),
            "video_id": video_id,
        })
        return f"OK   {meeting_date}: {len(result.member_summaries)} members"
    except Exception as exc:
        return f"ERR  {meeting_date}: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="transcript file or directory")
    ap.add_argument("--workers", type=int, default=5, help="parallel workers for directories (default: 5)")
    ap.add_argument("--force", action="store_true", help="re-analyze meetings already in DB")
    args = ap.parse_args()

    if args.path.is_file():
        paths = [args.path]
    elif args.path.is_dir():
        paths = sorted(args.path.glob("*.txt"))
        if not paths:
            ap.error(f"no .txt files in {args.path}")
    else:
        ap.error(f"{args.path} is not a file or directory")

    agent = MeetingAnalysisAgent()
    print(f"analyzing {len(paths)} file(s) with {agent.llm_client.model} "
          f"across {args.workers} worker(s)...")

    # Single file → no thread overhead
    if len(paths) == 1:
        print(run_one(agent, paths[0], args.force))
        return 0

    ok = err = skip = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(run_one, agent, p, args.force): p for p in paths}
        for fut in as_completed(futures):
            line = fut.result()
            print(line)
            if line.startswith("OK"):
                ok += 1
            elif line.startswith("ERR"):
                err += 1
            else:
                skip += 1

    print(f"\ndone: {ok} ok, {err} failed, {skip} skipped")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
