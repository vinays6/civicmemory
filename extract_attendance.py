"""
Extract roll-call attendance from LA City Council Journal PDFs.

Parses the 'Members Present: ...; Absent: ...' block that appears once per
meeting under the Roll Call heading. Raw names as they appear; resolve to
canonical at read time via the name_alias table.

    python extract_attendance.py sample_record.pdf [more.pdf ...]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pdfplumber
from sqlalchemy import insert

from db import attendance as attendance_t, engine_for
from extract_votes import ZERO_WIDTH_RE, parse_names

DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},\s+\d{4}"
)

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


def parse_pdf(pdf_path: Path) -> Attendance:
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
        if "Members Present" not in text and len(pdf.pages) > 1:
            text += "\n" + (pdf.pages[1].extract_text() or "")

    text = ZERO_WIDTH_RE.sub("", text)
    date_m = DATE_RE.search(text)
    if not date_m:
        raise ValueError(f"No meeting date found in {pdf_path}")
    md = datetime.strptime(date_m.group(0), "%B %d, %Y").date()

    roll = ROLL_CALL_RE.search(text)
    if not roll:
        raise ValueError(f"No roll-call block found in {pdf_path}")

    present = parse_names(roll.group("present"))
    exp_p = int(roll.group("pn"))
    if len(present) != exp_p:
        print(f"warning: {pdf_path.name}: parsed {len(present)} present names "
              f"but roll reports ({exp_p})", file=sys.stderr)

    absent_blob = roll.group("absent")
    absent = parse_names(absent_blob) if absent_blob else []
    if roll.group("an") is not None:
        exp_a = int(roll.group("an"))
        if len(absent) != exp_a:
            print(f"warning: {pdf_path.name}: parsed {len(absent)} absent names "
                  f"but roll reports ({exp_a})", file=sys.stderr)

    return Attendance(md, present, absent)


def write_db(db_path: Path, att: Attendance) -> None:
    eng = engine_for(db_path)
    d = att.meeting_date.isoformat()
    with eng.begin() as conn:
        conn.execute(
            attendance_t.delete().where(attendance_t.c.meeting_date == d)
        )
        rows = (
            [{"meeting_date": d, "member": m, "status": "present"} for m in att.present]
            + [{"meeting_date": d, "member": m, "status": "absent"} for m in att.absent]
        )
        if rows:
            conn.execute(insert(attendance_t), rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    args = ap.parse_args()

    for pdf in args.pdfs:
        att = parse_pdf(pdf)
        write_db(args.db, att)
        print(f"{pdf.name}: {att.meeting_date} — "
              f"{len(att.present)} present, {len(att.absent)} absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
