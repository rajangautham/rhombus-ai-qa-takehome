# Schema drift — all four changes together

| | |
|---|---|
| **Pipeline stopped?** | Not reached |
| **Chatbot fix worked?** | N/A |
| **Severity** | High (blocked) |

## What I changed
Drop `country`, rename `amount_usd` → `order_amount`, `quantity` → string, add `discount_code` ([dataset](../datasets/schema-combined.csv)).

## What I expected
Fails on the first missing column; the question is whether the error reports *all* the changes or only the first.

## What happened on Rhombus
Not run on the platform: switching the input dataset breaks the pipeline at node 2 for any file ([05](05-dataset-swap-breaks-pipeline.md)), so the result would describe the swap bug, not this drift.

## What my validation caught (before the pipeline runs)
`python data-validation/validate.py --case precheck-schema-combined --input datasets/schema-combined.csv` ([result](../data-validation/results/precheck-schema-combined.json)):

| group | check | status | detail |
|---|---|---|---|
| input-schema | expected columns present | **FAIL** | missing=['amount_usd', 'country'] |
| input-schema | no unexpected columns | **WARN** | new=['discount_code', 'order_amount'] |
| input-schema | quantity is numeric | **FAIL** | 213 non-numeric values (3 planted in baseline) |

The baseline passes the same pre-check with 0 FAIL/WARN, so these flags are caused by the drift alone.

## To reproduce / re-test once the swap bug is fixed
1. Data Input → From Device → upload `datasets/schema-combined.csv` → select it → ▶.
2. Download the last node's output, then:
   `python data-validation/validate.py --case schema-combined --input datasets/schema-combined.csv --output <output.csv> --baseline-output data-validation/outputs/baseline-reference.csv`
