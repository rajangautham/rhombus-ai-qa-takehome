# Schema drift — rename column (`amount_usd` → `order_amount`)

| | |
|---|---|
| **Pipeline stopped?** | Not reached |
| **Chatbot fix worked?** | N/A |
| **Severity** | High (blocked) |

## What I changed
Header `amount_usd` renamed to `order_amount`; values unchanged ([dataset](../datasets/schema-rename-column.csv)).

## What I expected
The Custom node hard-codes `df['amount_usd']`, so a `KeyError` crash — the *good* failure mode (loud). The questions were then whether the log names the column and whether the chatbot's fix handles both names.

## What happened on Rhombus
Not run on the platform: switching the input dataset breaks the pipeline at node 2 for any file ([05](05-dataset-swap-breaks-pipeline.md)), so the result would describe the swap bug, not this drift.

## What my validation caught (before the pipeline runs)
`python data-validation/validate.py --case precheck-schema-rename-column --input datasets/schema-rename-column.csv` ([result](../data-validation/results/precheck-schema-rename-column.json)):

| group | check | status | detail |
|---|---|---|---|
| input-schema | expected columns present | **FAIL** | missing=['amount_usd'] |
| input-schema | no unexpected columns | **WARN** | new=['order_amount'] |

The baseline passes the same pre-check with 0 FAIL/WARN, so these flags are caused by the drift alone.

## To reproduce / re-test once the swap bug is fixed
1. Data Input → From Device → upload `datasets/schema-rename-column.csv` → select it → ▶.
2. Download the last node's output, then:
   `python data-validation/validate.py --case schema-rename-column --input datasets/schema-rename-column.csv --output <output.csv> --baseline-output data-validation/outputs/baseline-reference.csv`
