# re-pricing-ingatlan

Weekly scraper for **Ingatlan.com** listing fees (Hungary) — uses Playwright.

## Platform

Ingatlan.com is Hungary's dominant real estate portal.

## Pricing Model

**Per-listing fee** that varies by region and property value:

### Budapest
| Tier | Property Value | Fee (HUF) |
|------|---------------|-----------|
| Free | ≤ 28,000,000 Ft | 0 |
| Alap | > 28,000,000 Ft | 9,900 |
| Emelt | > 28,000,000 Ft | 19,900 |
| Prémium | > 28,000,000 Ft | 39,900 |

### Pest County
| Tier | Property Value | Fee (HUF) |
|------|---------------|-----------|
| Free | ≤ 20,000,000 Ft | 0 |
| Alap | > 20,000,000 Ft | 4,900 |
| Emelt | > 20,000,000 Ft | 9,900 |
| Prémium | > 20,000,000 Ft | 19,900 |

### Vidék (Other Regions)
| Tier | Fee (HUF) |
|------|-----------|
| Alap | 2,900 |
| Emelt | 5,900 |
| Prémium | 9,900 |

- `fee_period = per_listing`
- `currency = HUF`
- `hybrid_note = "free tier exists below threshold"` (Budapest/Pest County)

Source: [Ingatlan.com magánhirdetők szolgáltatásai](https://hirdetesfeladas.ingatlan.com/szolgaltatasaink-maganhirdetoknek/osszes-csomag)

## Why Playwright?

The pricing page uses dynamic rendering and may require interacting with region
selector controls. Playwright handles this reliably.

## Running Locally

```bash
pip install -r requirements.txt
playwright install chromium
python scraper.py
```
