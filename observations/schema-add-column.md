# Schema drift — add column (`discount_code`)

| | |
|---|---|
| **Pipeline stopped?** | Not reached |
| **Chatbot fix worked?** | N/A |
| **Severity** | Medium (blocked) |

## What I changed
New column `discount_code` appended ([dataset](../datasets/schema-add-column.csv)).

## What I expected
Nothing in the pipeline references it, so it should pass through untouched. Question: does it reach the output (silent schema change downstream) or get dropped?

## What happened on Rhombus
Not run on the platform: switching the input dataset breaks the pipeline at node 2 for any file ([05](05-dataset-swap-breaks-pipeline.md)), so the result would describe the swap bug, not this drift.

## What my validation caught (before the pipeline runs)
`python data-validation/validate.py --case precheck-schema-add-column --input datasets/schema-add-column.csv` ([result](../data-validation/results/precheck-schema-add-column.json)):

| group | check | status | detail |
|---|---|---|---|
| input-schema | no unexpected columns | **WARN** | new=['discount_code'] |

The baseline passes the same pre-check with 0 FAIL/WARN, so these flags are caused by the drift alone.

## To reproduce / re-test once the swap bug is fixed
1. Data Input → From Device → upload `datasets/schema-add-column.csv` → select it → ▶.
2. Download the last node's output, then:
   `python data-validation/validate.py --case schema-add-column --input datasets/schema-add-column.csv --output <output.csv> --baseline-output data-validation/outputs/baseline-reference.csv`
