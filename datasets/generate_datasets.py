"""
Generate the baseline messy CSV plus every drifted variant, from one seeded
ground truth. Every defect is planted on purpose and recorded in manifest.json,
so data validation can check cleaning against known answers.

Usage:  python datasets/generate_datasets.py        (writes into datasets/)
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
N_ROWS = 200
OUT = Path(__file__).parent

FIRST = ["Alice", "Bob", "Chen", "Diya", "Ethan", "Fatima", "George", "Hana", "Ivan", "Jia",
         "Kofi", "Lena", "Mateo", "Nora", "Omar", "Priya", "Quinn", "Ravi", "Sofia", "Tom"]
LAST = ["Smith", "Nguyen", "Patel", "Garcia", "Kim", "Brown", "Singh", "Lee", "Wong", "Jones"]
COUNTRIES = ["Australia", "United States", "India", "United Kingdom", "Singapore"]
COUNTRY_VARIANTS = {
    "Australia": ["australia", "AUS", " Australia ", "AU"],
    "United States": ["USA", "usa", "US", "United states"],
    "India": ["india", "IND", " India"],
    "United Kingdom": ["UK", "uk", "Great Britain"],
    "Singapore": ["singapore", "SG"],
}
STATUSES = ["shipped", "pending", "delivered", "cancelled"]
STATUS_VARIANTS = {"shipped": ["SHIPPED", "Shipped "], "pending": ["Pending", "PENDING"],
                   "delivered": ["Delivered", " delivered"], "cancelled": ["Canceled", "CANCELLED"]}

COLUMNS = ["order_id", "customer_name", "email", "order_date", "amount_usd", "quantity",
           "country", "status"]


def build_truth(rng):
    """Clean ground truth: what a perfect cleaning pipeline should produce."""
    rows = []
    start = date(2026, 1, 1)
    for i in range(N_ROWS):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        rows.append({
            "order_id": f"ORD-{1000 + i}",
            "customer_name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{i}@example.com",
            "order_date": start + timedelta(days=rng.randint(0, 270)),
            "amount_usd": round(rng.uniform(5, 500), 2),
            "quantity": rng.randint(1, 10),
            "country": rng.choice(COUNTRIES),
            "status": rng.choice(STATUSES),
        })
    return rows


def fmt_date(d, style):
    if style == "mdy":
        return d.strftime("%m/%d/%Y")
    if style == "dmy":
        return d.strftime("%d/%m/%Y")
    return d.isoformat()


def to_raw(row, date_style="mdy"):
    r = dict(row)
    r["order_date"] = fmt_date(row["order_date"], date_style)
    r["amount_usd"] = f"{row['amount_usd']:.2f}"
    r["quantity"] = str(row["quantity"])
    return r


def build_baseline(truth, rng):
    """Inject defects into the truth. Returns raw rows + manifest of what was planted."""
    raw = [to_raw(r) for r in truth]
    m = {k: [] for k in ["missing_email", "missing_amount", "missing_country", "invalid_email",
                         "negative_quantity", "nonnumeric_quantity", "inconsistent_country",
                         "inconsistent_status", "whitespace_name", "dollar_sign_amount",
                         "iso_date", "exact_duplicates", "id_duplicates_conflicting"]}
    idx = list(range(len(raw)))
    rng.shuffle(idx)
    take = iter(idx)

    def pick(n):
        return [next(take) for _ in range(n)]

    for i in pick(8):
        raw[i]["email"] = ""; m["missing_email"].append(raw[i]["order_id"])
    for i in pick(6):
        raw[i]["amount_usd"] = ""; m["missing_amount"].append(raw[i]["order_id"])
    for i in pick(5):
        raw[i]["country"] = ""; m["missing_country"].append(raw[i]["order_id"])
    for i, bad in zip(pick(6), ["not-an-email", "jia.lee@", "@example.com", "bob at example.com",
                                "priya..patel@example", "N/A"]):
        raw[i]["email"] = bad; m["invalid_email"].append(raw[i]["order_id"])
    for i in pick(4):
        raw[i]["quantity"] = str(-int(raw[i]["quantity"])); m["negative_quantity"].append(raw[i]["order_id"])
    for i, bad in zip(pick(3), ["three", "2 pcs", "?"]):
        raw[i]["quantity"] = bad; m["nonnumeric_quantity"].append(raw[i]["order_id"])
    for i in pick(25):
        c = raw[i]["country"]
        if c in COUNTRY_VARIANTS:
            raw[i]["country"] = rng.choice(COUNTRY_VARIANTS[c]); m["inconsistent_country"].append(raw[i]["order_id"])
    for i in pick(20):
        s = raw[i]["status"]
        raw[i]["status"] = rng.choice(STATUS_VARIANTS[s]); m["inconsistent_status"].append(raw[i]["order_id"])
    for i in pick(10):
        raw[i]["customer_name"] = f"  {raw[i]['customer_name'].upper()} "; m["whitespace_name"].append(raw[i]["order_id"])
    for i in pick(8):
        if raw[i]["amount_usd"]:
            raw[i]["amount_usd"] = "$" + raw[i]["amount_usd"]; m["dollar_sign_amount"].append(raw[i]["order_id"])
    for i in pick(6):
        raw[i]["order_date"] = fmt_date(truth[i]["order_date"], "iso"); m["iso_date"].append(raw[i]["order_id"])

    # Exact duplicate rows (should be removed)
    dup_src = pick(10)
    dups = [dict(raw[i]) for i in dup_src]
    m["exact_duplicates"] = [raw[i]["order_id"] for i in dup_src]
    # Same order_id, conflicting content (a judgement call for the pipeline)
    conflict_src = pick(3)
    conflicts = []
    for i in conflict_src:
        c = dict(raw[i]); c["status"] = "pending" if raw[i]["status"] != "pending" else "shipped"
        conflicts.append(c); m["id_duplicates_conflicting"].append(raw[i]["order_id"])

    final = raw + dups + conflicts
    rng.shuffle(final)
    manifest = {
        "seed": SEED,
        "input_rows": len(final),
        "unique_order_ids": N_ROWS,
        "expected_rows_after_exact_dedup": len(final) - len(dups),
        "expected_rows_after_id_dedup": N_ROWS,
        "canonical_countries": COUNTRIES,
        "canonical_statuses": STATUSES,
        "planted_defects": m,
        "defect_counts": {k: len(v) for k, v in m.items()},
    }
    return final, manifest


def write_csv(path, rows, columns):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def main():
    rng = random.Random(SEED)
    truth = build_truth(rng)
    baseline, manifest = build_baseline(truth, rng)
    truth_by_id = {t["order_id"]: t for t in truth}

    # Ground truth (clean) – used by validation for row-level semantic checks
    write_csv(OUT / "ground_truth.csv",
              [{**t, "order_date": t["order_date"].isoformat()} for t in truth], COLUMNS)
    write_csv(OUT / "baseline.csv", baseline, COLUMNS)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))

    variants = {}

    # --- Schema drift ---
    variants["schema-drop-column"] = ([dict(r) for r in baseline], [c for c in COLUMNS if c != "country"],
                                      "Dropped `country` (a column the cleaning pipeline standardises).")
    ren = [{**{k: v for k, v in r.items() if k != "amount_usd"}, "order_amount": r["amount_usd"]} for r in baseline]
    variants["schema-rename-column"] = (ren, [("order_amount" if c == "amount_usd" else c) for c in COLUMNS],
                                        "Renamed `amount_usd` -> `order_amount`.")
    typ = []
    for r in baseline:
        q = r["quantity"]
        typ.append({**r, "quantity": f"{q} units" if q.lstrip("-").isdigit() else q})
    variants["schema-type-change"] = (typ, COLUMNS,
                                      "`quantity` changed from integer to string (`'3 units'`).")
    add_rng = random.Random(SEED + 1)
    add = [{**r, "discount_code": add_rng.choice(["", "SAVE10", "WELCOME", "VIP20"])} for r in baseline]
    variants["schema-add-column"] = (add, COLUMNS + ["discount_code"], "Added new column `discount_code`.")
    comb = []
    for r in add:
        c = {k: v for k, v in r.items() if k not in ("country", "amount_usd")}
        c["order_amount"] = r["amount_usd"]
        q = r["quantity"]; c["quantity"] = f"{q} units" if q.lstrip("-").isdigit() else q
        comb.append(c)
    comb_cols = ["order_id", "customer_name", "email", "order_date", "order_amount", "quantity",
                 "status", "discount_code"]
    variants["schema-combined"] = (comb, comb_cols, "All four schema changes at once.")

    # --- Semantic drift (structure identical, meaning changed) ---
    cents = []
    for r in baseline:
        a = r["amount_usd"]; raw_a = a.lstrip("$")
        try:
            v = str(int(round(float(raw_a) * 100)))
            cents.append({**r, "amount_usd": ("$" if a.startswith("$") else "") + v})
        except ValueError:
            cents.append(dict(r))
    variants["semantic-dollars-to-cents"] = (cents, COLUMNS,
                                             "`amount_usd` now holds cents (x100); header unchanged.")
    dmy = []
    for r in baseline:
        d = truth_by_id[r["order_id"]]["order_date"]
        dmy.append({**r, "order_date": fmt_date(d, "dmy") if "/" in r["order_date"] else r["order_date"]})
    variants["semantic-date-ddmm"] = (dmy, COLUMNS,
                                      "`order_date` switched MM/DD/YYYY -> DD/MM/YYYY; header unchanged.")

    index = {"baseline": {"file": "baseline.csv", "description": "Messy baseline with planted defects."}}
    for name, (rows, cols, desc) in variants.items():
        fn = f"{name}.csv"; write_csv(OUT / fn, rows, cols)
        index[name] = {"file": fn, "description": desc}

    # Stats useful for the date case: how many swapped dates are silently ambiguous
    ambiguous = sum(1 for t in truth if t["order_date"].day <= 12)
    index["semantic-date-ddmm"]["note"] = (
        f"{ambiguous}/{N_ROWS} dates have day<=12, so they still parse as valid MM/DD dates "
        f"(silent corruption); the rest should fail to parse as MM/DD.")
    (OUT / "index.json").write_text(json.dumps(index, indent=2))
    print(json.dumps(index, indent=2))
    print("baseline defect counts:", json.dumps(manifest["defect_counts"]))


if __name__ == "__main__":
    main()
