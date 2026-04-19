"""
Name normalization for civicmemory.

Non-destructive model: raw names in vote/attendance are NEVER rewritten.
`roster.py apply` loads roster.json into the name_alias table; queries in
analyze_votes.py then join through it at read time.

    python roster.py build     # observe raw names, write roster.json
    python roster.py check     # list DB names not covered by current roster
    python roster.py apply     # sync name_alias from roster.json (idempotent)
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import delete, insert, select

from db import DEFAULT_DB_PATH, engine_for, name_alias as alias_t, all_raw_names

ROSTER_PATH = Path("roster.json")


def fingerprint(name: str) -> str:
    """Collapse cosmetic variants to the same key:
        'Soto-Martínez' / 'Soto-Martinez' / 'Soto Martinez' → 'sotomartinez'
        'Price Jr.' / 'price jr'                           → 'pricejr'
    """
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return "".join(c for c in stripped.lower() if c.isalnum())


def build_roster(counts: Counter[str]) -> tuple[dict[str, list[str]], list[dict]]:
    """Cluster by fingerprint, choose canonical = most-frequent spelling
    (tie-break: longer string, which favors accented/punctuated forms)."""
    by_fp: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for name, n in counts.items():
        by_fp[fingerprint(name)].append((name, n))

    roster: dict[str, list[str]] = {}
    review: list[dict] = []

    for fp, variants in by_fp.items():
        if not fp:
            review.append({"fingerprint": fp, "variants": variants,
                           "reason": "empty fingerprint"})
            continue
        variants_sorted = sorted(variants, key=lambda v: (-v[1], -len(v[0])))
        canonical = variants_sorted[0][0]
        aliases = [v for v, _ in variants_sorted[1:]]
        roster[canonical] = aliases

        if len(variants) > 1:
            total = sum(n for _, n in variants)
            top = variants_sorted[0][1]
            if total > 0 and top / total < 0.7:
                review.append({"fingerprint": fp, "variants": variants_sorted,
                               "reason": "no dominant spelling"})
            if len(fp) <= 3:
                review.append({"fingerprint": fp, "variants": variants_sorted,
                               "reason": "short fingerprint, possible collision"})

    return roster, review


def load_roster(path: Path) -> dict[str, str]:
    """Flat {alias: canonical} map, canonical maps to itself for convenience."""
    with open(path) as f:
        roster = json.load(f)
    flat: dict[str, str] = {}
    for canonical, aliases in roster.items():
        flat[canonical] = canonical
        for a in aliases:
            if a in flat and flat[a] != canonical:
                raise ValueError(
                    f"alias {a!r} maps to both {flat[a]!r} and {canonical!r}"
                )
            flat[a] = canonical
    return flat


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_build(args: argparse.Namespace) -> int:
    eng = engine_for(args.db)
    with eng.connect() as conn:
        counts = Counter(dict(all_raw_names(conn)))
    if not counts:
        print("No names in DB. Run extract_votes.py first.", file=sys.stderr)
        return 1

    roster, review = build_roster(counts)
    with open(args.out, "w") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"Wrote {args.out}: {len(roster)} canonical members")
    total_aliases = sum(len(a) for a in roster.values())
    if total_aliases:
        print(f"  {total_aliases} alias(es) folded:")
        for canon, aliases in sorted(roster.items()):
            if aliases:
                print(f"    {canon}  ←  {', '.join(aliases)}")
    if review:
        print(f"\n{len(review)} cluster(s) flagged for review:")
        for r in review:
            print(f"  [{r['reason']}] {r['variants']}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Sync roster.json into the name_alias table. Replaces entire table —
    roster.json is the source of truth."""
    flat = load_roster(args.roster)
    eng = engine_for(args.db)
    # Store only non-self-mappings: (alias != canonical).
    rows = [{"alias": a, "canonical": c} for a, c in flat.items() if a != c]
    with eng.begin() as conn:
        conn.execute(delete(alias_t))
        if rows:
            conn.execute(insert(alias_t), rows)
    print(f"Synced name_alias table: {len(rows)} alias mapping(s)")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    flat = load_roster(args.roster)
    eng = engine_for(args.db)
    with eng.connect() as conn:
        counts = dict(all_raw_names(conn))
    unknown = {n: c for n, c in counts.items() if n not in flat}
    if not unknown:
        print("All names in DB resolve to a canonical form.")
        return 0
    print(f"{len(unknown)} name(s) not covered by roster:")
    for name, c in sorted(unknown.items(), key=lambda kv: -kv[1]):
        fp = fingerprint(name)
        hit = next((canon for canon in flat.values() if fingerprint(canon) == fp), None)
        hint = f"  (fingerprint → {hit!r})" if hit and hit != name else ""
        print(f"  {c:>4}×  {name}{hint}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build roster.json from observed names")
    b.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    b.add_argument("--out", type=Path, default=ROSTER_PATH)
    b.set_defaults(func=cmd_build)

    a = sub.add_parser("apply", help="sync roster.json into name_alias table")
    a.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    a.add_argument("--roster", type=Path, default=ROSTER_PATH)
    a.set_defaults(func=cmd_apply)

    c = sub.add_parser("check", help="list DB names not covered by roster")
    c.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    c.add_argument("--roster", type=Path, default=ROSTER_PATH)
    c.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
