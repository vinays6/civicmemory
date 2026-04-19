"""
Voting analytics on votes.sqlite.

Primary import surface (used by the profile builder and frontend):

    load_votes(db)                    -> (members, by_item, items_meta)
    agreement_matrix(members, by_item, contested_only=False)
    codissent_matrix(members, by_item)
    asymmetric_agreement(members, by_item)
    precompute_matrices(members, by_item)
    member_stats(member, members, by_item, items_meta, matrices)
    kingmaker_score(member, members, by_item)
    controversial_items(by_item, items_meta, limit=10)

Agreement between two members on an item is 1 if they voted the same
(aye/nay), 0 if opposite. Absences are excluded from that item's pair.

Secondary development interface — CLI:

    python analyze_votes.py matrix [--contested-only]
    python analyze_votes.py factions [-k N] [--contested-only]
    python analyze_votes.py bipartisan
    python analyze_votes.py contested
    python analyze_votes.py profile "Member Name"
    python analyze_votes.py kingmakers
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

MIN_OVERLAP: int = 5


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_votes(
    db: Path,
) -> tuple[list[str], dict[int, dict[str, str]], dict[int, dict[str, Any]]]:
    """Load (members, by_item, items_meta) from the SQLite DB.

    by_item:    {item_id: {member: 'aye' | 'nay' | 'absent'}}
    items_meta: {item_id: {meeting_date, item_number, file_code,
                           council_district, description, disposition}}
    """
    with sqlite3.connect(db) as conn:
        members = sorted(r[0] for r in conn.execute("SELECT name FROM councilmember"))
        by_item: dict[int, dict[str, str]] = defaultdict(dict)
        for item_id, member, pos in conn.execute(
            "SELECT item_id, member, position FROM vote"
        ):
            by_item[item_id][member] = pos
        items_meta: dict[int, dict[str, Any]] = {}
        for row in conn.execute(
            """SELECT id, meeting_date, item_number, file_code,
                      council_district, description, disposition
               FROM item"""
        ):
            items_meta[row[0]] = {
                "meeting_date": row[1],
                "item_number": row[2],
                "file_code": row[3],
                "council_district": row[4],
                "description": row[5],
                "disposition": row[6],
            }
    return members, dict(by_item), items_meta


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def _contested(by_item: dict[int, dict[str, str]]) -> dict[int, dict[str, str]]:
    return {
        iid: v for iid, v in by_item.items() if any(p == "nay" for p in v.values())
    }


def agreement_matrix(
    members: list[str],
    by_item: dict[int, dict[str, str]],
    contested_only: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (agreement_rate, co_participation_count). Ignores absences.

    Diagonal is left at 0 (no self-pair); consumers should ignore it.
    """
    n = len(members)
    idx = {m: i for i, m in enumerate(members)}
    agree = np.zeros((n, n))
    total = np.zeros((n, n))

    items = _contested(by_item).values() if contested_only else by_item.values()

    for votes in items:
        present = [(m, p) for m, p in votes.items() if p in ("aye", "nay")]
        for i, (m1, p1) in enumerate(present):
            a = idx[m1]
            for m2, p2 in present[i + 1:]:
                b = idx[m2]
                total[a, b] += 1
                total[b, a] += 1
                if p1 == p2:
                    agree[a, b] += 1
                    agree[b, a] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(total > 0, agree / total, np.nan)
    return rate, total


def codissent_matrix(
    members: list[str],
    by_item: dict[int, dict[str, str]],
) -> tuple[np.ndarray, np.ndarray]:
    """For each pair, rate at which both voted nay among items where
    at least one did (and both were present).

    Returns (codissent_rate, denominator_count). Diagonal is 0.
    """
    n = len(members)
    idx = {m: i for i, m in enumerate(members)}
    both_nay = np.zeros((n, n))
    denom = np.zeros((n, n))

    for votes in _contested(by_item).values():
        present = [(m, p) for m, p in votes.items() if p in ("aye", "nay")]
        for i, (m1, p1) in enumerate(present):
            a = idx[m1]
            for m2, p2 in present[i + 1:]:
                b = idx[m2]
                if p1 == "nay" or p2 == "nay":
                    denom[a, b] += 1
                    denom[b, a] += 1
                    if p1 == "nay" and p2 == "nay":
                        both_nay[a, b] += 1
                        both_nay[b, a] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(denom > 0, both_nay / denom, np.nan)
    return rate, denom


