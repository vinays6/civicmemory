"""
Process LA City Council campaign contribution CSV into per-member finance JSON.

Computes 8 required stats per council member and writes intermediate
finance-only JSON files to la_council_finance/_finance/ for later merging
with platform data scraped from campaign websites.
"""
import json
import os
import re
from pathlib import Path
import pandas as pd

CSV_PATH = "City_Campaign_Contributions_(and_Misc_Increases_to_Cash)_20260419.csv"
OUT_DIR = Path("la_council_finance")
FINANCE_DIR = OUT_DIR / "_finance"
FINANCE_DIR.mkdir(parents=True, exist_ok=True)

# (district, name, last_name_lower_for_filename)
MEMBERS = [
    (1,  "Eunisses Hernandez",      "hernandez"),
    (2,  "Adrin Nazarian",          "nazarian"),
    (3,  "Bob Blumenfield",         "blumenfield"),
    (4,  "Nithya Raman",            "raman"),
    (5,  "Katy Yaroslavsky",        "yaroslavsky"),
    (6,  "Imelda Padilla",          "padilla"),
    (7,  "Monica Rodriguez",        "rodriguez"),
    (8,  "Marqueece Harris-Dawson", "harris-dawson"),
    (9,  "Curren D. Price Jr.",     "price"),
    (10, "Heather Hutt",            "hutt"),
    (11, "Traci Park",              "park"),
    (12, "John Lee",                "lee"),
    (13, "Hugo Soto-Martinez",      "soto-martinez"),
    (14, "Ysabel Jurado",           "jurado"),
    (15, "Tim McOsker",             "mcosker"),
]

# ---- industry mapping (substring match on normalized employer, first match wins) ----
INDUSTRY_KEYWORDS = [
    ("Real Estate", [
        "REAL ESTATE", "REALTY", "REALTOR", "PROPERTIES", "PROPERTY", "DEVELOPMENT",
        "DEVELOPER", "CONSTRUCTION", "BUILDER", "HOMES", "HOUSING", "CBRE", "KW ",
        "KELLER WILLIAMS", "COMPASS", "CIM GROUP", "RELATED COMPANIES",
    ]),
    ("Labor Unions", [
        "UNION", "LOCAL ", "SEIU", "AFSCME", "UFCW", "IBEW", "TEAMSTERS",
        "LABORERS", "CARPENTERS", "UNITE HERE", "AFL-CIO", "UFT", "UTLA",
        "NURSES ASSOCIATION", "FIREFIGHTERS", "POLICE PROTECTIVE",
        "BUILDING TRADES", "IATSE", "WGA", "SAG-AFTRA",
    ]),
    ("Entertainment", [
        "NETFLIX", "DISNEY", "WARNER", "PARAMOUNT", "UNIVERSAL", "SONY PICTURES",
        "NBCUNIVERSAL", "HBO", "MGM", "LIONSGATE", "AMAZON STUDIOS", "FOX ",
        "STUDIOS", "ENTERTAINMENT", "PRODUCTIONS", "TALENT AGENCY", "CAA",
        "WME", "UTA", "ICM", "PARADIGM", "WILLIAM MORRIS", "RECORDS",
        "MEDIA",
    ]),
    ("Tech", [
        "GOOGLE", "META", "FACEBOOK", "APPLE", "MICROSOFT", "AMAZON", "NETFLIX",
        "UBER", "LYFT", "AIRBNB", "SNAP", "SNAPCHAT", "TESLA", "SPACEX",
        "TECHNOLOG", "SOFTWARE", "SYSTEMS", "ENGINEER", "TECH ", ".COM",
    ]),
    ("Legal/Law Firms", [
        "LAW ", "LAWYER", "ATTORN", "LEGAL", "LLP", "LAW OFFICE", "LAW FIRM",
        "LATHAM", "GIBSON DUNN", "MUNGER", "O'MELVENY", "SHEPPARD MULLIN",
        "GREENBERG TRAURIG", "MANATT", "LOEB", "KIRKLAND", "PAUL HASTINGS",
        "SKADDEN",
    ]),
    ("Healthcare", [
        "HOSPITAL", "MEDICAL", "HEALTH", "PHYSICIAN", "DOCTOR", "DENTIST",
        "KAISER", "CEDARS", "UCLA HEALTH", "USC KECK", "CLINIC", "PHARMA",
        "BIOTECH",
    ]),
    ("Finance", [
        "BANK", "CAPITAL", "INVESTMENT", "FINANCIAL", "WEALTH", "EQUITY",
        "VENTURES", "FUND ", "ASSET", "HOLDING", "ADVISORS", "GOLDMAN",
        "MORGAN", "CITI", "WELLS FARGO", "BLACKROCK", "INSURANCE",
    ]),
    ("Retail/Hospitality", [
        "RESTAURANT", "HOTEL", "RETAIL", "HOSPITALITY", "FOODS", "MARKET",
        "CAFE", "BAR ", "DINING", "STORE", "SHOP", "APPAREL",
    ]),
    ("Government/Public Sector", [
        "CITY OF", "COUNTY OF", "STATE OF", "GOVERNMENT", "COUNCIL",
        "DEPARTMENT", "LAUSD", "METRO", "DWP", "PUBLIC WORKS", "HOUSING AUTHORITY",
        "UNITED STATES",
    ]),
    ("Education", [
        "UNIVERSITY", "COLLEGE", "SCHOOL", "EDUCATION", "ACADEMY", "UCLA",
        "USC", "CAL STATE", "CSU ", "TEACHER", "PROFESSOR",
    ]),
]


