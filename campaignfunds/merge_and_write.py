"""
Merge per-member finance JSONs (in la_council_finance/_finance/) with the
hand-curated platform data in platform_data.py, then write the final
cd{district}_{lastname}.json files directly into la_council_finance/.
"""
import json
from pathlib import Path

from platform_data import PLATFORMS

FINANCE_DIR = Path("la_council_finance/_finance")
OUT_DIR = Path("la_council_finance")

# Mapping of district → filename last-name slug (must match process_finance.py)
SLUGS = {
    1: "hernandez",
    2: "nazarian",
    3: "blumenfield",
    4: "raman",
    5: "yaroslavsky",
    6: "padilla",
    7: "rodriguez",
    8: "harris-dawson",
    9: "price",
    10: "hutt",
    11: "park",
    12: "lee",
    13: "soto-martinez",
    14: "jurado",
    15: "mcosker",
}


def main():
    written = 0
    for district, platform in sorted(PLATFORMS.items()):
        slug = SLUGS[district]
        fin_path = FINANCE_DIR / f"cd{district}_{slug}.json"
        if not fin_path.exists():
            print(f"  [WARN] missing finance file: {fin_path}")
            continue
        with open(fin_path) as f:
            finance = json.load(f)

        merged = {
            "district": district,
            "name": finance["name"],
            "party_affiliation": platform["party_affiliation"],
            "campaign_website_url": platform["campaign_website_url"],
            "office": finance["office"],
            "finance_summary": finance["finance_summary"],
            "campaign_platform": {
                "key_issues": platform["key_issues"],
                "campaign_promises": platform["campaign_promises"],
                "endorsements": platform["endorsements"],
                "source_note": platform["source_note"],
            },
            "all_contributions": finance["all_contributions"],
        }

        out_path = OUT_DIR / f"cd{district}_{slug}.json"
        with open(out_path, "w") as f:
            json.dump(merged, f, indent=2, default=str)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"  wrote {out_path}  ({size_mb:.2f} MB)")
        written += 1

    print(f"\nWrote {written} merged JSON files to {OUT_DIR}/")


if __name__ == "__main__":
    main()
