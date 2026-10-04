"""
Compare a Rhombus AI output (GCS) with its input (S3), the baseline output and
the seeded ground truth. Writes a JSON result per case and exits non-zero on
any FAIL, so it can run in CI.

Paths may be local files, s3://bucket/key or gs://bucket/key.

Examples
  # baseline
  python data-validation/validate.py --case baseline \
      --input s3://my-src/orders.csv --output gs://my-dst/orders_clean.csv

  # drifted run, compared against the saved baseline output
  python data-validation/validate.py --case semantic-dollars-to-cents \
      --input datasets/semantic-dollars-to-cents.csv \
      --output gs://my-dst/orders_clean.csv \
      --baseline-output data-validation/outputs/baseline.csv

  # determinism: same input run 3 times
  python data-validation/validate.py --case baseline-determinism \
      --input datasets/baseline.csv --output out1.csv --repeat-outputs out2.csv out3.csv
"""
import argparse
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent
DATASETS = ROOT / "datasets"
RESULTS = HERE / "results"
OUTPUTS = HERE / "outputs"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EXPECTED_COLUMNS = ["order_id", "customer_name", "email", "order_date", "amount_usd",
                    "quantity", "country", "status"]
# Rhombus may rename columns while cleaning; map known aliases back to canonical names.
ALIASES = {"order_amount": "amount_usd", "amount": "amount_usd", "date": "order_date",
           "name": "customer_name", "qty": "quantity"}


