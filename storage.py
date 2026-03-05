import csv
import os
from datetime import date

FIELDNAMES = [
    "scrape_date", "platform", "market", "currency", "tier_name",
    "fee_amount", "fee_period", "prop_value_min", "prop_value_max",
    "location_note", "hybrid_note",
]


def append_rows(csv_path: str, rows: list[dict]) -> None:
    """Append rows to the pricing CSV, writing header if file is new."""
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})
    print(f"Wrote {len(rows)} row(s) to {csv_path}")
