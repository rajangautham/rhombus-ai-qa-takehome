# Schema drift — drop column (`country`)

| | |
|---|---|
| **Pipeline stopped?** | Not reached |
| **Chatbot fix worked?** | N/A |
| **Severity** | High (blocked) |

## What I changed
Column `country` removed ([dataset](../datasets/schema-drop-column.csv)).

## What I expected
`KeyError: 'country'` in the Custom node and in Text Cleanup's target columns. Loud failure.

## What happened on Rhombus
Not run on the platform: switching the input dataset breaks the pipeline at node 2 for any file ([05](05-dataset-swap-breaks-pipeline.md)), so the result would describe the swap bug, not this drift.

## What my validation caught (before the pipeline runs)
`python data-validation/validate.py --case precheck-schema-drop-column --input datasets/schema-drop-column.csv` ([result](../data-validation/results/precheck-schema-drop-column.json)):

| group | check | status | detail |
|---|---|---|---|
| input-schema | expected columns present | **FAIL** | missing=['country'] |

The baseline passes the same pre-check with 0 FAIL/WARN, so these flags are caused by the drift alone.

## To reproduce / re-test once the swap bug is fixed
1. Data Input → From Device → upload `datasets/schema-drop-column.csv` → select it → ▶.
2. Download the last node's output, then:
   `python data-validation/validate.py --case schema-drop-column --input datasets/schema-drop-column.csv --output <output.csv> --baseline-output data-validation/outputs/baseline-reference.csv`
