"""
Extract LA City Council voting records from Journal/Council Proceeding PDFs.

Usage:
    python extract_votes.py sample_record.pdf [more.pdf ...]

Output: votes.sqlite with a normalized schema.
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

NAME_TOKEN = r"[A-Z][A-Za-zÀ-ÿ'\-\.]+(?:\s+Jr\.|\s+Sr\.|\-[A-Z][A-Za-zÀ-ÿ]+)?"
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
MOTION_RE = re.compile(r"Adopted Motion\s*\(([^)]+)\)", re.IGNORECASE)
DISPOSITION_RE = re.compile(r"^(Adopted\s+\w+|Adopted Item|Failed|Substitute Motion)", re.MULTILINE)


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


ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")


def parse_names(blob: str) -> list[str]:
    """Split an Ayes/Nays/Absent name list. Handles 'Price Jr.' etc."""
    blob = ZERO_WIDTH_RE.sub("", blob)
    # Repair line-wrapped hyphenated names: "Soto-\nMartínez" → "Soto-Martínez".
    blob = re.sub(r"-\s+", "-", blob)
    blob = re.sub(r"\s+", " ", blob).strip().rstrip(",")
    if not blob:
        return []
    parts = [p.strip() for p in blob.split(",")]
    out: list[str] = []
    for p in parts:
        # Merge "Jr." / "Sr." suffix back onto previous name.
        if p in {"Jr.", "Sr.", "Jr", "Sr"} and out:
            out[-1] = f"{out[-1]} {p}"
        elif p:
            out.append(p)
    return out


def extract_meeting_date(full_text: str) -> date:
    m = DATE_RE.search(full_text)
    if not m:
        raise ValueError("Could not find meeting date in PDF")
    return datetime.strptime(m.group(0), "%B %d, %Y").date()


def extract_items(full_text: str, meeting_date: date) -> list[Vote]:
    """Split text into per-item blocks keyed by '(N) file-code'."""
    matches = list(ITEM_HEADER_RE.finditer(full_text))
    votes: list[Vote] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[start:end]
        item_num = int(m.group(1))
        file_code = m.group(2)

        cd_match = CD_RE.search(block)
        cd = cd_match.group(1) if cd_match else None

        # Description: content between the header (and optional CD line) and
        # the tally / disposition. Collapse whitespace.
        tally = TALLY_RE.search(block)
        if not tally:
            # No vote recorded on this item (e.g. referred, deferred).
            continue
        desc_end = DISPOSITION_RE.search(block)
        desc_end_idx = desc_end.start() if desc_end else tally.start()
        desc_start = cd_match.end() if cd_match else m.end()
        description = re.sub(r"\s+", " ", block[desc_start:desc_end_idx]).strip()

        disposition = desc_end.group(1).strip() if desc_end else None

        votes.append(
            Vote(
                meeting_date=meeting_date,
                item_number=item_num,
                file_code=file_code,
                council_district=cd,
                description=description,
                disposition=disposition,
                ayes=parse_names(tally.group("ayes")),
                nays=parse_names(tally.group("nays")),
                absent=parse_names(tally.group("abs")),
            )
        )
    return votes


def parse_pdf(pdf_path: Path) -> list[Vote]:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    meeting_date = extract_meeting_date(text)
    return extract_items(text, meeting_date)


SCHEMA = """
CREATE TABLE IF NOT EXISTS councilmember (
    name TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS meeting (
    meeting_date TEXT PRIMARY KEY,
    source_pdf   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS item (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_date     TEXT NOT NULL REFERENCES meeting(meeting_date),
    item_number      INTEGER NOT NULL,
    file_code        TEXT NOT NULL,
    council_district TEXT,
    description      TEXT,
    disposition      TEXT,
    UNIQUE (meeting_date, item_number)
);
CREATE TABLE IF NOT EXISTS vote (
    item_id    INTEGER NOT NULL REFERENCES item(id),
    member     TEXT    NOT NULL REFERENCES councilmember(name),
    position   TEXT    NOT NULL CHECK (position IN ('aye','nay','absent')),
    PRIMARY KEY (item_id, member)
);
CREATE INDEX IF NOT EXISTS idx_vote_member ON vote(member);
CREATE INDEX IF NOT EXISTS idx_vote_position ON vote(position);
"""


def write_db(db_path: Path, pdf_path: Path, votes: list[Vote]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        if not votes:
            return
        meeting_date = votes[0].meeting_date.isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO meeting VALUES (?, ?)",
            (meeting_date, str(pdf_path.name)),
        )
        for v in votes:
            cur = conn.execute(
                """INSERT OR IGNORE INTO item
                   (meeting_date, item_number, file_code, council_district,
                    description, disposition)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (meeting_date, v.item_number, v.file_code, v.council_district,
                 v.description, v.disposition),
            )
            item_id = cur.lastrowid or conn.execute(
                "SELECT id FROM item WHERE meeting_date=? AND item_number=?",
                (meeting_date, v.item_number),
            ).fetchone()[0]

            for position, names in (("aye", v.ayes), ("nay", v.nays), ("absent", v.absent)):
                for name in names:
                    conn.execute(
                        "INSERT OR IGNORE INTO councilmember VALUES (?)", (name,)
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO vote VALUES (?, ?, ?)",
                        (item_id, name, position),
                    )
        conn.commit()
    finally:
        conn.close()


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
