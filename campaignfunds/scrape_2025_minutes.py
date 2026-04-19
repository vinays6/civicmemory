"""
Scrape 2025 LA City Council Journal/Actions (Minutes) PDFs.

Starts at the main RJL page (JS-rendered), but the tabs are links that
navigate to frame content hosted at ens2.lacity.org. The 2025 entries all
live in the "Journals(Minutes) Archives" year subfolder for 2025.
We also scan the current-year "Journals(Minutes)" tab in case any 2025
entries linger there.

Each PDF link on the listing has the form
    http://ens.lacity.org/clk/councilactions/clkcouncilactions{ID}_{MMDDYYYY}.pdf
The trailing date in the URL is the *posting* date, not the meeting date.
The meeting date is parsed from the link title
    "Journal/Actions - MM/DD/YY"       (2-digit year)
    "Journal/Actions - MM/DD/YYYY"     (4-digit year)
with optional suffixes " - Special", " Part N of M", " - N of M", etc.
"""
from __future__ import annotations

import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path("raw_minutes/2025")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROOT = "https://cityclerk.lacity.org/lacityclerkconnect/index.cfm?fa=c.search&tab=RJL"

# ---- regexes for parsing titles ----

# Core "MM/DD/YY" or "MM/DD/YYYY" meeting date in the title
DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")

# Part / section suffix — matches "Part 1 of 3", "1 of 3", "- 2 of 3", etc.
PART_RE = re.compile(
    r"(?:part\s*|-\s*)?(\d+)\s*of\s*(\d+)",
    re.IGNORECASE,
)

# Special marker
SPECIAL_RE = re.compile(r"\bspecial\b", re.IGNORECASE)


def parse_meeting_date(title: str) -> tuple[int, int, int] | None:
    """Return (year, month, day) parsed from title, or None."""
    m = DATE_RE.search(title)
    if not m:
        return None
    mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        # Convention: 2-digit year -> 2000 + yr (all council minutes are 21st century)
        yr = 2000 + yr
    return yr, mo, da


def slug_for(title: str) -> str | None:
    """Turn 'Journal/Actions - 04/15/25 Part 2 of 3' -> '2025-04-15_part2'."""
    parsed = parse_meeting_date(title)
    if not parsed:
        return None
    yr, mo, da = parsed
    base = f"{yr:04d}-{mo:02d}-{da:02d}"

    part_m = PART_RE.search(title)
    if part_m:
        base += f"_part{int(part_m.group(1))}"
    elif SPECIAL_RE.search(title):
        base += "_special"

    return base


def collect_links_on(page, year: int) -> list[dict]:
    """Pull (title, href) pairs for every anchor that looks like a PDF for `year`."""
    links = page.eval_on_selector_all(
        "a",
        "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
    )
    keep: list[dict] = []
    for ln in links:
        href = (ln.get("href") or "").strip()
        text = (ln.get("text") or "").strip()
        if "clkcouncilactions" not in href.lower() or not href.lower().endswith(".pdf"):
            continue
        parsed = parse_meeting_date(text)
        if not parsed:
            continue
        if parsed[0] != year:
            continue
        keep.append({"title": text, "href": href, "meeting": parsed})
    return keep


def download(url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 civicmemory-scraper"})
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if not data:
                raise RuntimeError("empty body")
            dest.write_bytes(data)
            return True
        except Exception as e:
            last_err = e
            time.sleep(1.5 * attempt)
    print(f"    ! failed {url}: {last_err}")
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        all_entries: list[dict] = []

        # 1) Go through the main page and extract the tab links (so we respect
        #    the user's "start at the main page + click tabs" intent)
        page.goto(ROOT, wait_until="networkidle")
        page.wait_for_timeout(1500)

        tab_links = page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
        )
        tabs: dict[str, str] = {}
        for ln in tab_links:
            t = (ln["text"] or "").strip()
            h = (ln["href"] or "").strip()
            if t == "Journals(Minutes)":
                tabs["current"] = h
            elif t == "Journals(Minutes) Archives":
                tabs["archives"] = h
        print(f"tab urls: {tabs}")

        # 2) Current-year tab — scan for any 2025 entries
        print(f"\n>> current tab: {tabs['current']}")
        page.goto(tabs["current"], wait_until="networkidle")
        page.wait_for_timeout(2500)
        cur_entries = collect_links_on(page, 2025)
        print(f"   found {len(cur_entries)} 2025 entries in current tab")
        all_entries.extend(cur_entries)

        # 3) Archives tab — find 2025 year subfolder, click into it
        print(f"\n>> archives tab: {tabs['archives']}")
        page.goto(tabs["archives"], wait_until="networkidle")
        page.wait_for_timeout(2500)

        archive_links = page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
        )
        year2025_url = None
        for ln in archive_links:
            if (ln["text"] or "").strip() == "Journal/Actions Archive 2025":
                year2025_url = ln["href"]
                break
        if not year2025_url:
            print("   [FATAL] could not find 'Journal/Actions Archive 2025' link")
            sys.exit(1)
        print(f"   2025 archive url: {year2025_url}")

        page.goto(year2025_url, wait_until="networkidle")
        page.wait_for_timeout(2500)
        arc_entries = collect_links_on(page, 2025)
        print(f"   found {len(arc_entries)} 2025 entries in archive")
        all_entries.extend(arc_entries)

        browser.close()

    # De-duplicate by (title, href)
    seen = set()
    unique: list[dict] = []
    for e in all_entries:
        key = (e["title"], e["href"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    print(f"\ntotal unique 2025 entries: {len(unique)}")

    # 4) Assign filenames, handling filename collisions
    assigned: dict[str, dict] = {}  # filename -> entry
    for e in unique:
        base = slug_for(e["title"])
        if not base:
            print(f"   [SKIP] cannot parse title: {e['title']!r}")
            continue
        fname = f"{base}.pdf"
        # Collision handling: same meeting date appears multiple times without
        # "part"/"special" suffix → add _v2, _v3, …
        if fname in assigned:
            for i in range(2, 20):
                cand = f"{base}_v{i}.pdf"
                if cand not in assigned:
                    fname = cand
                    break
        e["filename"] = fname
        assigned[fname] = e

    # 5) Download
    print(f"\ndownloading {len(assigned)} PDFs to {OUT_DIR}/ ...")
    ok = 0
    fail = 0
    for fname, e in sorted(assigned.items()):
        dest = OUT_DIR / fname
        if dest.exists() and dest.stat().st_size > 0:
            print(f"   skip (exists): {fname}")
            ok += 1
            continue
        url = e["href"]
        # Upgrade ens.lacity.org http -> https-safe via the original host
        print(f"   {fname}  <-  {e['title']!r}")
        if download(url, dest):
            ok += 1
        else:
            fail += 1

    print(f"\ndone: ok={ok}  fail={fail}")


if __name__ == "__main__":
    main()