# ---------------------------------------------------------------- I/O
def read_csv(path: str) -> pd.DataFrame:
    if path.startswith("s3://"):
        import boto3  # pip install boto3 ; creds from env / ~/.aws
        bucket, key = path[5:].split("/", 1)
        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
        return pd.read_csv(io.BytesIO(body), dtype=str, keep_default_na=False)
    if path.startswith("gs://"):
        from google.cloud import storage  # pip install google-cloud-storage ; GOOGLE_APPLICATION_CREDENTIALS
        bucket, key = path[5:].split("/", 1)
        data = storage.Client().bucket(bucket).blob(key).download_as_bytes()
        return pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols = [re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_") for c in df.columns]
    df.columns = [ALIASES.get(c, c) for c in cols]
    return df


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[$,\s]", "", regex=True), errors="coerce")


def parse_dates(s: pd.Series, dayfirst=False) -> pd.Series:
    return pd.to_datetime(s.replace("", None), errors="coerce", format="mixed", dayfirst=dayfirst)


def content_hash(df: pd.DataFrame) -> str:
    d = norm_cols(df)
    d = d[sorted(d.columns)]
    d = d.sort_values(list(d.columns)).reset_index(drop=True)
    return hashlib.sha256(d.to_csv(index=False).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- checks
class Report:
    def __init__(self, case):
        self.case, self.checks = case, []

    def add(self, group, name, status, detail):
        self.checks.append({"group": group, "check": name, "status": status, "detail": detail})

    def ok(self, g, n, cond, detail, warn_only=False):
        self.add(g, n, "PASS" if cond else ("WARN" if warn_only else "FAIL"), detail)


def check_schema(r, inp, out):
    exp, got, src = set(EXPECTED_COLUMNS), set(out.columns), set(inp.columns)
    missing, extra = sorted(exp - got), sorted(got - exp)
    r.ok("schema", "output has baseline columns", not missing, f"missing={missing} extra={extra}")
    r.ok("schema", "input columns all reach output", src <= got,
         f"dropped_by_pipeline={sorted(src - got)}", warn_only=True)
    r.add("schema", "column order", "INFO", list(out.columns))


def check_rows(r, inp, out, manifest):
    n_in, n_out = len(inp), len(out)
    r.add("rows", "counts", "INFO", {"input": n_in, "output": n_out, "removed": n_in - n_out})
    r.ok("rows", "output not larger than input", n_out <= n_in, f"{n_out} <= {n_in}")
    r.ok("rows", "output not empty", n_out > 0, f"{n_out} rows")
    if manifest and n_in == manifest["input_rows"]:
        lo, hi = manifest["expected_rows_after_id_dedup"] - 30, manifest["expected_rows_after_exact_dedup"]
        r.ok("rows", "row count in plausible cleaned range", lo <= n_out <= hi,
             f"expected {lo}..{hi} (exact-dedup={hi}, id-dedup={manifest['expected_rows_after_id_dedup']}, "
             f"lower bound allows dropping invalid rows)", warn_only=True)


def check_cleaning(r, out, manifest):
    g = "cleaning"
    r.ok(g, "no exact duplicate rows", not out.duplicated().any(), f"{int(out.duplicated().sum())} duplicates")
    if "order_id" in out:
        d = int(out["order_id"].duplicated().sum())
        r.ok(g, "order_id unique", d == 0, f"{d} repeated ids (3 planted conflicting-content dupes)", warn_only=True)
    for col in ["order_id", "email", "amount_usd", "country"]:
        if col in out:
            n = int((out[col].astype(str).str.strip() == "").sum())
            r.ok(g, f"no blanks in {col}", n == 0, f"{n} blank", warn_only=(col != "order_id"))
    if "email" in out:
        e = out["email"].astype(str).str.strip()
        bad = e[(e != "") & ~e.str.match(EMAIL_RE)]
        r.ok(g, "emails valid", bad.empty, f"{len(bad)} invalid: {bad.head(5).tolist()}")
    if "country" in out and manifest:
        vals = set(out["country"].astype(str).str.strip()) - {""}
        bad = sorted(vals - set(manifest["canonical_countries"]))
        r.ok(g, "country standardised", not bad, f"non-canonical values: {bad}")
    if "status" in out and manifest:
        vals = set(out["status"].astype(str).str.strip().str.lower()) - {""}
        bad = sorted(vals - set(manifest["canonical_statuses"]))
        cased = out["status"].astype(str).str.strip().nunique() <= len(manifest["canonical_statuses"]) + 1
        r.ok(g, "status standardised", not bad and cased, f"non-canonical: {bad}, distinct={sorted(out['status'].unique())}")
    if "customer_name" in out:
        s = out["customer_name"].astype(str)
        ws = int((s != s.str.strip()).sum())
        r.ok(g, "names trimmed", ws == 0, f"{ws} with leading/trailing spaces")
    if "quantity" in out:
        q = to_num(out["quantity"])
        r.ok(g, "quantity numeric", q.notna().all(), f"{int(q.isna().sum())} non-numeric")
        r.ok(g, "quantity non-negative", (q.dropna() >= 0).all(), f"{int((q < 0).sum())} negative")
    if "amount_usd" in out:
        a = to_num(out["amount_usd"])
        has_symbol = int(out["amount_usd"].astype(str).str.contains(r"\$").sum())
        r.ok(g, "amount numeric (no $)", has_symbol == 0, f"{has_symbol} still contain '$'")
    if "order_date" in out:
        d = parse_dates(out["order_date"])
        r.ok(g, "dates parseable", d.notna().all(), f"{int(d.isna().sum())} unparseable")
        fmts = out["order_date"].astype(str).str.replace(r"\d", "9", regex=True).value_counts().to_dict()
        r.ok(g, "single date format", len(fmts) <= 1, f"formats seen: {fmts}", warn_only=True)


def check_semantics(r, out, truth, base_out):
    g = "semantic"
    # 1) Row-level against ground truth (we know the right answer for every order_id)
    if truth is not None and "order_id" in out:
        m = out.drop_duplicates("order_id").merge(truth, on="order_id", suffixes=("", "_truth"))
        r.add(g, "rows joinable to ground truth", "INFO", f"{len(m)} of {len(truth)}")
        if "amount_usd" in m:
            a, t = to_num(m["amount_usd"]), to_num(m["amount_usd_truth"])
            ok = (a - t).abs() <= 0.01
            ratio = (a / t).median()
            r.ok(g, "amounts match truth", ok[a.notna()].mean() > 0.98,
                 f"{int((~ok & a.notna()).sum())} mismatched; median output/truth ratio={ratio:.2f}")
        if "order_date" in m:
            d, t = parse_dates(m["order_date"]), parse_dates(m["order_date_truth"])
            match = (d == t)
            swapped = (d.dt.month == t.dt.day) & (d.dt.day == t.dt.month) & (t.dt.day != t.dt.month)
            r.ok(g, "dates match truth", match[d.notna()].mean() > 0.98,
                 f"match={int(match.sum())}, day/month swapped={int(swapped.sum())}, "
                 f"unparseable/blank={int(d.isna().sum())}")
    # 2) Distribution vs baseline output — what you'd have in production with no ground truth
    if base_out is not None:
        if "amount_usd" in out and "amount_usd" in base_out:
            cur, base = to_num(out["amount_usd"]).median(), to_num(base_out["amount_usd"]).median()
            ratio = cur / base if base else float("nan")
            r.ok(g, "amount distribution stable vs baseline", 0.5 < ratio < 2,
                 f"median {cur:.2f} vs baseline {base:.2f} (x{ratio:.1f}); ~x100 suggests cents")
        if "order_date" in out and "order_date" in base_out:
            cur, base = parse_dates(out["order_date"]), parse_dates(base_out["order_date"])
            nat_cur, nat_base = cur.isna().mean(), base.isna().mean()
            r.ok(g, "date parse rate stable vs baseline", nat_cur - nat_base < 0.05,
                 f"unparseable {nat_cur:.0%} vs baseline {nat_base:.0%}")
            cd = cur.dropna().dt.day
            r.ok(g, "day-of-month not capped at 12", cd.empty or cd.max() > 12,
                 f"max day={None if cd.empty else int(cd.max())} (all <=12 implies day/month swap)", warn_only=True)
            mshift = abs(cur.dt.month.mean() - base.dt.month.mean())
            r.ok(g, "month distribution stable vs baseline", not (mshift > 1),
                 f"mean month {cur.dt.month.mean():.1f} vs {base.dt.month.mean():.1f}", warn_only=True)


def check_input_profile(r, inp):
    """Source-side drift guards: catch semantic drift before the pipeline can hide it."""
    g = "input-profile"
    if "order_date" in inp:
        parts = inp["order_date"].astype(str).str.extract(r"^(\d{1,2})/(\d{1,2})/\d{4}$").dropna().astype(int)
        first_gt12 = int((parts[0] > 12).sum())
        r.ok(g, "slash dates look MM/DD (first part <= 12)", first_gt12 == 0,
             f"{first_gt12} of {len(parts)} slash dates have first part > 12"
             + (" -> source looks DD/MM; the other " + str(len(parts) - first_gt12)
                + " are ambiguous and can be silently swapped" if first_gt12 else ""))
    if "amount_usd" in inp:
        a = to_num(inp["amount_usd"]).dropna()
        whole = float((a == a.round()).mean()) if len(a) else 0
        r.ok(g, "amounts look like dollars (not integer cents)", whole < 0.5 and a.median() < 5000,
             f"median={a.median():.2f}, share of whole numbers={whole:.0%}")


def check_determinism(r, outputs):
    hashes = [content_hash(o) for o in outputs]
    r.ok("determinism", f"{len(outputs)} runs identical", len(set(hashes)) == 1, {"hashes": hashes})
    if len(set(hashes)) > 1:
        a, b = norm_cols(outputs[0]), norm_cols(outputs[[h != hashes[0] for h in hashes].index(True)])
        r.add("determinism", "diff summary", "INFO", {
            "rows": [len(a), len(b)],
            "cols_only_in_first": sorted(set(a.columns) - set(b.columns)),
            "cols_only_in_other": sorted(set(b.columns) - set(a.columns))})


# ---------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--baseline-output")
    p.add_argument("--repeat-outputs", nargs="*", default=[])
    p.add_argument("--manifest", default=str(DATASETS / "manifest.json"))
    p.add_argument("--truth", default=str(DATASETS / "ground_truth.csv"))
    a = p.parse_args()

    inp, out_raw = read_csv(a.input), read_csv(a.output)
    inp, out = norm_cols(inp), norm_cols(out_raw)
    manifest = json.loads(Path(a.manifest).read_text()) if Path(a.manifest).exists() else None
    truth = norm_cols(read_csv(a.truth)) if Path(a.truth).exists() else None
    base_out = norm_cols(read_csv(a.baseline_output)) if a.baseline_output else None

    OUTPUTS.mkdir(exist_ok=True); RESULTS.mkdir(exist_ok=True)
    out_raw.to_csv(OUTPUTS / f"{a.case}.csv", index=False)  # keep a copy of what GCS held

    r = Report(a.case)
    check_input_profile(r, inp)
    check_schema(r, inp, out)
    check_rows(r, inp, out, manifest)
    check_cleaning(r, out, manifest)
    check_semantics(r, out, truth, base_out)
    if a.repeat_outputs:
        check_determinism(r, [out_raw] + [read_csv(x) for x in a.repeat_outputs])

    summary = {s: sum(c["status"] == s for c in r.checks) for s in ["PASS", "WARN", "FAIL", "INFO"]}
    result = {"case": a.case, "timestamp": datetime.now(timezone.utc).isoformat(),
              "input": a.input, "output": a.output, "output_hash": content_hash(out_raw),
              "summary": summary, "checks": r.checks}
    (RESULTS / f"{a.case}.json").write_text(json.dumps(result, indent=2, default=str))

    print(f"\n== {a.case} ==  {summary}")
    for c in r.checks:
        if c["status"] != "INFO":
            print(f"  [{c['status']:4}] {c['group']:12} {c['check']:42} {c['detail']}")
    sys.exit(1 if summary["FAIL"] else 0)


if __name__ == "__main__":
    main()
