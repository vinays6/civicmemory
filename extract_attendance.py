"""
Extract roll-call attendance from LA City Council Journal PDFs.

Parses the 'Members Present: ...; Absent: ...' block that appears once per
meeting under the Roll Call heading. This is the meeting-opening roll and
reflects who was seated at the start — it is distinct from the per-item
'Absent:' tallies that can shift as members step out.

Usage:
    python extract_attendance.py sample_record.pdf [more.pdf ...]

Writes to the same votes.sqlite used by extract_votes.py, into a new
'attendance' table.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pdfplumber

from extract_votes import ZERO_WIDTH_RE, parse_names

DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},\s+\d{4}"
)

# Roll-call block. The 'Absent' clause is optional: if the entire council is
# seated, the journal sometimes omits it.
ROLL_CALL_RE = re.compile(
    r"Members\s+Present:\s*(?P<present>.*?)\((?P<pn>\d+)\)\s*"
    r"(?:;\s*Absent:\s*(?P<absent>[^\(]*?)\((?P<an>\d+)\))?",
    re.DOTALL,
)


@dataclass
class Attendance:
    meeting_date: date
    present: list[str]
    absent: list[str]
    source_pdf: str


def parse_pdf(pdf_path: Path) -> Attendance:
    with pdfplumber.open(pdf_path) as pdf:
        # Roll call always appears on page 1; read just enough text.
        text = pdf.pages[0].extract_text() or ""
        if "Members Present" not in text and len(pdf.pages) > 1:
            text += "\n" + (pdf.pages[1].extract_text() or "")

    text = ZERO_WIDTH_RE.sub("", text)
    date_m = DATE_RE.search(text)
    if not date_m:
        raise ValueError(f"No meeting date found in {pdf_path}")
    meeting_date = datetime.strptime(date_m.group(0), "%B %d, %Y").date()

    roll = ROLL_CALL_RE.search(text)
    if not roll:
        raise ValueError(f"No roll-call block found in {pdf_path}")

    present = parse_names(roll.group("present"))
    expected_present = int(roll.group("pn"))
    if len(present) != expected_present:
        print(
            f"warning: {pdf_path.name}: parsed {len(present)} present names "
            f"but roll reports ({expected_present})",
            file=sys.stderr,
        )

    absent_blob = roll.group("absent")
    absent = parse_names(absent_blob) if absent_blob else []
    if roll.group("an") is not None:
        expected_absent = int(roll.group("an"))
        if len(absent) != expected_absent:
            print(
                f"warning: {pdf_path.name}: parsed {len(absent)} absent names "
                f"but roll reports ({expected_absent})",
                file=sys.stderr,
            )

    return Attendance(meeting_date, present, absent, pdf_path.name)


SCHEMA = """
CREATE TABLE IF NOT EXISTS attendance (
    meeting_date TEXT NOT NULL,
    member       TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('present','absent')),
    PRIMARY KEY (meeting_date, member)
);
CREATE INDEX IF NOT EXISTS idx_attendance_member ON attendance(member);
"""


def write_db(db_path: Path, att: Attendance) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        d = att.meeting_date.isoformat()
        # Replace any prior attendance rows for this meeting — makes reruns safe.
        conn.execute("DELETE FROM attendance WHERE meeting_date = ?", (d,))
        rows = [(d, m, "present") for m in att.present] + \
               [(d, m, "absent") for m in att.absent]
        conn.executemany(
            "INSERT INTO attendance (meeting_date, member, status) VALUES (?, ?, ?)",
            rows,
        )
        # Ensure councilmember table (from extract_votes.py schema) has everyone.
        conn.executemany(
            "INSERT OR IGNORE INTO councilmember (name) VALUES (?)",
            [(m,) for m in att.present + att.absent],
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    args = ap.parse_args()

    for pdf in args.pdfs:
        att = parse_pdf(pdf)
        write_db(args.db, att)
        print(
            f"{pdf.name}: {att.meeting_date} — "
            f"{len(att.present)} present, {len(att.absent)} absent"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