def normalize_employer(e: str) -> str:
    if e is None or (isinstance(e, float) and pd.isna(e)):
        return "UNKNOWN"
    s = str(e).strip().upper()
    s = re.sub(r"\s+", " ", s)
    if s in {"", "N/A", "NA", "NONE", "NOT EMPLOYED", "NOT APPLICABLE"}:
        return "UNKNOWN"
    if s in {"SELF", "SELF-EMPLOYED", "SELF EMPLOYED", "SELFEMPLOYED"}:
        return "SELF-EMPLOYED"
    if s in {"RETIRED"}:
        return "RETIRED"
    return s


def classify_industry(employer_norm: str) -> str:
    if employer_norm in {"UNKNOWN", "SELF-EMPLOYED", "RETIRED"}:
        return "Unknown"
    for industry, kws in INDUSTRY_KEYWORDS:
        for kw in kws:
            if kw in employer_norm:
                return industry
    return "Unknown"


def parse_amount(v) -> float:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    s = str(v).replace("$", "").replace(",", "").strip()
    if s in {"", "-"}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def main():
    print(f"Loading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"  total rows: {len(df):,}")

    # Filter out Schedule I (misc. increases to cash)
    df = df[df["Schedule"] != "I"].copy()
    print(f"  after dropping Schedule I: {len(df):,}")

    # Parse amount
    df["amount"] = df["Contribution Amount"].map(parse_amount)
    df["employer_norm"] = df["Contrib Employer"].map(normalize_employer)
    df["industry"] = df["employer_norm"].map(classify_industry)

    index_rows = []

    for district, full_name, last_key in MEMBERS:
        office = f"City Council Member - District {district}"
        sub = df[df["Office"] == office].copy()
        if sub.empty:
            print(f"  [WARN] no rows for D{district} {full_name}")
            continue

        total_amt = round(sub["amount"].sum(), 2)
        total_contributors = int(sub["Contributor"].dropna().nunique())

        # Top employers (excluding UNKNOWN / SELF / RETIRED? — include them per spec
        # but group them properly by normalized name)
        emp_grp = (
            sub.groupby("employer_norm")
            .agg(total_amount=("amount", "sum"), num_contributions=("amount", "count"))
            .reset_index()
            .sort_values("total_amount", ascending=False)
            .head(20)
        )
        top_employers = [
            {
                "employer_name": r["employer_norm"],
                "total_amount": round(float(r["total_amount"]), 2),
                "num_contributions": int(r["num_contributions"]),
            }
            for _, r in emp_grp.iterrows()
        ]

        # Top contributors (individuals)
        def first_nonnull(s):
            s = s.dropna()
            return s.iloc[0] if len(s) else None

        con_grp = (
            sub.groupby("Contributor")
            .agg(
                total_amount=("amount", "sum"),
                num_contributions=("amount", "count"),
                employer=("employer_norm", first_nonnull),
                occupation=("Contrib Occupation", first_nonnull),
            )
            .reset_index()
            .sort_values("total_amount", ascending=False)
            .head(20)
        )
        top_contributors = [
            {
                "name": r["Contributor"],
                "employer": r["employer"] if r["employer"] is not None else None,
                "occupation": r["occupation"] if r["occupation"] is not None else None,
                "total_amount": round(float(r["total_amount"]), 2),
                "num_contributions": int(r["num_contributions"]),
            }
            for _, r in con_grp.iterrows()
        ]

        # By type
        type_grp = (
            sub.groupby("Contribution Type")
            .agg(total_amount=("amount", "sum"), count=("amount", "count"))
            .reset_index()
        )
        contributions_by_type = {
            r["Contribution Type"]: {
                "total_amount": round(float(r["total_amount"]), 2),
                "count": int(r["count"]),
            }
            for _, r in type_grp.iterrows()
        }

        # Geo breakdown (top 10 cities)
        city_grp = (
            sub.groupby("Contributor City")
            .agg(total_amount=("amount", "sum"), num_contributions=("amount", "count"))
            .reset_index()
            .sort_values("total_amount", ascending=False)
            .head(10)
        )
        geographic_breakdown = [
            {
                "city": r["Contributor City"],
                "total_amount": round(float(r["total_amount"]), 2),
                "num_contributions": int(r["num_contributions"]),
            }
            for _, r in city_grp.iterrows()
        ]

        # Industry summary
        ind_grp = (
            sub.groupby("industry")
            .agg(total_amount=("amount", "sum"), num_contributions=("amount", "count"))
            .reset_index()
            .sort_values("total_amount", ascending=False)
        )
        industry_summary = {
            r["industry"]: {
                "total_amount": round(float(r["total_amount"]), 2),
                "num_contributions": int(r["num_contributions"]),
            }
            for _, r in ind_grp.iterrows()
        }

        # all_contributions — full row list with the user's requested canonical names
        cols_map = {
            "Contribution Date": "con_date",
            "Contributor": "con_name",
            "Contributor City": "con_city_nm",
            "Contributor State": "con_state_nm",
            "Contributor Zip": "con_zip_cd",
            "Contrib Occupation": "con_occp",
            "Contrib Employer": "con_empr",
            "Committee Name": "cmt_nm",
            "Candidate/Officeholder": "cand_name",
            "Office": "seat_desc",
            "District": "dist_num",
            "Contribution Type": "con_type",
            "Contribution Amount": "con_amount_raw",
            "Intermediary Name": "int_name",
            "Intermediary Employer": "int_empr",
            "Schedule": "schedule",
        }
        keep = sub[list(cols_map.keys())].rename(columns=cols_map).copy()
        keep["con_amount"] = sub["amount"].round(2).values
        # clean NaN -> None for JSON
        all_contributions = json.loads(
            keep.where(pd.notna(keep), None).to_json(orient="records")
        )
        # force con_amount as float
        for row in all_contributions:
            if row.get("con_amount") is not None:
                row["con_amount"] = round(float(row["con_amount"]), 2)

        finance = {
            "district": district,
            "name": full_name,
            "office": f"Los Angeles City Council, District {district}",
            "finance_summary": {
                "total_contributions_usd": total_amt,
                "total_contributors": total_contributors,
                "top_employers": top_employers,
                "top_contributors": top_contributors,
                "contributions_by_type": contributions_by_type,
                "geographic_breakdown": geographic_breakdown,
                "industry_summary": industry_summary,
            },
            "all_contributions": all_contributions,
        }

        out_path = FINANCE_DIR / f"cd{district}_{last_key}.json"
        with open(out_path, "w") as f:
            json.dump(finance, f, indent=2, default=str)

        top3 = ", ".join(
            f"{e['employer_name']} (${e['total_amount']:,.0f})"
            for e in top_employers[:3]
        )
        print(
            f"  D{district:<2} {full_name:<25} "
            f"total=${total_amt:>13,.2f}  "
            f"rows={len(sub):>5}  "
            f"top3: {top3}"
        )

        index_rows.append(
            {
                "district": district,
                "name": full_name,
                "total_contributions_usd": total_amt,
                "total_rows": len(sub),
            }
        )

    with open(FINANCE_DIR / "_index.json", "w") as f:
        json.dump(index_rows, f, indent=2)

    print(f"\nWrote {len(index_rows)} finance files to {FINANCE_DIR}/")


if __name__ == "__main__":
    main()
