"""
Exploration v3: navigate directly to the tab URLs and find 2025 PDF links.
"""
from playwright.sync_api import sync_playwright

TABS = {
    "current": "https://ens2.lacity.org/enssubscribe2/netdocs/index.cfm?catid=2&SI&SP&DS=2&DD=2&CSS=77113&rootcat=2",
    "archives": "https://ens2.lacity.org/enssubscribe2/netdocs/index.cfm?catid=6&SI&SP&DS=2&DD=2&CSS=77113&rootcat=6",
}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        for label, url in TABS.items():
            print(f"\n======= {label.upper()} — {url}")
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(2500)

            hrefs = page.eval_on_selector_all(
                "a",
                "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
            )
            print(f"  total links: {len(hrefs)}")
            for h in hrefs:
                href = h["href"] or ""
                text = h["text"] or ""
                if "ens.lacity.org" in href or ".pdf" in href.lower() or "Journal" in text or "clkcouncilactions" in href:
                    print(f"   {text[:100]!r} -> {href}")

            # Check for an iframe?
            print("  frames:", [f.url for f in page.frames])

            # Dump body text preview
            bt = page.inner_text("body")
            print(f"  body text preview (first 1500 chars):\n{bt[:1500]}\n")

        browser.close()


if __name__ == "__main__":
    main()
