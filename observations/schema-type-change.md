# Schema drift — data type change (`quantity` int → string)

| | |
|---|---|
| **Pipeline stopped?** | Yes — but at node 2, for an unrelated reason |
| **Chatbot fix worked?** | N/A |
| **Severity** | Critical (blocked) |

## What I changed
Every `quantity` value became a string like `3 units` ([dataset](../datasets/schema-type-change.csv)). Header unchanged.

## What I expected
Reading the generated Custom-node code: `float('3 units')` fails → NaN → the code drops every row where quantity is NaN. Prediction: **a successful run with an empty output** — the worst outcome, because nothing would signal it.

## What happened on Rhombus
Uploaded via Data Input → From Device, selected, ran ▶. Failed at node 2 (`orders_no_exact_dupes`) with `DataFrameDuplicateRowRemover.transform() missing 1 required positional argument: 'columns'` — the same error the **unchanged original file** produces after a dataset switch. The drifted data never reached a step that could react to it. See [05](05-dataset-swap-breaks-pipeline.md).

## What my validation caught (before the pipeline runs)
`python data-validation/validate.py --case precheck-schema-type-change --input datasets/schema-type-change.csv` ([result](../data-validation/results/precheck-schema-type-change.json)):

| group | check | status | detail |
|---|---|---|---|
| input-schema | quantity is numeric | **FAIL** | 213 non-numeric values (3 planted in baseline) |

The baseline passes the same pre-check with 0 FAIL/WARN, so these flags are caused by the drift alone.

## To reproduce / re-test once the swap bug is fixed
1. Data Input → From Device → upload `datasets/schema-type-change.csv` → select it → ▶.
2. Download the last node's output, then:
   `python data-validation/validate.py --case schema-type-change --input datasets/schema-type-change.csv --output <output.csv> --baseline-output data-validation/outputs/baseline-reference.csv`
