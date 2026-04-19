"""
Name normalization across a year+ of LA City Council meeting PDFs.

Workflow:

    # 1. Extract everything into votes.sqlite with raw names as they appear.
    python extract_votes.py *.pdf
    python extract_attendance.py *.pdf

    # 2. Build a roster from observed names. Clusters variants that differ
    #    only in accents, punctuation, whitespace, or hyphenation. Writes
    #    roster.json and a review report of any ambiguous clusters.
    python roster.py build

    # 3. (Optional) Hand-edit roster.json to correct any bad mappings.

    # 4. Apply the roster: rewrite every name in the DB to its canonical
    #    form. Safe to re-run; idempotent.
    python roster.py apply

    # 5. New extractions will continue to use raw names; re-run `apply`
    #    after each new batch of ingestion.

Fingerprint rule: NFKD-normalize → strip combining marks → lowercase →
keep only [a-z0-9]. Names with the same fingerprint are assumed to be
the same person. The canonical spelling is whichever raw form appears
most often in the data.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROSTER_PATH = Path("roster.json")


def fingerprint(name: str) -> str:
    """Collapse cosmetic variants to the same key.

    Examples:
        'Soto-Martínez' → 'sotomartinez'
        'Soto-Martinez' → 'sotomartinez'
        'Soto Martinez' → 'sotomartinez'
        'Price Jr.'     → 'pricejr'
        'price jr'      → 'pricejr'
    """
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return "".join(c for c in stripped.lower() if c.isalnum())


def collect_names(conn: sqlite3.Connection) -> Counter[str]:
    """Return a frequency count of every raw name seen anywhere in the DB."""
    counts: Counter[str] = Counter()
    for (name,) in conn.execute("SELECT member FROM vote"):
        counts[name] += 1
    # Attendance may not exist yet if extract_attendance hasn't run.
    try:
        for (name,) in conn.execute("SELECT member FROM attendance"):
            counts[name] += 1
    except sqlite3.OperationalError:
        pass
    for (name,) in conn.execute("SELECT name FROM councilmember"):
        counts[name] += 0  # ensure roster members with no votes still appear
    return counts


def build_roster(counts: Counter[str]) -> tuple[dict[str, list[str]], list[dict]]:
    """Cluster names by fingerprint and pick a canonical form per cluster.

    Returns:
        roster:  {canonical_name: [alias, alias, ...]} — aliases exclude the
                 canonical itself.
        review:  list of clusters worth a human look (e.g. multiple variants
                 with similar frequencies, very short fingerprints).
    """
    by_fp: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for name, n in counts.items():
        by_fp[fingerprint(name)].append((name, n))

    roster: dict[str, list[str]] = {}
    review: list[dict] = []

    for fp, variants in by_fp.items():
        if not fp:
            # Empty fingerprint means the name was pure punctuation — skip
            # and flag for review.
            review.append({"fingerprint": fp, "variants": variants,
                           "reason": "empty fingerprint"})
            continue
        # Canonical = most frequent spelling; tie-break on longer string
        # (tends to be the accented/punctuated form, which is what official
        # rosters use).
        variants_sorted = sorted(variants, key=lambda v: (-v[1], -len(v[0])))
        canonical = variants_sorted[0][0]
        aliases = [v for v, _ in variants_sorted[1:]]
        roster[canonical] = aliases

        if len(variants) > 1:
            total = sum(n for _, n in variants)
            top = variants_sorted[0][1]
            # Flag clusters where no variant dominates (>70% of occurrences)
            # — could indicate two distinct people collapsed together.
            if total > 0 and top / total < 0.7:
                review.append({
                    "fingerprint": fp,
                    "variants": variants_sorted,
                    "reason": "no dominant spelling",
                })
            # Flag very short fingerprints — more likely to collide.
            if len(fp) <= 3:
                review.append({
                    "fingerprint": fp,
                    "variants": variants_sorted,
                    "reason": "short fingerprint, possible collision",
                })

    return roster, review


def load_roster(path: Path) -> dict[str, str]:
    """Load roster.json and return a flat {any_name: canonical_name} map."""
    with open(path) as f:
        roster = json.load(f)
    flat: dict[str, str] = {}
    for canonical, aliases in roster.items():
        flat[canonical] = canonical
        for alias in aliases:
            if alias in flat and flat[alias] != canonical:
                raise ValueError(
                    f"alias {alias!r} maps to both {flat[alias]!r} "
                    f"and {canonical!r}"
                )
            flat[alias] = canonical
    return flat


def normalize(name: str, flat_roster: dict[str, str]) -> str:
    """Map a raw name to its canonical form. Unknown names pass through."""
    if name in flat_roster:
        return flat_roster[name]
    # Fall back to fingerprint match so names that weren't in the training
    # corpus still resolve if their fingerprint matches a known canonical.
    fp = fingerprint(name)
    for canonical in flat_roster.values():
        if fingerprint(canonical) == fp:
            return canonical
    return name


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_build(args: argparse.Namespace) -> int:
    with sqlite3.connect(args.db) as conn:
        counts = collect_names(conn)
    if not counts:
        print("No names found in DB. Run extract_votes.py first.", file=sys.stderr)
        return 1

    roster, review = build_roster(counts)
    with open(args.out, "w") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"Wrote {args.out}: {len(roster)} canonical members")
    total_aliases = sum(len(a) for a in roster.values())
    if total_aliases:
        print(f"  {total_aliases} alias(es) folded into canonical forms:")
        for canon, aliases in sorted(roster.items()):
            if aliases:
                print(f"    {canon}  ←  {', '.join(aliases)}")
    if review:
        print(f"\n{len(review)} cluster(s) flagged for review:")
        for r in review:
            print(f"  [{r['reason']}] {r['variants']}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    flat = load_roster(args.roster)
    with sqlite3.connect(args.db) as conn:
        changes = 0

        # 1. councilmember table: rewrite rows in place. Because (name) is
        #    the primary key we INSERT OR IGNORE the canonical then delete
        #    the alias row.
        for alias, canonical in flat.items():
            if alias == canonical:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO councilmember (name) VALUES (?)",
                (canonical,),
            )
            cur = conn.execute(
                "DELETE FROM councilmember WHERE name = ?", (alias,)
            )
            changes += cur.rowcount

        # 2. vote.member: update to canonical. Note that (item_id, member) is
        #    the PK — if a prior run already wrote a canonical row for the
        #    same item we'd collide, so use INSERT OR REPLACE semantics.
        for alias, canonical in flat.items():
            if alias == canonical:
                continue
            # Move any alias rows to canonical, replacing if a canonical row
            # already exists for the same item.
            conn.execute(
                """INSERT OR REPLACE INTO vote (item_id, member, position)
                   SELECT item_id, ?, position FROM vote WHERE member = ?""",
                (canonical, alias),
            )
            cur = conn.execute("DELETE FROM vote WHERE member = ?", (alias,))
            changes += cur.rowcount

        # 3. attendance table (if it exists).
        try:
            for alias, canonical in flat.items():
                if alias == canonical:
                    continue
                conn.execute(
                    """INSERT OR REPLACE INTO attendance
                       (meeting_date, member, status)
                       SELECT meeting_date, ?, status
                       FROM attendance WHERE member = ?""",
                    (canonical, alias),
                )
                cur = conn.execute(
                    "DELETE FROM attendance WHERE member = ?", (alias,)
                )
                changes += cur.rowcount
        except sqlite3.OperationalError:
            pass

        conn.commit()

    print(f"Applied roster: {changes} row(s) rewritten to canonical names")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Report any names in the DB that the roster does not recognize."""
    flat = load_roster(args.roster)
    with sqlite3.connect(args.db) as conn:
        counts = collect_names(conn)
    unknown = {n: c for n, c in counts.items() if n not in flat}
    if not unknown:
        print("All names in DB resolve to a canonical form.")
        return 0
    print(f"{len(unknown)} name(s) not covered by roster:")
    for name, c in sorted(unknown.items(), key=lambda kv: -kv[1]):
        suggestion = normalize(name, flat)
        hint = f" (fingerprint → {suggestion!r})" if suggestion != name else ""
        print(f"  {c:>4}×  {name}{hint}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build roster.json from observed names")
    b.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    b.add_argument("--out", type=Path, default=ROSTER_PATH)
    b.set_defaults(func=cmd_build)

    a = sub.add_parser("apply", help="rewrite DB names to canonical form")
    a.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    a.add_argument("--roster", type=Path, default=ROSTER_PATH)
    a.set_defaults(func=cmd_apply)

    c = sub.add_parser("check", help="list DB names not covered by roster")
    c.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    c.add_argument("--roster", type=Path, default=ROSTER_PATH)
    c.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
