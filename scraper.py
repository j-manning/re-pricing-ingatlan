"""
Ingatlan.com pricing scraper (Hungary) — uses Playwright.

Source: https://hirdetesfeladas.ingatlan.com/szolgaltatasaink-maganhirdetoknek/osszes-csomag

Pricing varies by:
  1. Location: Budapest vs Pest County vs Other regions
  2. Property value relative to threshold:
       Budapest:    28,000,000 HUF threshold
       Pest County: 20,000,000 HUF threshold
       Other:       no value-based threshold

Free tier: listings below threshold in each region (no fee).
Paid tiers: listings above threshold, and optional package upgrades.

The page may require selecting a location or property type via UI controls;
Playwright handles this by waiting for dynamic content to load.

fee_period = per_listing
hybrid_note = "free tier exists below threshold"
"""

import re
from datetime import date

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import (
    PLATFORM, MARKET, CURRENCY, PRICING_URL, CSV_PATH,
    BUDAPEST_THRESHOLD_HUF, PEST_COUNTY_THRESHOLD_HUF, PLAYWRIGHT_TIMEOUT,
)
from storage import append_rows

# Known tiers from last manual verification (2026-03)
# Structure: (tier_name, fee_amount, prop_value_min, prop_value_max, location_note, hybrid_note)
KNOWN_TIERS = [
    # Budapest — above threshold
    {
        "tier_name": "Budapest — Alap (above threshold)",
        "fee_amount": 9900,
        "prop_value_min": BUDAPEST_THRESHOLD_HUF,
        "prop_value_max": "",
        "location_note": "Budapest",
        "hybrid_note": "free tier exists below 28M HUF threshold",
    },
    {
        "tier_name": "Budapest — Emelt (above threshold)",
        "fee_amount": 19900,
        "prop_value_min": BUDAPEST_THRESHOLD_HUF,
        "prop_value_max": "",
        "location_note": "Budapest",
        "hybrid_note": "free tier exists below 28M HUF threshold",
    },
    {
        "tier_name": "Budapest — Prémium (above threshold)",
        "fee_amount": 39900,
        "prop_value_min": BUDAPEST_THRESHOLD_HUF,
        "prop_value_max": "",
        "location_note": "Budapest",
        "hybrid_note": "free tier exists below 28M HUF threshold",
    },
    # Pest County — above threshold
    {
        "tier_name": "Pest megye — Alap (above threshold)",
        "fee_amount": 4900,
        "prop_value_min": PEST_COUNTY_THRESHOLD_HUF,
        "prop_value_max": "",
        "location_note": "Pest megye",
        "hybrid_note": "free tier exists below 20M HUF threshold",
    },
    {
        "tier_name": "Pest megye — Emelt (above threshold)",
        "fee_amount": 9900,
        "prop_value_min": PEST_COUNTY_THRESHOLD_HUF,
        "prop_value_max": "",
        "location_note": "Pest megye",
        "hybrid_note": "free tier exists below 20M HUF threshold",
    },
    {
        "tier_name": "Pest megye — Prémium (above threshold)",
        "fee_amount": 19900,
        "prop_value_min": PEST_COUNTY_THRESHOLD_HUF,
        "prop_value_max": "",
        "location_note": "Pest megye",
        "hybrid_note": "free tier exists below 20M HUF threshold",
    },
    # Vidék (other regions) — flat fee, no threshold
    {
        "tier_name": "Vidék — Alap",
        "fee_amount": 2900,
        "prop_value_min": "",
        "prop_value_max": "",
        "location_note": "vidék (other regions)",
        "hybrid_note": "no value threshold for regional listings",
    },
    {
        "tier_name": "Vidék — Emelt",
        "fee_amount": 5900,
        "prop_value_min": "",
        "prop_value_max": "",
        "location_note": "vidék (other regions)",
        "hybrid_note": "no value threshold for regional listings",
    },
    {
        "tier_name": "Vidék — Prémium",
        "fee_amount": 9900,
        "prop_value_min": "",
        "prop_value_max": "",
        "location_note": "vidék (other regions)",
        "hybrid_note": "no value threshold for regional listings",
    },
]


def extract_huf_amounts(text: str) -> list[int]:
    """Extract HUF price amounts from page text (e.g. '9 900 Ft', '39 900 Ft')."""
    # Match patterns like "9 900" or "39900" followed optionally by Ft/HUF
    matches = re.findall(r"(\d[\d\s]{2,})\s*(?:Ft|HUF)", text)
    amounts = []
    for m in matches:
        try:
            val = int(m.replace(" ", "").replace("\xa0", ""))
            if 1000 <= val <= 1_000_000:  # Plausible listing fee range
                amounts.append(val)
        except ValueError:
            pass
    return sorted(set(amounts))


def scrape_with_playwright() -> tuple[list[int], str]:
    """
    Use Playwright to load the pricing page and extract text content.
    Returns (huf_amounts_found, full_page_text).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="hu-HU",
        )
        page = context.new_page()

        try:
            page.goto(PRICING_URL, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT)
        except PlaywrightTimeout:
            print("Page load timed out on networkidle — continuing with domcontentloaded state.")
            page.goto(PRICING_URL, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT)

        # Wait for pricing content — look for Ft amounts
        try:
            page.wait_for_selector("text=Ft", timeout=10_000)
        except PlaywrightTimeout:
            print("Could not find 'Ft' text on page within timeout.")

        # Some pages show pricing only after clicking a location selector
        # Try clicking through region options if present
        for region_label in ["Budapest", "Pest megye", "Vidék"]:
            try:
                btn = page.locator(f"text={region_label}").first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass

        text = page.inner_text("body")
        browser.close()

    amounts = extract_huf_amounts(text)
    return amounts, text


def build_rows(amounts_found: list[int], verified: bool, today: str) -> list[dict]:
    rows = []
    for tier in KNOWN_TIERS:
        note = tier["hybrid_note"]
        if not verified:
            note += " [UNVERIFIED — page structure changed or Playwright failed]"
        rows.append({
            "scrape_date": today,
            "platform": PLATFORM,
            "market": MARKET,
            "currency": CURRENCY,
            "tier_name": tier["tier_name"],
            "fee_amount": tier["fee_amount"],
            "fee_period": "per_listing",
            "prop_value_min": tier["prop_value_min"],
            "prop_value_max": tier["prop_value_max"],
            "location_note": tier["location_note"],
            "hybrid_note": note,
        })
    return rows


def main():
    today = date.today().isoformat()
    print(f"Fetching Ingatlan.com pricing via Playwright: {PRICING_URL}")

    try:
        amounts, text = scrape_with_playwright()
        print(f"HUF amounts found on page: {amounts}")

        # Verify at least some known amounts are present
        known_amounts = {t["fee_amount"] for t in KNOWN_TIERS}
        matched = known_amounts & set(amounts)
        verified = len(matched) >= 3

        if verified:
            print(f"Verified {len(matched)} known tier amounts on live page.")
        else:
            print(
                f"WARNING: Only {len(matched)} known amounts matched "
                f"({matched}). Using last-known values."
            )

    except Exception as e:
        print(f"Playwright scrape failed: {e}")
        print("Falling back to last-known values.")
        verified = False

    rows = build_rows(amounts_found=[], verified=verified, today=today)
    append_rows(CSV_PATH, rows)


if __name__ == "__main__":
    main()
