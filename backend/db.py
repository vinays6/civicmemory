"""
SQLAlchemy schema and helpers for civicmemory.

Unified schema covering:
  - Structured roll-call extracts: meeting, item, vote, attendance
  - Identity resolution: name_alias (alias -> canonical)
  - LLM-synthesized content: member_opinion (per-meeting), member_profile
    (rolled up across meetings)

Raw names (as printed in each PDF or spoken in transcripts) are stored in
vote.member, attendance.member, and member_opinion.member. The name_alias
table is consulted at read time to resolve variants; aliases are never
written destructively over raw data. member_profile is keyed by the
canonical name since it aggregates across all spellings.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "civicmemory.db"

metadata = MetaData()

meeting = Table(
    "meeting",
    metadata,
    Column("meeting_date", String, primary_key=True),
    Column("source_pdf", String),
    Column("transcript", Text),
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

member_opinion = Table(
    "member_opinion",
    metadata,
    Column("meeting_date", String,
           ForeignKey("meeting.meeting_date"), primary_key=True),
    Column("member", String, primary_key=True),
    Column("opinion_json", Text, nullable=False),
    Column("model", String),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index("idx_member_opinion_member", member_opinion.c.member)

member_profile = Table(
    "member_profile",
    metadata,
    Column("member_canonical", String, primary_key=True),
    Column("profile_json", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def engine_for(db: str | Path) -> Engine:
    """SQLite engine for a given path. Creates all tables on first use."""
    eng = create_engine(f"sqlite:///{db}", future=True)
    metadata.create_all(eng)
    return eng


_default_engine: Engine | None = None


def default_engine() -> Engine:
    global _default_engine
    if _default_engine is None:
        _default_engine = engine_for(DEFAULT_DB_PATH)
    return _default_engine


def init_db() -> None:
    """Ensure the default DB exists with all tables."""
    default_engine()


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


def raw_names_for(canonical_name: str, alias_map: dict[str, str]) -> set[str]:
    """All raw spellings that resolve to a given canonical (incl. self)."""
    raws = {a for a, c in alias_map.items() if c == canonical_name}
    raws.add(canonical_name)
    return raws


def members_for_meeting(meeting_date: str) -> list[str]:
    """Canonical names observed in attendance or votes for a given meeting.
    Falls back to all canonical members if the meeting has no roll-call data
    ingested yet (e.g. transcript analysis running before attendance extract)."""
    eng = default_engine()
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
        raws: set[str] = set()
        for (m,) in conn.execute(
            select(attendance.c.member).where(attendance.c.meeting_date == meeting_date)
        ):
            raws.add(m)
        for (m,) in conn.execute(
            select(vote.c.member)
            .join(item, vote.c.item_id == item.c.id)
            .where(item.c.meeting_date == meeting_date)
            .distinct()
        ):
            raws.add(m)
        if raws:
            return sorted({canonical(m, alias_map) for m in raws})
        return canonical_members(conn, alias_map)


def canonical_members(conn, alias_map: dict[str, str] | None = None) -> list[str]:
    """All canonical names observed in vote, attendance, or opinion — sorted."""
    if alias_map is None:
        alias_map = load_alias_map(conn)
    raws: set[str] = set()
    for (m,) in conn.execute(select(vote.c.member).distinct()):
        raws.add(m)
    for (m,) in conn.execute(select(attendance.c.member).distinct()):
        raws.add(m)
    for (m,) in conn.execute(select(member_opinion.c.member).distinct()):
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


# ---------------------------------------------------------------------------
# LLM-output helpers (meeting transcript + per-member opinions + profiles)
# ---------------------------------------------------------------------------

def upsert_meeting(meeting_date: str, transcript: str | None = None,
                   source_pdf: str | None = None) -> None:
    """Create or update a meeting row. Only overwrites columns you pass."""
    eng = default_engine()
    with eng.begin() as conn:
        existing = conn.execute(
            select(meeting.c.meeting_date).where(meeting.c.meeting_date == meeting_date)
        ).first()
        values = {}
        if transcript is not None:
            values["transcript"] = transcript
        if source_pdf is not None:
            values["source_pdf"] = source_pdf
        if existing is None:
            conn.execute(insert(meeting).values(meeting_date=meeting_date, **values))
        elif values:
            conn.execute(
                update(meeting).where(meeting.c.meeting_date == meeting_date).values(**values)
            )


def replace_member_opinions(
    meeting_date: str,
    opinions: Iterable[dict],
    model: str | None = None,
) -> None:
    """Delete all opinions for a meeting and re-insert. Each opinion dict
    must contain 'member_name'; the full dict is stored as opinion_json."""
    eng = default_engine()
    now = datetime.now(timezone.utc)
    with eng.begin() as conn:
        conn.execute(delete(member_opinion).where(member_opinion.c.meeting_date == meeting_date))
        rows = [
            {
                "meeting_date": meeting_date,
                "member": op["member_name"],
                "opinion_json": json.dumps(op, ensure_ascii=True),
                "model": model,
                "updated_at": now,
            }
            for op in opinions
        ]
        if rows:
            conn.execute(insert(member_opinion), rows)


def get_member_opinions(canonical_name: str) -> list[dict]:
    """All opinions for a canonical member, resolved through name_alias.
    Returns dicts: {meeting_date, member (raw), opinion, model, updated_at}."""
    eng = default_engine()
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
        raws = raw_names_for(canonical_name, alias_map)
        rows = conn.execute(
            select(
                member_opinion.c.meeting_date,
                member_opinion.c.member,
                member_opinion.c.opinion_json,
                member_opinion.c.model,
                member_opinion.c.updated_at,
            )
            .where(member_opinion.c.member.in_(raws))
            .order_by(member_opinion.c.meeting_date.asc())
        ).all()
        return [
            {
                "meeting_date": r.meeting_date,
                "member": r.member,
                "opinion": json.loads(r.opinion_json),
                "model": r.model,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]


def get_distinct_opinion_members() -> list[str]:
    """Distinct canonical names across all member_opinion rows."""
    eng = default_engine()
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
        raws = [r[0] for r in conn.execute(select(member_opinion.c.member).distinct())]
        return sorted({canonical(m, alias_map) for m in raws})


def upsert_member_profile(member_canonical_name: str, profile_json: dict) -> None:
    eng = default_engine()
    now = datetime.now(timezone.utc)
    payload = json.dumps(profile_json, ensure_ascii=True)
    with eng.begin() as conn:
        existing = conn.execute(
            select(member_profile.c.member_canonical)
            .where(member_profile.c.member_canonical == member_canonical_name)
        ).first()
        if existing is None:
            conn.execute(insert(member_profile).values(
                member_canonical=member_canonical_name,
                profile_json=payload,
                updated_at=now,
            ))
        else:
            conn.execute(
                update(member_profile)
                .where(member_profile.c.member_canonical == member_canonical_name)
                .values(profile_json=payload, updated_at=now)
            )


def get_member_profile(member_canonical_name: str) -> dict | None:
    eng = default_engine()
    with eng.connect() as conn:
        row = conn.execute(
            select(member_profile.c.member_canonical,
                   member_profile.c.profile_json,
                   member_profile.c.updated_at)
            .where(member_profile.c.member_canonical == member_canonical_name)
        ).first()
        if row is None:
            return None
        return {
            "member_canonical": row.member_canonical,
            "profile": json.loads(row.profile_json),
            "updated_at": row.updated_at,
        }


def get_all_member_profiles() -> list[dict]:
    eng = default_engine()
    with eng.connect() as conn:
        rows = conn.execute(
            select(member_profile.c.member_canonical,
                   member_profile.c.profile_json,
                   member_profile.c.updated_at)
            .order_by(member_profile.c.member_canonical.asc())
        ).all()
        return [
            {
                "member_canonical": r.member_canonical,
                "profile": json.loads(r.profile_json),
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
