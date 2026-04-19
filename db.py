"""
SQLAlchemy schema and helpers for civicmemory.

Model: vote.member and attendance.member store RAW names as they appear
in each PDF. A separate name_alias(alias -> canonical) table, populated
from roster.json via `roster.py apply`, is consulted at read time to
resolve variants. Aliases are never written destructively over raw data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

meeting = Table(
    "meeting",
    metadata,
    Column("meeting_date", String, primary_key=True),
    Column("source_pdf", String, nullable=False),
)

item = Table(
    "item",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("meeting_date", String,
           ForeignKey("meeting.meeting_date"), nullable=False),
    Column("item_number", Integer, nullable=False),
    Column("file_code", String, nullable=False),
    Column("council_district", String),
    Column("description", String),
    Column("disposition", String),
    UniqueConstraint("meeting_date", "item_number", name="uq_item_meeting_num"),
)

vote = Table(
    "vote",
    metadata,
    Column("item_id", Integer, ForeignKey("item.id"),
           primary_key=True, nullable=False),
    Column("member", String, primary_key=True, nullable=False),
    Column("position", String, nullable=False),
    CheckConstraint("position IN ('aye','nay','absent')", name="ck_vote_pos"),
)
Index("idx_vote_member", vote.c.member)
Index("idx_vote_position", vote.c.position)

attendance = Table(
    "attendance",
    metadata,
    Column("meeting_date", String, primary_key=True, nullable=False),
    Column("member", String, primary_key=True, nullable=False),
    Column("status", String, nullable=False),
    CheckConstraint("status IN ('present','absent')", name="ck_att_status"),
)
Index("idx_attendance_member", attendance.c.member)

name_alias = Table(
    "name_alias",
    metadata,
    Column("alias", String, primary_key=True),
    Column("canonical", String, nullable=False),
)
Index("idx_name_alias_canonical", name_alias.c.canonical)


def engine_for(db: str | Path) -> Engine:
    """SQLite engine for a given path. Creates all tables on first use."""
    eng = create_engine(f"sqlite:///{db}", future=True)
    metadata.create_all(eng)
    return eng


# ---------------------------------------------------------------------------
# Alias-map read helpers — applied at query time, never mutate the raw tables
# ---------------------------------------------------------------------------

def load_alias_map(conn) -> dict[str, str]:
    """Returns {alias: canonical}. Self-canonicals are not stored; callers
    should fall through to the raw name when a lookup misses."""
    rows = conn.execute(select(name_alias.c.alias, name_alias.c.canonical)).all()
    return {a: c for a, c in rows}


def canonical(raw: str, alias_map: dict[str, str]) -> str:
    """Map a raw name to its canonical form. Unknown raws pass through."""
    return alias_map.get(raw, raw)


def canonical_members(conn, alias_map: dict[str, str] | None = None) -> list[str]:
    """All canonical names observed in vote or attendance, sorted."""
    if alias_map is None:
        alias_map = load_alias_map(conn)
    raws: set[str] = set()
    for (m,) in conn.execute(select(vote.c.member).distinct()):
        raws.add(m)
    for (m,) in conn.execute(select(attendance.c.member).distinct()):
        raws.add(m)
    return sorted({canonical(m, alias_map) for m in raws})


def all_raw_names(conn) -> Iterable[tuple[str, int]]:
    """Yield (raw_name, frequency) across vote + attendance."""
    from collections import Counter
    counts: Counter[str] = Counter()
    for (m,) in conn.execute(select(vote.c.member)):
        counts[m] += 1
    for (m,) in conn.execute(select(attendance.c.member)):
        counts[m] += 1
    return counts.items()
