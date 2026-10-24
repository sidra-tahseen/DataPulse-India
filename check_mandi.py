
import json
from pathlib import Path
from datetime import datetime

folder = Path("data/raw")
files = sorted(
    folder.glob("mandi_prices_*.json"),
    key=lambda p: p.stat().st_mtime,
)

if len(files) < 2:
    print("Need at least two snapshots.")
    raise SystemExit(1)

snapshots = []

for path in files[-2:]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    snapshots.append(records)

    print(f"\n{path.name}: {len(records)} records")
    if records:
        print("Sample:", records[0])

identity_fields = (
    "state", "district", "market",
    "commodity", "variety", "grade",
)

def get_latest(records):
    result = {}

    for record in records:
        identity = tuple(
            str(record.get(field) or "").strip()
            for field in identity_fields
        )

        if not all(identity):
            continue

        try:
            price = float(record["modal_price"])
            date = datetime.strptime(
                record["arrival_date"], "%d/%m/%Y"
            )
        except (KeyError, TypeError, ValueError):
            continue

        if price < 0:
            continue

        old = result.get(identity)
        if old is None or date > old[0]:
            result[identity] = (date, price, record)

    return result

old = get_latest(snapshots[0])
new = get_latest(snapshots[1])
overlap = set(old) & set(new)

print("\nPrevious valid combinations:", len(old))
print("Current valid combinations:", len(new))
print("Matching combinations:", len(overlap))

for key in list(sorted(overlap))[:10]:
    print(
        "\n", key,
        "\n Previous:", old[key][1], old[key][2].get("arrival_date"),
        "\n Current: ", new[key][1], new[key][2].get("arrival_date"),
    )

changed = []

for key in sorted(overlap):
    previous_price = old[key][1]
    current_price = new[key][1]

    if previous_price != current_price:
        changed.append({
            "market": key[2],
            "commodity": key[3],
            "previous_price": previous_price,
            "current_price": current_price,
            "change": round(current_price - previous_price, 2),
        })

print("\n========== PRICE CHANGE SUMMARY ==========")
print("Matching combinations:", len(overlap))
print("Changed prices:", len(changed))
print("Unchanged prices:", len(overlap) - len(changed))

for item in changed:
    print(item)
