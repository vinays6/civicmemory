"""
JSON-output CLI for querying the civicmemory voting database.

Designed for LLM consumption: every subcommand writes a single JSON document
to stdout; human-readable errors go to stderr with a nonzero exit code.
Names in input args and output are canonical (alias-resolved).

Subcommands:
    members                       List canonical member names.
    meetings                      List meeting dates (+ item counts).
    items       [filters]         List agenda items.
    item        <item_id>         Full detail + per-member votes for one item.
    votes       <member>          Vote history for a member.
    member      <member>          Per-member stats (counts, dissent, partners).
    agreement   [--pair A B]      Pairwise agreement rate(s).
    dissent                       Dissent profile per member.
    lone-wolf   [--member M]      Items where one member was alone.
    pivotal     [--member M]      Kingmaker scores (pivotal votes).
    contested                     Items with ≥1 nay.
    search      <query>           LIKE-search item descriptions.
    sql         <select-stmt>     Execute a read-only SELECT.

Global flags:
    --db PATH                     Override database path.
    --limit N                     Cap list outputs (default 50; 0 = no limit).
    --contested-only              Restrict pairwise stats to contested items.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import func, select, text

from db import (
    DEFAULT_DB_PATH,
    canonical,
    canonical_members,
    engine_for,
    item as item_t,
    load_alias_map,
    meeting as meeting_t,
    raw_names_for,
    vote as vote_t,
)
from analyze_votes import (
    MIN_OVERLAP,
    controversial_items,
    kingmaker_score,
    load_votes,
    member_stats,
    precompute_matrices,
)


def _emit(payload: Any) -> int:
    json.dump(payload, sys.stdout, indent=2, default=str, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def _fail(msg: str, code: int = 1) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return code


def _resolve(name: str, alias_map: dict[str, str], members: list[str]) -> str | None:
    """Map user-supplied name to a canonical member. Accepts canonical or raw."""
    c = canonical(name, alias_map)
    if c in members:
        return c
    # case-insensitive fallback
    low = name.lower()
    for m in members:
        if m.lower() == low:
            return m
    return None


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def cmd_members(args) -> int:
    eng = engine_for(args.db)
    with eng.connect() as conn:
        return _emit(canonical_members(conn))


def cmd_meetings(args) -> int:
    eng = engine_for(args.db)
    with eng.connect() as conn:
        rows = conn.execute(
            select(
                meeting_t.c.meeting_date,
                meeting_t.c.source_pdf,
                func.count(item_t.c.id).label("item_count"),
            )
            .select_from(
                meeting_t.outerjoin(item_t, meeting_t.c.meeting_date == item_t.c.meeting_date)
            )
            .group_by(meeting_t.c.meeting_date)
            .order_by(meeting_t.c.meeting_date.asc())
        ).all()
    return _emit([
        {"meeting_date": r[0], "source_pdf": r[1], "item_count": r[2]}
        for r in rows
    ])


def cmd_items(args) -> int:
    eng = engine_for(args.db)
    stmt = select(
        item_t.c.id, item_t.c.meeting_date, item_t.c.item_number,
        item_t.c.file_code, item_t.c.council_district,
        item_t.c.description, item_t.c.disposition,
    )
    if args.date:
        stmt = stmt.where(item_t.c.meeting_date == args.date)
    if args.cd:
        stmt = stmt.where(item_t.c.council_district == args.cd)
    if args.search:
        stmt = stmt.where(item_t.c.description.ilike(f"%{args.search}%"))
    stmt = stmt.order_by(item_t.c.meeting_date.asc(), item_t.c.item_number.asc())

    with eng.connect() as conn:
        rows = conn.execute(stmt).all()
        if args.contested:
            contested_ids = {
                r[0] for r in conn.execute(
                    select(vote_t.c.item_id)
                    .where(vote_t.c.position == "nay")
                    .group_by(vote_t.c.item_id)
                )
            }
            rows = [r for r in rows if r[0] in contested_ids]

    if args.limit:
        rows = rows[:args.limit]

    return _emit([
        {"item_id": r[0], "meeting_date": r[1], "item_number": r[2],
         "file_code": r[3], "council_district": r[4],
         "description": r[5], "disposition": r[6]}
        for r in rows
    ])


def cmd_item(args) -> int:
    eng = engine_for(args.db)
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
        irow = conn.execute(
            select(item_t).where(item_t.c.id == args.item_id)
        ).mappings().first()
        if not irow:
            return _fail(f"no item with id={args.item_id}")
        vrows = conn.execute(
            select(vote_t.c.member, vote_t.c.position)
            .where(vote_t.c.item_id == args.item_id)
        ).all()

    tally = {"aye": 0, "nay": 0, "absent": 0}
    votes: list[dict[str, str]] = []
    for raw, pos in vrows:
        tally[pos] = tally.get(pos, 0) + 1
        votes.append({"member": canonical(raw, alias_map), "position": pos})
    votes.sort(key=lambda v: (v["position"], v["member"]))

    return _emit({
        "item_id": irow["id"],
        "meeting_date": irow["meeting_date"],
        "item_number": irow["item_number"],
        "file_code": irow["file_code"],
        "council_district": irow["council_district"],
        "description": irow["description"],
        "disposition": irow["disposition"],
        "tally": tally,
        "contested": tally["nay"] > 0,
        "votes": votes,
    })


def cmd_votes(args) -> int:
    eng = engine_for(args.db)
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
        members = canonical_members(conn, alias_map)
        resolved = _resolve(args.member, alias_map, members)
        if resolved is None:
            return _fail(f"unknown member: {args.member!r}")
        raws = raw_names_for(resolved, alias_map)
        rows = conn.execute(
            select(
                item_t.c.id, item_t.c.meeting_date, item_t.c.item_number,
                item_t.c.file_code, item_t.c.description, item_t.c.disposition,
                vote_t.c.position,
            )
            .join(item_t, vote_t.c.item_id == item_t.c.id)
            .where(vote_t.c.member.in_(raws))
            .order_by(item_t.c.meeting_date.asc(), item_t.c.item_number.asc())
        ).all()

    out = [
        {"item_id": r[0], "meeting_date": r[1], "item_number": r[2],
         "file_code": r[3], "description": r[4], "disposition": r[5],
         "position": r[6]}
        for r in rows
    ]
    if args.limit:
        out = out[:args.limit]
    return _emit({"member": resolved, "count": len(rows), "votes": out})


def cmd_member(args) -> int:
    members, by_item, items_meta = load_votes(args.db)
    eng = engine_for(args.db)
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
    resolved = _resolve(args.member, alias_map, members)
    if resolved is None:
        return _fail(f"unknown member: {args.member!r}")
    matrices = precompute_matrices(members, by_item)
    return _emit(member_stats(resolved, members, by_item, items_meta, matrices))


def cmd_agreement(args) -> int:
    members, by_item, _ = load_votes(args.db)
    matrices = precompute_matrices(members, by_item)
    key = "agreement_contested" if args.contested_only else "agreement"
    tkey = key + "_total"
    rate, total = matrices[key], matrices[tkey]

    if args.pair:
        eng = engine_for(args.db)
        with eng.connect() as conn:
            alias_map = load_alias_map(conn)
        a = _resolve(args.pair[0], alias_map, members)
        b = _resolve(args.pair[1], alias_map, members)
        if a is None or b is None:
            return _fail(f"unknown member in pair: {args.pair}")
        i, j = members.index(a), members.index(b)
        r, n = rate[i, j], int(total[i, j])
        return _emit({
            "a": a, "b": b,
            "agreement_rate": None if np.isnan(r) else float(r),
            "co_participation": n,
            "contested_only": bool(args.contested_only),
            "min_overlap_warning": n < MIN_OVERLAP,
        })

    idx = {m: i for i, m in enumerate(members)}
    matrix: dict[str, dict[str, Any]] = {}
    for a in members:
        row: dict[str, Any] = {}
        for b in members:
            if a == b:
                continue
            i, j = idx[a], idx[b]
            r, n = rate[i, j], int(total[i, j])
            row[b] = {
                "rate": None if np.isnan(r) else float(r),
                "n": n,
            }
        matrix[a] = row
    return _emit({
        "contested_only": bool(args.contested_only),
        "min_overlap": MIN_OVERLAP,
        "matrix": matrix,
    })


def cmd_dissent(args) -> int:
    members, by_item, items_meta = load_votes(args.db)
    matrices = precompute_matrices(members, by_item)
    profiles = []
    for m in members:
        s = member_stats(m, members, by_item, items_meta, matrices)
        profiles.append({
            "member": m,
            "aye": s["vote_counts"]["aye"],
            "nay": s["vote_counts"]["nay"],
            "absent": s["vote_counts"]["absent"],
            "aye_rate": s["aye_rate"],
            "participation_rate": s["participation_rate"],
            "dissent_rate": s["dissent_rate"],
            "lone_wolf_count": len(s["lone_wolf_items"]),
            "top_codissent_partners": s["top_codissent_partners"],
        })
    profiles.sort(key=lambda p: p["dissent_rate"], reverse=True)
    return _emit(profiles)


def cmd_lone_wolf(args) -> int:
    members, by_item, items_meta = load_votes(args.db)
    eng = engine_for(args.db)
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
    targets: list[str]
    if args.member:
        resolved = _resolve(args.member, alias_map, members)
        if resolved is None:
            return _fail(f"unknown member: {args.member!r}")
        targets = [resolved]
    else:
        targets = members

    out = []
    for m in targets:
        for item_id, votes in by_item.items():
            pos = votes.get(m)
            if pos not in ("aye", "nay"):
                continue
            same = [mm for mm, pp in votes.items() if pp == pos]
            other = sum(1 for pp in votes.values() if pp in ("aye", "nay") and pp != pos)
            if len(same) == 1 and other > 0:
                meta = items_meta.get(item_id, {})
                out.append({
                    "member": m,
                    "position": pos,
                    "item_id": item_id,
                    "meeting_date": meta.get("meeting_date"),
                    "item_number": meta.get("item_number"),
                    "file_code": meta.get("file_code"),
                    "description": meta.get("description"),
                })
    out.sort(key=lambda r: (r["meeting_date"] or "", r["item_number"] or 0))
    if args.limit:
        out = out[:args.limit]
    return _emit(out)


def cmd_pivotal(args) -> int:
    members, by_item, items_meta = load_votes(args.db)
    eng = engine_for(args.db)
    with eng.connect() as conn:
        alias_map = load_alias_map(conn)
    if args.member:
        resolved = _resolve(args.member, alias_map, members)
        if resolved is None:
            return _fail(f"unknown member: {args.member!r}")
        score = kingmaker_score(resolved, members, by_item)
        score["flipped"] = [
            {"item_id": iid, **{k: items_meta.get(iid, {}).get(k)
                                for k in ("meeting_date", "item_number",
                                          "file_code", "description")}}
            for iid in score.pop("flipped_items")
        ]
        return _emit(score)

    scores = [kingmaker_score(m, members, by_item) for m in members]
    scores.sort(key=lambda s: s["score"], reverse=True)
    return _emit([
        {"member": s["member"], "score": s["score"],
         "flipped_count": len(s["flipped_items"])}
        for s in scores
    ])


def cmd_contested(args) -> int:
    _, by_item, items_meta = load_votes(args.db)
    rows = controversial_items(by_item, items_meta, limit=args.limit or len(by_item))
    return _emit(rows)


def cmd_search(args) -> int:
    eng = engine_for(args.db)
    with eng.connect() as conn:
        rows = conn.execute(
            select(
                item_t.c.id, item_t.c.meeting_date, item_t.c.item_number,
                item_t.c.file_code, item_t.c.council_district,
                item_t.c.description, item_t.c.disposition,
            )
            .where(item_t.c.description.ilike(f"%{args.query}%"))
            .order_by(item_t.c.meeting_date.asc(), item_t.c.item_number.asc())
        ).all()
    if args.limit:
        rows = rows[:args.limit]
    return _emit([
        {"item_id": r[0], "meeting_date": r[1], "item_number": r[2],
         "file_code": r[3], "council_district": r[4],
         "description": r[5], "disposition": r[6]}
        for r in rows
    ])


def cmd_sql(args) -> int:
    stmt = args.stmt.strip().rstrip(";")
    lowered = stmt.lower().lstrip()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return _fail("only SELECT / WITH statements are allowed")
    # crude guard: reject semicolons (no multi-statement), DML/DDL keywords
    forbidden = (";", " insert ", " update ", " delete ", " drop ",
                 " alter ", " create ", " replace ", " attach ", " pragma ")
    for bad in forbidden:
        if bad in f" {lowered} ":
            return _fail(f"forbidden token in SQL: {bad.strip()!r}")

    eng = engine_for(args.db)
    with eng.connect() as conn:
        result = conn.execute(text(stmt))
        cols = list(result.keys())
        rows = [dict(zip(cols, r)) for r in result.fetchall()]
    if args.limit:
        rows = rows[:args.limit]
    return _emit({"columns": cols, "rows": rows, "row_count": len(rows)})


# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    common.add_argument("--limit", type=int, default=50,
                        help="cap list outputs (0 = no limit)")
    common.add_argument("--contested-only", action="store_true",
                        help="restrict pairwise stats to contested items")

    ap = argparse.ArgumentParser(
        description=__doc__, parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[common])

    add("members")
    add("meetings")

    p = add("items")
    p.add_argument("--date")
    p.add_argument("--cd", help="council district")
    p.add_argument("--search", help="substring match on description")
    p.add_argument("--contested", action="store_true")

    p = add("item"); p.add_argument("item_id", type=int)
    p = add("votes"); p.add_argument("member")
    p = add("member"); p.add_argument("member")

    p = add("agreement")
    p.add_argument("--pair", nargs=2, metavar=("A", "B"))

    add("dissent")

    p = add("lone-wolf"); p.add_argument("--member")
    p = add("pivotal"); p.add_argument("--member")

    add("contested")

    p = add("search"); p.add_argument("query")
    p = add("sql")
    p.add_argument("stmt", help="a single read-only SELECT or WITH statement")

    return ap


HANDLERS = {
    "members": cmd_members,
    "meetings": cmd_meetings,
    "items": cmd_items,
    "item": cmd_item,
    "votes": cmd_votes,
    "member": cmd_member,
    "agreement": cmd_agreement,
    "dissent": cmd_dissent,
    "lone-wolf": cmd_lone_wolf,
    "pivotal": cmd_pivotal,
    "contested": cmd_contested,
    "search": cmd_search,
    "sql": cmd_sql,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit == 0:
        args.limit = None
    return HANDLERS[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
