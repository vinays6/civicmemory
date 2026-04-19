from __future__ import annotations

import os
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DB_PATH = Path(os.getenv("CIVICMEMORY_SOURCE_DB", str(REPO_ROOT / "votes.sqlite")))
TRANSCRIPTS_DIR = Path(
    os.getenv("CIVICMEMORY_TRANSCRIPTS_DIR", str(REPO_ROOT / "civicmemdata" / "transcripts"))
)


def _connect_source_db() -> sqlite3.Connection:
    connection = sqlite3.connect(SOURCE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _load_transcript_from_files(meeting_date: str) -> tuple[str, str]:
    transcript_files = sorted(TRANSCRIPTS_DIR.glob(f"{meeting_date}_*.txt"))
    if not transcript_files:
        raise ValueError(f"No transcript found for meeting date '{meeting_date}' in {TRANSCRIPTS_DIR}.")

    chunks = [path.read_text(encoding="utf-8") for path in transcript_files]
    transcript_text = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
    if not transcript_text:
        raise ValueError(f"Transcript files for meeting date '{meeting_date}' are empty.")

    source_file = ";".join(path.name for path in transcript_files)
    return transcript_text, source_file


def _load_alias_map(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT alias, canonical FROM name_alias").fetchall()
    return {row["alias"]: row["canonical"] for row in rows}


def _canonicalize_names(raw_names: list[str], alias_map: dict[str, str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in raw_names:
        canonical_name = alias_map.get(raw_name, raw_name)
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        names.append(canonical_name)
    return names


def _load_councilmembers_for_date(connection: sqlite3.Connection, meeting_date: str) -> list[dict]:
    alias_map = _load_alias_map(connection)

    attendance_rows = connection.execute(
        """
        SELECT member
        FROM attendance
        WHERE meeting_date = ?
        ORDER BY member ASC
        """,
        (meeting_date,),
    ).fetchall()
    raw_names = [row["member"] for row in attendance_rows]

    if not raw_names:
        vote_rows = connection.execute(
            """
            SELECT DISTINCT vote.member AS member
            FROM vote
            INNER JOIN item ON item.id = vote.item_id
            WHERE item.meeting_date = ?
            ORDER BY vote.member ASC
            """,
            (meeting_date,),
        ).fetchall()
        raw_names = [row["member"] for row in vote_rows]

    if not raw_names:
        raise ValueError(f"No councilmembers found in source DB for meeting date '{meeting_date}'.")

    return [{"name": name} for name in _canonicalize_names(raw_names, alias_map)]


def get_meeting_analysis_input(meeting_date: str) -> tuple[dict, list[dict]]:
    transcript_text, _source_file = _load_transcript_from_files(meeting_date)
    with _connect_source_db() as connection:
        councilmembers = _load_councilmembers_for_date(connection, meeting_date)

    meeting = {
        "meeting_id": f"meeting_{meeting_date.replace('-', '_')}",
        "date": meeting_date,
        "transcript": transcript_text,
    }
    return meeting, councilmembers
