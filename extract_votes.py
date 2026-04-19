"""
Extract LA City Council voting records from Journal/Council Proceeding PDFs.

Writes raw names exactly as they appear in the PDF. Name normalization
happens at read time via the name_alias table (see roster.py).

Usage:
    python extract_votes.py sample_record.pdf [more.pdf ...]
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

from db import engine_for, item as item_t, meeting as meeting_t, vote as vote_t

ITEM_HEADER_RE = re.compile(r"^\((\d+)\)\s+([\w\-]+)\s*$", re.MULTILINE)
CD_RE = re.compile(r"^CD\s+([\w\-]+)", re.MULTILINE)
DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},\s+\d{4}"
)
TALLY_RE = re.compile(
    r"Ayes:\s*(?P<ayes>[^;]*?)\((?P<an>\d+)\)\s*;\s*"
    r"Nays:\s*(?P<nays>[^;]*?)\((?P<nn>\d+)\)\s*;\s*"
    r"Absent:\s*(?P<abs>[^\(]*?)\((?P<abn>\d+)\)",
    re.DOTALL,
)
DISPOSITION_RE = re.compile(
    r"^(Adopted\s+\w+|Adopted Item|Failed|Substitute Motion)", re.MULTILINE
)

ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")


@dataclass
class Vote:
    meeting_date: date
    item_number: int
    file_code: str
    council_district: str | None
    description: str
    disposition: str | None
    ayes: list[str]
    nays: list[str]
    absent: list[str]


def parse_names(blob: str) -> list[str]:
    """Split an Ayes/Nays/Absent name list. Handles 'Price Jr.' suffixes and
    names line-wrapped on a hyphen like 'Soto-\\nMartínez'."""
    blob = ZERO_WIDTH_RE.sub("", blob)
    blob = re.sub(r"-\s+", "-", blob)
    blob = re.sub(r"\s+", " ", blob).strip().rstrip(",")
    if not blob:
        return []
    parts = [p.strip() for p in blob.split(",")]
    out: list[str] = []
    for p in parts:
        if p in {"Jr.", "Sr.", "Jr", "Sr"} and out:
            out[-1] = f"{out[-1]} {p}"
        elif p:
            out.append(p)
    return out


def extract_meeting_date(text: str) -> date:
    m = DATE_RE.search(text)
    if not m:
        raise ValueError("Could not find meeting date in PDF")
    return datetime.strptime(m.group(0), "%B %d, %Y").date()


def extract_items(text: str, meeting_date: date) -> list[Vote]:
    matches = list(ITEM_HEADER_RE.finditer(text))
    votes: list[Vote] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        item_num = int(m.group(1))
        file_code = m.group(2)

        cd_match = CD_RE.search(block)
        cd = cd_match.group(1) if cd_match else None

        tally = TALLY_RE.search(block)
        if not tally:
            continue
        disp = DISPOSITION_RE.search(block)
        desc_end_idx = disp.start() if disp else tally.start()
        desc_start = cd_match.end() if cd_match else m.end()
        description = re.sub(r"\s+", " ", block[desc_start:desc_end_idx]).strip()

        votes.append(
            Vote(
                meeting_date=meeting_date,
                item_number=item_num,
                file_code=file_code,
                council_district=cd,
                description=description,
                disposition=disp.group(1).strip() if disp else None,
                ayes=parse_names(tally.group("ayes")),
                nays=parse_names(tally.group("nays")),
                absent=parse_names(tally.group("abs")),
            )
        )
    return votes


def parse_pdf(pdf_path: Path) -> list[Vote]:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    md = extract_meeting_date(text)
    return extract_items(text, md)


def write_db(db_path: Path, pdf_path: Path, votes: list[Vote]) -> None:
    if not votes:
        return
    eng = engine_for(db_path)
    meeting_date = votes[0].meeting_date.isoformat()
    with eng.begin() as conn:
        # Upsert the meeting row.
        conn.execute(meeting_t.delete().where(meeting_t.c.meeting_date == meeting_date))
        conn.execute(insert(meeting_t).values(
            meeting_date=meeting_date, source_pdf=pdf_path.name
        ))

        for v in votes:
            existing = conn.execute(
                select(item_t.c.id).where(
                    (item_t.c.meeting_date == meeting_date)
                    & (item_t.c.item_number == v.item_number)
                )
            ).scalar_one_or_none()

            if existing is None:
                res = conn.execute(insert(item_t).values(
                    meeting_date=meeting_date,
                    item_number=v.item_number,
                    file_code=v.file_code,
                    council_district=v.council_district,
                    description=v.description,
                    disposition=v.disposition,
                ))
                item_id = res.inserted_primary_key[0]
            else:
                item_id = existing

            # Clear any prior votes for this item so re-runs are clean.
            conn.execute(vote_t.delete().where(vote_t.c.item_id == item_id))
            rows = (
                [{"item_id": item_id, "member": n, "position": "aye"} for n in v.ayes]
                + [{"item_id": item_id, "member": n, "position": "nay"} for n in v.nays]
                + [{"item_id": item_id, "member": n, "position": "absent"} for n in v.absent]
            )
            if rows:
                conn.execute(insert(vote_t), rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="+", type=Path)
    ap.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    args = ap.parse_args()

    total = 0
    for pdf in args.pdfs:
        votes = parse_pdf(pdf)
        write_db(args.db, pdf, votes)
        print(f"{pdf.name}: {len(votes)} voted items")
        total += len(votes)
    print(f"Wrote {total} items to {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