def asymmetric_agreement(
    members: list[str],
    by_item: dict[int, dict[str, str]],
) -> np.ndarray:
    """M[a, b] = P(b votes same as a | a votes nay and b is present).

    Not symmetric. Diagonal is NaN.
    """
    n = len(members)
    idx = {m: i for i, m in enumerate(members)}
    num = np.zeros((n, n))
    denom = np.zeros((n, n))

    for votes in by_item.values():
        for m1, p1 in votes.items():
            if p1 != "nay":
                continue
            a = idx[m1]
            for m2, p2 in votes.items():
                if m2 == m1 or p2 not in ("aye", "nay"):
                    continue
                b = idx[m2]
                denom[a, b] += 1
                if p2 == p1:
                    num[a, b] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(denom > 0, num / denom, np.nan)
    np.fill_diagonal(out, np.nan)
    return out


def precompute_matrices(
    members: list[str],
    by_item: dict[int, dict[str, str]],
) -> dict[str, np.ndarray]:
    """Precompute the matrices needed by member_stats and CLI commands."""
    rate_full, total_full = agreement_matrix(members, by_item, contested_only=False)
    rate_c, total_c = agreement_matrix(members, by_item, contested_only=True)
    cod_rate, cod_n = codissent_matrix(members, by_item)
    return {
        "agreement": rate_full,
        "agreement_total": total_full,
        "agreement_contested": rate_c,
        "agreement_contested_total": total_c,
        "codissent": cod_rate,
        "codissent_total": cod_n,
    }


# ---------------------------------------------------------------------------
# Clustering helper
# ---------------------------------------------------------------------------

