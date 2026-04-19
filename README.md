# civicmemory

claude builder club hackathon

Pipeline for extracting and analyzing LA City Council voting records from
Journal/Council Proceeding PDFs.

## Setup

```
pip install -r requirements.txt
```

Data is stored in `votes.sqlite` (SQLite — relational schema of
`meeting → item → vote`, plus `councilmember` and `attendance` tables).

## Scripts

### `extract_votes.py`

Parses a council proceeding PDF and writes each agenda item, its
description, and the Ayes/Nays/Absent tally to `votes.sqlite`.

```
python extract_votes.py sample_record.pdf [more.pdf ...]
```

### `extract_attendance.py`

Parses the opening roll-call block (`Members Present: ...; Absent: ...`)
and writes it to the `attendance` table. Distinct from per-item absences:
captures who was seated when the meeting was gaveled in.

```
python extract_attendance.py sample_record.pdf [more.pdf ...]
```

### `roster.py`

Normalizes councilmember names across PDFs. Folds cosmetic variants
(`Soto-Martinez` → `Soto-Martínez`, `Price Jr` → `Price Jr.`) by
fingerprinting on NFKD-normalized alphanumerics.

```
python roster.py build       # observe names, write roster.json, flag ambiguous clusters
python roster.py check       # list DB names not covered by current roster
python roster.py apply       # rewrite DB names to canonical form (idempotent)
```

Run `build` / `apply` after each ingestion batch. `roster.json` is
human-editable — commit it to git and review diffs before applying.

### `analyze_votes.py`

Analytics on the extracted data. Primary import surface for the profile
builder and frontend:

- `load_votes(db)` → `(members, by_item, items_meta)`
- `agreement_matrix(members, by_item, contested_only=False)`
- `codissent_matrix(members, by_item)`
- `asymmetric_agreement(members, by_item)`
- `precompute_matrices(members, by_item)`
- `member_stats(member, members, by_item, items_meta, matrices)`
- `kingmaker_score(member, members, by_item)`
- `controversial_items(by_item, items_meta, limit=10)`

CLI for development:

```
python analyze_votes.py matrix [--contested-only]       # pairwise agreement %
python analyze_votes.py factions [-k N] [--contested-only]  # hierarchical clustering
python analyze_votes.py bipartisan                      # items splitting usual blocs
python analyze_votes.py contested                       # all items with any Nay
python analyze_votes.py profile "Hernandez"             # JSON member profile
python analyze_votes.py kingmakers                      # who could flip outcomes
```

## Typical ingestion loop

```
python extract_votes.py new_meetings/*.pdf
python extract_attendance.py new_meetings/*.pdf
python roster.py check          # any unknown name variants?
python roster.py build          # refresh roster
# review roster.json diff, commit
python roster.py apply          # fold variants into canonical forms
python analyze_votes.py matrix  # sanity-check results
```
