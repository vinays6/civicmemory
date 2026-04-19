from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Iterable, List

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, scoped_session, sessionmaker


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "civicmemory.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[str] = mapped_column(String, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)


class MeetingMemberSummary(Base):
    __tablename__ = "meeting_member_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    member_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


class MemberProfileRecord(Base):
    __tablename__ = "member_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_meeting(meeting_id: str, date: str, transcript: str) -> None:
    with session_scope() as session:
        meeting = session.get(Meeting, meeting_id)
        if meeting is None:
            meeting = Meeting(id=meeting_id, date=date, transcript=transcript)
            session.add(meeting)
        else:
            meeting.date = date
            meeting.transcript = transcript


def replace_meeting_member_summaries(
    meeting_id: str,
    member_summaries: Iterable[dict],
) -> None:
    with session_scope() as session:
        existing = session.scalars(
            select(MeetingMemberSummary).where(MeetingMemberSummary.meeting_id == meeting_id)
        ).all()
        for row in existing:
            session.delete(row)

        for summary in member_summaries:
            session.add(
                MeetingMemberSummary(
                    meeting_id=meeting_id,
                    member_name=summary["member_name"],
                    summary_json=json.dumps(summary, ensure_ascii=True),
                )
            )


def get_member_summaries(member_name: str) -> List[MeetingMemberSummary]:
    with session_scope() as session:
        rows = session.scalars(
            select(MeetingMemberSummary)
            .where(MeetingMemberSummary.member_name == member_name)
            .order_by(MeetingMemberSummary.meeting_id.asc())
        ).all()
        return rows


def get_all_member_summaries() -> List[MeetingMemberSummary]:
    with session_scope() as session:
        rows = session.scalars(
            select(MeetingMemberSummary).order_by(
                MeetingMemberSummary.member_name.asc(), MeetingMemberSummary.meeting_id.asc()
            )
        ).all()
        return rows


def get_distinct_member_names() -> List[str]:
    with session_scope() as session:
        rows = session.execute(
            select(MeetingMemberSummary.member_name).distinct().order_by(MeetingMemberSummary.member_name.asc())
        ).all()
        return [row[0] for row in rows]


def upsert_member_profile(member_name: str, profile_json: dict) -> None:
    with session_scope() as session:
        record = session.scalars(
            select(MemberProfileRecord).where(MemberProfileRecord.member_name == member_name)
        ).first()
        now = datetime.now(timezone.utc)
        payload = json.dumps(profile_json, ensure_ascii=True)
        if record is None:
            session.add(
                MemberProfileRecord(
                    member_name=member_name,
                    profile_json=payload,
                    updated_at=now,
                )
            )
        else:
            record.profile_json = payload
            record.updated_at = now


def get_member_profile(member_name: str) -> MemberProfileRecord | None:
    with session_scope() as session:
        return session.scalars(
            select(MemberProfileRecord).where(MemberProfileRecord.member_name == member_name)
        ).first()


def get_all_member_profiles() -> List[MemberProfileRecord]:
    with session_scope() as session:
        rows = session.scalars(
            select(MemberProfileRecord).order_by(MemberProfileRecord.member_name.asc())
        ).all()
        return rows