def _check_overlap(members: list[str], total: np.ndarray) -> None:
    """Raise if any off-diagonal pair has fewer than MIN_OVERLAP items."""
    n = len(members)
    offenders: list[tuple[str, str, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if total[i, j] < MIN_OVERLAP:
                offenders.append((members[i], members[j], int(total[i, j])))
    if offenders:
        lines = ", ".join(f"{a}/{b}={c}" for a, b, c in offenders[:10])
        more = f" (+{len(offenders) - 10} more)" if len(offenders) > 10 else ""
        raise ValueError(
            f"{len(offenders)} pair(s) have co-participation < MIN_OVERLAP"
            f"={MIN_OVERLAP}: {lines}{more}"
        )


def _cluster(
    members: list[str],
    rate: np.ndarray,
    total: np.ndarray,
    k: int,
) -> dict[str, int]:
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    _check_overlap(members, total)
    dist = 1 - rate
    np.fill_diagonal(dist, 0)
    Z = linkage(squareform(dist, checks=False), method="average")
    labels = fcluster(Z, t=k, criterion="maxclust")
    return {m: int(lab) for m, lab in zip(members, labels)}


# ---------------------------------------------------------------------------
# Per-member analytics
# ---------------------------------------------------------------------------

def _majority(votes: dict[str, str]) -> str | None:
    """Returns 'aye', 'nay', or None (tie / no votes)."""
    ayes = sum(1 for p in votes.values() if p == "aye")
    nays = sum(1 for p in votes.values() if p == "nay")
    if ayes > nays:
        return "aye"
    if nays > ayes:
        return "nay"
    return None


def member_stats(
    member: str,
    members: list[str],
    by_item: dict[int, dict[str, str]],
    items_meta: dict[int, dict[str, Any]],
    matrices: dict[str, np.ndarray],
) -> dict[str, Any]:
    if member not in members:
        raise ValueError(f"Unknown member: {member!r}")
    idx = {m: i for i, m in enumerate(members)}
    mi = idx[member]

    counts = {"aye": 0, "nay": 0, "absent": 0}
    losing = 0
    present_in_decided = 0
    lone_wolf: list[int] = []

    for item_id, votes in by_item.items():
        pos = votes.get(member)
        if pos in counts:
            counts[pos] += 1
        if pos in ("aye", "nay"):
            majority = _majority(votes)
            if majority is not None:
                present_in_decided += 1
                if pos != majority:
                    losing += 1
            # Lone wolf: the only aye or the only nay among present.
            same_side = [m for m, p in votes.items() if p == pos]
            if len(same_side) == 1:
                other_side = sum(
                    1 for p in votes.values() if p in ("aye", "nay") and p != pos
                )
                if other_side > 0:
                    lone_wolf.append(item_id)

    present = counts["aye"] + counts["nay"]
    total_items = len(by_item)
    aye_rate = counts["aye"] / present if present else 0.0
    participation_rate = present / total_items if total_items else 0.0
    dissent_rate = losing / present_in_decided if present_in_decided else 0.0

    cod_rate = matrices["codissent"]
    cod_n = matrices["codissent_total"]
    partners: list[dict[str, Any]] = []
    for j, other in enumerate(members):
        if j == mi:
            continue
        n = int(cod_n[mi, j])
        if n < MIN_OVERLAP:
            continue
        r = float(cod_rate[mi, j])
        if np.isnan(r):
            continue
        partners.append({"member": other, "rate": r, "n": n})
    partners.sort(key=lambda p: p["rate"], reverse=True)
    top_partners = partners[:3]

    align_c = matrices["agreement_contested"]
    alignment_row: dict[str, float | None] = {}
    for j, other in enumerate(members):
        if j == mi:
            continue
        v = align_c[mi, j]
        alignment_row[other] = None if np.isnan(v) else float(v)

    return {
        "member": member,
        "vote_counts": counts,
        "aye_rate": aye_rate,
        "participation_rate": participation_rate,
        "dissent_rate": dissent_rate,
        "lone_wolf_items": lone_wolf,
        "top_codissent_partners": top_partners,
        "alignment_row_contested": alignment_row,
    }


def kingmaker_score(
    member: str,
    members: list[str],
    by_item: dict[int, dict[str, str]],
) -> dict[str, Any]:
    if member not in members:
        raise ValueError(f"Unknown member: {member!r}")
    flipped: list[int] = []
    for item_id, votes in by_item.items():
        pos = votes.get(member)
        if pos not in ("aye", "nay"):
            continue
        ayes = sum(1 for p in votes.values() if p == "aye")
        nays = sum(1 for p in votes.values() if p == "nay")
        if nays == 0:  # uncontested
            continue
        if pos == "aye":
            new_ayes, new_nays = ayes - 1, nays
        else:
            new_ayes, new_nays = ayes, nays - 1

        def outcome(a: int, n: int) -> str:
            if a > n:
                return "aye"
            if n > a:
                return "nay"
            return "tie"

        if outcome(ayes, nays) != outcome(new_ayes, new_nays):
            flipped.append(item_id)
    return {"member": member, "flipped_items": flipped, "score": len(flipped)}


def controversial_items(
    by_item: dict[int, dict[str, str]],
    items_meta: dict[int, dict[str, Any]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item_id, votes in by_item.items():
        ayes = sum(1 for p in votes.values() if p == "aye")
        nays = sum(1 for p in votes.values() if p == "nay")
        absent = sum(1 for p in votes.values() if p == "absent")
        if ayes + nays == 0:
            continue
        meta = items_meta.get(item_id, {})
        rows.append({
            "item_id": item_id,
            "meeting_date": meta.get("meeting_date"),
            "item_number": meta.get("item_number"),
            "file_code": meta.get("file_code"),
            "description": meta.get("description"),
            "tally": {"aye": ayes, "nay": nays, "absent": absent},
            "_margin": abs(ayes - nays),
        })
    rows.sort(key=lambda r: (r["_margin"], _neg_date(r["meeting_date"])))
    for r in rows:
        r.pop("_margin", None)
    return rows[:limit]


def _neg_date(d: str | None) -> str:
    """Sort key that orders newer dates first when used ascending."""
    if not d:
        return ""
    # ISO dates sort lexicographically; invert by subtracting from a sentinel.
    return "".join(chr(255 - ord(c)) if c.isdigit() else c for c in d)


# ---------------------------------------------------------------------------
# CLI handlers
# ---------------------------------------------------------------------------

def cmd_matrix(members, by_item, items_meta, matrices, args) -> None:
    key = "agreement_contested" if args.contested_only else "agreement"
    total_key = "agreement_contested_total" if args.contested_only else "agreement_total"
    rate = matrices[key]
    total = matrices[total_key]
    w = max(len(m) for m in members)
    header = " " * (w + 2) + "  ".join(f"{m[:6]:>6}" for m in members)
    print(header)
    for i, m in enumerate(members):
        row = "  ".join(
            "  n/a " if np.isnan(rate[i, j]) else f"{rate[i, j] * 100:5.1f}"
            for j in range(len(members))
        )
        print(f"{m:<{w}}  {row}")
    nonzero = total[total > 0]
    if nonzero.size:
        print(f"\nMin co-participation: {int(nonzero.min())} items")


def cmd_factions(members, by_item, items_meta, matrices, args) -> None:
    key = "agreement_contested" if args.contested_only else "agreement"
    total_key = "agreement_contested_total" if args.contested_only else "agreement_total"
    bloc = _cluster(members, matrices[key], matrices[total_key], args.k)
    groups: dict[int, list[str]] = defaultdict(list)
    for m, lab in bloc.items():
        groups[lab].append(m)
    for lab, ms in sorted(groups.items()):
        print(f"Bloc {lab}: {', '.join(ms)}")


def cmd_contested(members, by_item, items_meta, matrices, args) -> None:
    contested = _contested(by_item)
    if not contested:
        print("No contested items (all unanimous in this dataset).")
        return
    for item_id in sorted(
        contested,
        key=lambda i: (items_meta[i]["meeting_date"], items_meta[i]["item_number"]),
    ):
        meta = items_meta[item_id]
        nays = sorted(m for m, p in by_item[item_id].items() if p == "nay")
        desc = (meta.get("description") or "")[:90]
        print(f"{meta['meeting_date']} #{meta['item_number']} {meta['file_code']}: "
              f"Nays={', '.join(nays)}")
        print(f"    {desc}")


def cmd_bipartisan(members, by_item, items_meta, matrices, args) -> None:
    bloc = _cluster(members, matrices["agreement"], matrices["agreement_total"], 2)
    for item_id, votes in by_item.items():
        nays = sorted(m for m, p in votes.items() if p == "nay")
        if not nays:
            continue
        nay_blocs = {bloc[m] for m in nays if m in bloc}
        if len(nay_blocs) > 1:
            meta = items_meta[item_id]
            desc = (meta.get("description") or "")[:90]
            print(f"{meta['meeting_date']} #{meta['item_number']} {meta['file_code']}: "
                  f"Nays={nays} (blocs={sorted(nay_blocs)})")
            print(f"    {desc}")


def cmd_profile(members, by_item, items_meta, matrices, args) -> None:
    stats = member_stats(args.member, members, by_item, items_meta, matrices)
    print(json.dumps(stats, indent=2, default=str))


def cmd_kingmakers(members, by_item, items_meta, matrices, args) -> None:
    scores = [kingmaker_score(m, members, by_item) for m in members]
    scores.sort(key=lambda s: s["score"], reverse=True)
    for s in scores:
        print(f"{s['score']:>3}  {s['member']}  {s['flipped_items']}")


CMDS = {
    "matrix": cmd_matrix,
    "factions": cmd_factions,
    "bipartisan": cmd_bipartisan,
    "contested": cmd_contested,
    "profile": cmd_profile,
    "kingmakers": cmd_kingmakers,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=CMDS)
    ap.add_argument("member", nargs="?", help="member name (for 'profile')")
    ap.add_argument("--db", type=Path, default=Path("votes.sqlite"))
    ap.add_argument("-k", type=int, default=2, help="number of blocs for 'factions'")
    ap.add_argument("--contested-only", action="store_true",
                    help="restrict matrix/factions to contested items")
    args = ap.parse_args()

    if args.cmd == "profile" and not args.member:
        ap.error("profile requires a member name")

    members, by_item, items_meta = load_votes(args.db)
    matrices = precompute_matrices(members, by_item)
    CMDS[args.cmd](members, by_item, items_meta, matrices, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
