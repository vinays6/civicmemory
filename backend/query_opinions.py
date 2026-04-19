"""
Query stored per-member meeting opinions from the DB.

Usage:
    python query_opinions.py                       # list all (meeting_date, member) pairs
    python query_opinions.py --date 2026-01-15     # all opinions for a meeting
    python query_opinions.py --member "John Smith" # all opinions for a member (alias-aware)
"""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy import select

from db import default_engine, get_member_opinions, member_opinion


def list_all() -> int:
    with default_engine().connect() as conn:
        rows = conn.execute(
            select(member_opinion.c.meeting_date, member_opinion.c.member)
            .order_by(member_opinion.c.meeting_date.asc(), member_opinion.c.member.asc())
        ).all()
    for date, member in rows:
        print(f"{date}\t{member}")
    print(f"\n{len(rows)} opinion(s)", file=sys.stderr)
    return 0


def show_meeting(date: str) -> int:
    with default_engine().connect() as conn:
        rows = conn.execute(
            select(member_opinion.c.member, member_opinion.c.opinion_json)
            .where(member_opinion.c.meeting_date == date)
            .order_by(member_opinion.c.member.asc())
        ).all()
    if not rows:
        print(f"no opinions found for {date}", file=sys.stderr)
        return 1
    for member, opinion_json in rows:
        print(f"=== {member} ===")
        print(json.dumps(json.loads(opinion_json), indent=2, ensure_ascii=False))
        print()
    return 0


def show_member(name: str) -> int:
    opinions = get_member_opinions(name)
    if not opinions:
        print(f"no opinions found for {name!r}", file=sys.stderr)
        return 1
    for row in opinions:
        print(f"=== {row['meeting_date']}  (raw name: {row['member']}) ===")
        print(json.dumps(row["opinion"], indent=2, ensure_ascii=False))
        print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--date", help="show all opinions for a meeting_date (YYYY-MM-DD)")
    g.add_argument("--member", help="show all opinions for a canonical member name")
    args = ap.parse_args()

    if args.date:
        return show_meeting(args.date)
    if args.member:
        return show_member(args.member)
    return list_all()


if __name__ == "__main__":
    sys.exit(main())
