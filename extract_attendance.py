"""
Extract roll-call attendance from LA City Council Journal PDFs.

Parses the 'Members Present: ...; Absent: ...' block that appears once per
meeting under the Roll Call heading. Raw names as they appear; resolve to
canonical at read time via the name_alias table.

    python extract_attendance.py sample_record.pdf [more.pdf ...]
"""

from __future__ import annotations

import argparse
import collections
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


def _dedupe_preserving_order(names: list[str]) -> tuple[list[str], list[str]]:
    seen: set[str] = set()
    deduped: list[str] = []
    duplicates: list[str] = []
    for name in names:
        if name in seen:
            duplicates.append(name)
            continue
        seen.add(name)
        deduped.append(name)
    return deduped, duplicates


def _reconcile_lists(
    pdf_name: str,
    present: list[str],
    absent: list[str],
    expected_present: int,
    expected_absent: int,
) -> tuple[list[str], list[str]]:
    present, present_dupes = _dedupe_preserving_order(present)
    absent, absent_dupes = _dedupe_preserving_order(absent)

    if present_dupes:
        print(
            f"warning: {pdf_name}: duplicate present names removed: {', '.join(present_dupes)}",
            file=sys.stderr,
        )
    if absent_dupes:
        print(
            f"warning: {pdf_name}: duplicate absent names removed: {', '.join(absent_dupes)}",
            file=sys.stderr,
        )

    absent_set = set(absent)
    overlap = [name for name in present if name in absent_set]
    if not overlap:
        return present, absent

    overlap_set = set(overlap)
    if len(present) - len(overlap) == expected_present:
        present = [name for name in present if name not in overlap_set]
        print(
            f"warning: {pdf_name}: removed overlapping names from present to match roll count: "
            f"{', '.join(overlap)}",
            file=sys.stderr,
        )
        return present, absent

    if len(absent) - len(overlap) == expected_absent:
        absent = [name for name in absent if name not in overlap_set]
        print(
            f"warning: {pdf_name}: removed overlapping names from absent to match roll count: "
            f"{', '.join(overlap)}",
            file=sys.stderr,
        )
        return present, absent

    print(
        f"warning: {pdf_name}: overlapping roll-call names remain unresolved; "
        f"preferring absent for database write: {', '.join(overlap)}",
        file=sys.stderr,
    )
    return present, absent


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
    absent_blob = roll.group("absent")
    absent = parse_names(absent_blob) if absent_blob else []
    exp_a = int(roll.group("an")) if roll.group("an") is not None else 0

    present, absent = _reconcile_lists(pdf_path.name, present, absent, exp_p, exp_a)

    if len(present) != exp_p:
        print(
            f"warning: {pdf_path.name}: parsed {len(present)} present names "
            f"but roll reports ({exp_p})",
            file=sys.stderr,
        )
    if roll.group("an") is not None:
        if len(absent) != exp_a:
            print(
                f"warning: {pdf_path.name}: parsed {len(absent)} absent names "
                f"but roll reports ({exp_a})",
                file=sys.stderr,
            )

    return Attendance(md, present, absent)


def write_db(db_path: Path, att: Attendance) -> None:
    eng = engine_for(db_path)
    d = att.meeting_date.isoformat()
    with eng.begin() as conn:
        conn.execute(
            attendance_t.delete().where(attendance_t.c.meeting_date == d)
        )
        status_by_member: "collections.OrderedDict[str, str]" = collections.OrderedDict()
        for member in att.present:
            status_by_member[member] = "present"
        for member in att.absent:
            if status_by_member.get(member) == "present":
                print(
                    f"warning: {d}: member {member} appeared in both present and absent; "
                    "writing absent",
                    file=sys.stderr,
                )
            status_by_member[member] = "absent"
        rows = [
            {"meeting_date": d, "member": member, "status": status}
            for member, status in status_by_member.items()
        ]
        if rows:
            conn.execute(insert(attendance_t), rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    args = ap.parse_args()

    for pdf in args.pdfs:
        try:
            att = parse_pdf(pdf)
        except ValueError as exc:
            message = str(exc)
            if "No roll-call block found" in message:
                print(f"skipping {pdf.name}: no roll-call block found", file=sys.stderr)
                continue
            if "No meeting date found" in message:
                print(f"skipping {pdf.name}: no meeting date found", file=sys.stderr)
                continue
            raise
        write_db(args.db, att)
        print(f"{pdf.name}: {att.meeting_date} — "
              f"{len(att.present)} present, {len(att.absent)} absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
