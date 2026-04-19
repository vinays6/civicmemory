from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DB_PATH = Path(os.getenv("CIVICMEMORY_SOURCE_DB", str(REPO_ROOT / "votes.sqlite")))
TRANSCRIPTS_DIR = Path(
    os.getenv("CIVICMEMORY_TRANSCRIPTS_DIR", str(REPO_ROOT / "civicmemdata" / "transcripts"))
)
CAMPAIGNFUNDS_DIR = Path(
    os.getenv(
        "CIVICMEMORY_CAMPAIGNFUNDS_DIR",
        str(REPO_ROOT / "campaignfunds" / "la_council_finance"),
    )
)

PAGE_NOISE_RE = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday)\s*-\s*[A-Za-z]+\s+\d{1,2},\s+\d{4}\s*-\s*PAGE\s+\d+",
    re.IGNORECASE,
)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "at",
    "be",
    "by",
    "city",
    "committee",
    "council",
    "district",
    "for",
    "from",
    "funding",
    "in",
    "into",
    "item",
    "items",
    "los",
    "of",
    "on",
    "or",
    "program",
    "programs",
    "project",
    "projects",
    "relative",
    "report",
    "resolution",
    "service",
    "services",
    "the",
    "to",
    "with",
}


def _connect_source_db() -> sqlite3.Connection:
    connection = sqlite3.connect(SOURCE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _load_transcript_from_files(meeting_date: str) -> tuple[str, str]:
    transcript_files = sorted(TRANSCRIPTS_DIR.glob(f"{meeting_date}_*.txt"))
    if not transcript_files:
        raise ValueError(f"No transcript found for meeting date '{meeting_date}' in {TRANSCRIPTS_DIR}.")

    chunks = [path.read_text(encoding="utf-8") for path in transcript_files]
    transcript_text = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
    if not transcript_text:
        raise ValueError(f"Transcript files for meeting date '{meeting_date}' are empty.")

    source_file = ";".join(path.name for path in transcript_files)
    return transcript_text, source_file


def _load_alias_map(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT alias, canonical FROM name_alias").fetchall()
    return {row["alias"]: row["canonical"] for row in rows}


def _canonicalize_names(raw_names: list[str], alias_map: dict[str, str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in raw_names:
        canonical_name = alias_map.get(raw_name, raw_name)
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        names.append(canonical_name)
    return names


def _load_councilmembers_for_date(connection: sqlite3.Connection, meeting_date: str) -> list[dict]:
    alias_map = _load_alias_map(connection)

    attendance_rows = connection.execute(
        """
        SELECT member
        FROM attendance
        WHERE meeting_date = ?
        ORDER BY member ASC
        """,
        (meeting_date,),
    ).fetchall()
    raw_names = [row["member"] for row in attendance_rows]

    if not raw_names:
        vote_rows = connection.execute(
            """
            SELECT DISTINCT vote.member AS member
            FROM vote
            INNER JOIN item ON item.id = vote.item_id
            WHERE item.meeting_date = ?
            ORDER BY vote.member ASC
            """,
            (meeting_date,),
        ).fetchall()
        raw_names = [row["member"] for row in vote_rows]

    if not raw_names:
        raise ValueError(f"No councilmembers found in source DB for meeting date '{meeting_date}'.")

    return [{"name": name} for name in _canonicalize_names(raw_names, alias_map)]


def get_meeting_analysis_input(meeting_date: str) -> tuple[dict, list[dict]]:
    transcript_text, _source_file = _load_transcript_from_files(meeting_date)
    with _connect_source_db() as connection:
        councilmembers = _load_councilmembers_for_date(connection, meeting_date)

    meeting = {
        "meeting_id": f"meeting_{meeting_date.replace('-', '_')}",
        "date": meeting_date,
        "transcript": transcript_text,
    }
    return meeting, councilmembers


def _normalize_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return normalized.encode("ascii", "ignore").decode("ascii")


def _normalize_member_key(text: str) -> str:
    ascii_text = _normalize_ascii(text).lower()
    return NON_ALNUM_RE.sub("", ascii_text)


def _tokenize(text: str) -> set[str]:
    ascii_text = _normalize_ascii(text).lower()
    tokens = set(TOKEN_RE.findall(ascii_text))
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def _clean_description(description: str | None, max_length: int = 180) -> str:
    if not description:
        return ""
    cleaned = PAGE_NOISE_RE.sub(" ", description)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    if len(cleaned) <= max_length:
        return cleaned
    truncated = cleaned[: max_length - 3].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."


def _select_top_employers(finance_summary: dict, limit: int = 5) -> list[dict]:
    employers = finance_summary.get("top_employers", [])
    informative = [
        employer
        for employer in employers
        if employer.get("employer_name") not in {"UNKNOWN", "SELF-EMPLOYED", "RETIRED"}
    ]
    chosen = informative[:limit] or employers[:limit]
    return [
        {
            "employer_name": employer.get("employer_name"),
            "total_amount": employer.get("total_amount", 0),
        }
        for employer in chosen
    ]


def _select_top_industries(finance_summary: dict, limit: int = 5) -> list[dict]:
    summary = finance_summary.get("industry_summary", {})
    rows = [
        {
            "industry": industry,
            "total_amount": details.get("total_amount", 0),
        }
        for industry, details in summary.items()
    ]
    rows.sort(key=lambda row: row["total_amount"], reverse=True)
    return rows[:limit]


def _build_member_keys(full_name: str, slug: str) -> set[str]:
    parts = [part for part in _normalize_ascii(full_name).lower().replace("-", " ").split() if part]
    keys = {_normalize_member_key(slug), _normalize_member_key(full_name)}
    if parts:
        keys.add(_normalize_member_key(parts[-1]))
    if len(parts) >= 2:
        keys.add(_normalize_member_key(" ".join(parts[-2:])))
    return {key for key in keys if key}


def _match_vote_member(raw_member: str, candidate_keys: dict[str, set[str]]) -> str | None:
    raw_key = _normalize_member_key(raw_member)
    if not raw_key:
        return None

    exact_matches = [name for name, keys in candidate_keys.items() if raw_key in keys]
    if len(exact_matches) == 1:
        return exact_matches[0]

    contains_matches = [name for name, keys in candidate_keys.items() if any(key and key in raw_key for key in keys)]
    if len(contains_matches) == 1:
        return contains_matches[0]

    return None


@lru_cache(maxsize=1)
def _load_campaign_profiles() -> list[dict]:
    files = sorted(CAMPAIGNFUNDS_DIR.glob("cd*_*.json"))
    if not files:
        raise ValueError(f"No campaign profile JSON files found in {CAMPAIGNFUNDS_DIR}.")

    profiles: list[dict] = []
    for path in files:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        slug = path.stem.split("_", 1)[1] if "_" in path.stem else path.stem
        finance_summary = payload.get("finance_summary", {})
        campaign_platform = payload.get("campaign_platform", {})
        profiles.append(
            {
                "district": payload["district"],
                "member_name": payload["name"],
                "member_slug": slug,
                "party_affiliation": payload.get("party_affiliation"),
                "office": payload.get("office"),
                "campaign_profile": {
                    "key_issues": campaign_platform.get("key_issues", [])[:5],
                    "campaign_promises": campaign_platform.get("campaign_promises", [])[:4],
                    "endorsements": campaign_platform.get("endorsements", [])[:4],
                    "source_note": campaign_platform.get("source_note"),
                },
                "finance_summary": {
                    "total_contributions_usd": finance_summary.get("total_contributions_usd", 0),
                    "total_contributors": finance_summary.get("total_contributors", 0),
                    "top_employers": _select_top_employers(finance_summary, limit=3),
                    "top_industries": _select_top_industries(finance_summary, limit=3),
                },
            }
        )
    return profiles


def _vote_similarity_score(issue_tokens: set[str], description: str) -> int:
    if not issue_tokens or not description:
        return 0
    description_tokens = _tokenize(description)
    return len(issue_tokens & description_tokens)


@lru_cache(maxsize=1)
def _load_vote_history() -> tuple[list[dict], dict[int, dict], dict[int, dict[str, str]], dict[str, list[tuple[int, str]]]]:
    profiles = _load_campaign_profiles()
    candidate_keys = {
        profile["member_name"]: _build_member_keys(profile["member_name"], profile["member_slug"])
        for profile in profiles
    }

    item_meta: dict[int, dict] = {}
    item_votes: dict[int, dict[str, str]] = defaultdict(dict)
    member_vote_refs: dict[str, list[tuple[int, str]]] = defaultdict(list)

    with _connect_source_db() as connection:
        rows = connection.execute(
            """
            SELECT item.id AS item_id,
                   item.meeting_date,
                   item.item_number,
                   item.file_code,
                   item.council_district,
                   item.description,
                   item.disposition,
                   vote.member,
                   vote.position
            FROM vote
            INNER JOIN item ON item.id = vote.item_id
            ORDER BY item.meeting_date DESC, item.item_number ASC
            """
        ).fetchall()

    for row in rows:
        member_name = _match_vote_member(row["member"], candidate_keys)
        if member_name is None:
            continue

        item_id = row["item_id"]
        item_meta[item_id] = {
            "meeting_date": row["meeting_date"],
            "item_number": row["item_number"],
            "file_code": row["file_code"],
            "council_district": row["council_district"],
            "description": _clean_description(row["description"]),
            "disposition": row["disposition"],
        }
        item_votes[item_id][member_name] = row["position"]
        member_vote_refs[member_name].append((item_id, row["position"]))

    return profiles, item_meta, dict(item_votes), dict(member_vote_refs)


def get_vote_prediction_input(issue_query: str) -> list[dict]:
    profiles, item_meta, item_votes, member_vote_refs = _load_vote_history()

    issue_tokens = _tokenize(issue_query)
    prediction_input: list[dict] = []

    for profile in profiles:
        member_name = profile["member_name"]
        votes = member_vote_refs.get(member_name, [])
        counts = {"aye": 0, "nay": 0, "absent": 0}
        relevant_examples: list[tuple[int, int, str, dict]] = []
        recent_nay_examples: list[dict] = []
        recent_contested_examples: list[dict] = []
        recent_nay_refs: set[str] = set()

        for item_id, position in votes:
            counts[position] = counts.get(position, 0) + 1
            meta = item_meta[item_id]
            all_positions = item_votes[item_id]
            ayes = sum(1 for vote_position in all_positions.values() if vote_position == "aye")
            nays = sum(1 for vote_position in all_positions.values() if vote_position == "nay")
            absences = sum(1 for vote_position in all_positions.values() if vote_position == "absent")
            reference = f"{meta['meeting_date']}#{meta['item_number']}"
            example = {
                "reference": reference,
                "position": position,
                "description": meta["description"],
                "tally": {"aye": ayes, "nay": nays, "absent": absences},
            }

            score = _vote_similarity_score(issue_tokens, meta["description"])
            if score > 0 and position in {"aye", "nay"}:
                position_rank = 0 if position == "nay" else 1 if position == "aye" else 2
                relevant_examples.append((score, position_rank, meta["meeting_date"], example))
            if position == "nay" and len(recent_nay_examples) < 2:
                recent_nay_examples.append(example)
                recent_nay_refs.add(reference)
            if (
                nays > 0
                and position in {"aye", "nay"}
                and reference not in recent_nay_refs
                and len(recent_contested_examples) < 2
            ):
                recent_contested_examples.append(example)

        relevant_examples.sort(key=lambda row: (-row[0], row[1], row[2]), reverse=False)
        top_relevant = [example for _, _, _, example in relevant_examples[:2]]

        total_votes = sum(counts.values())
        present_votes = counts["aye"] + counts["nay"]
        prediction_input.append(
            {
                "member_name": member_name,
                "district": profile["district"],
                "party_affiliation": profile["party_affiliation"],
                "office": profile["office"],
                "campaign_profile": profile["campaign_profile"],
                "finance_summary": profile["finance_summary"],
                "voting_record": {
                    "vote_counts": counts,
                    "total_recorded_items": total_votes,
                    "participation_rate": round((present_votes / total_votes), 3) if total_votes else 0.0,
                    "issue_relevant_votes": top_relevant,
                    "recent_nay_votes": recent_nay_examples,
                    "recent_contested_votes": recent_contested_examples,
                },
            }
        )

    if not prediction_input:
        raise ValueError("No vote history or campaign profiles are available for prediction.")

    return prediction_input
