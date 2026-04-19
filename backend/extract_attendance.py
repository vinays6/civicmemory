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
from sqlalchemy import insert, select

from db import DEFAULT_DB_PATH, attendance as attendance_t, engine_for
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


def _reconcile_roll_call(
    pdf_name: str,
    present: list[str], reported_present: int,
    absent: list[str],  reported_absent: int,
) -> tuple[list[str], list[str]]:
    """If a name is in both lists, drop it from the side whose parsed
    count exceeds its reported count. Tie-break: drop from Present."""
    dupes = set(present) & set(absent)
    if not dupes:
        return present, absent
    for name in dupes:
        present_over = len(present) > reported_present
        absent_over = len(absent) > reported_absent
        if absent_over and not present_over:
            side = "absent"
            absent = [n for n in absent if n != name]
        elif present_over and not absent_over:
            side = "present"
            present = [n for n in present if n != name]
        else:
            side = "present"
            present = [n for n in present if n != name]
        print(
            f"warning: {pdf_name}: {name!r} listed as both Present and "
            f"Absent; dropped from {side} list to reconcile counts",
            file=sys.stderr,
        )
    return present, absent


def parse_pdf(pdf_path: Path) -> Attendance | None:
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
        if "Members Present" not in text and len(pdf.pages) > 1:
            text += "\n" + (pdf.pages[1].extract_text() or "")

    text = ZERO_WIDTH_RE.sub("", text)
    date_m = DATE_RE.search(text)
    if not date_m:
        return None
    md = datetime.strptime(date_m.group(0), "%B %d, %Y").date()

    roll = ROLL_CALL_RE.search(text)
    if not roll:
        return None

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

    present, absent = _reconcile_roll_call(
        pdf_path.name, present, exp_p, absent, int(roll.group("an") or 0),
    )
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


FILENAME_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def existing_meeting_dates(db_path: Path) -> set[str]:
    """ISO dates already recorded in the attendance table."""
    eng = engine_for(db_path)
    with eng.connect() as conn:
        return {
            d for (d,) in conn.execute(
                select(attendance_t.c.meeting_date).distinct()
            )
        }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    ap.add_argument("--force", action="store_true",
                    help="re-ingest meetings already in the DB")
    args = ap.parse_args()

    existing = set() if args.force else existing_meeting_dates(args.db)

    for pdf in args.pdfs:
        # Cheap pre-check: skip if the filename's YYYY-MM-DD prefix is
        # already in the DB. Avoids reopening PDFs we've already ingested.
        fn_match = FILENAME_DATE_RE.search(pdf.name)
        if fn_match and fn_match.group(1) in existing:
            print(f"{pdf.name}: {fn_match.group(1)} already ingested; skipped")
            continue

        att = parse_pdf(pdf)
        if att is None:
            print(f"warning: {pdf.name}: no roll-call or meeting date found; "
                  f"skipped", file=sys.stderr)
            continue

        iso = att.meeting_date.isoformat()
        if iso in existing:
            print(f"{pdf.name}: {iso} already ingested; skipped")
            continue

        write_db(args.db, att)
        existing.add(iso)
        print(f"{pdf.name}: {att.meeting_date} — "
              f"{len(att.present)} present, {len(att.absent)} absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
