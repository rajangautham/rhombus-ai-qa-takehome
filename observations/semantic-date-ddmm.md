# Semantic drift — MM/DD dates become DD/MM

| | |
|---|---|
| **Pipeline stopped?** | Not reached |
| **Chatbot fix worked?** | N/A |
| **Severity** | Critical (blocked) |

## What I changed
`order_date` written as DD/MM/YYYY; header unchanged ([dataset](../datasets/semantic-date-ddmm.csv)).

## What I expected
Two distinct failure modes: 130 of 207 slash dates have day > 12, so they cannot be MM/DD — the Custom node's strict `%m/%d/%Y` would blank them **silently**; the other 77 are ambiguous and would be **swapped silently** (3 Aug → 8 Mar). Also, Data Input already converts `order_date` to DateTime at ingestion ([evidence](evidence/06-data-input-correct-values.png)), so the swap may happen before any pipeline step can see it.

## What happened on Rhombus
Not run on the platform: switching the input dataset breaks the pipeline at node 2 for any file ([05](05-dataset-swap-breaks-pipeline.md)), so the result would describe the swap bug, not this drift.

## What my validation caught (before the pipeline runs)
`python data-validation/validate.py --case precheck-semantic-date-ddmm --input datasets/semantic-date-ddmm.csv` ([result](../data-validation/results/precheck-semantic-date-ddmm.json)):

| group | check | status | detail |
|---|---|---|---|
| input-profile | slash dates look MM/DD (first part <= 12) | **FAIL** | 130 of 207 slash dates have first part > 12 -> source looks DD/MM; the other 77 are ambiguous and can be silently swapped |

The baseline passes the same pre-check with 0 FAIL/WARN, so these flags are caused by the drift alone.

## To reproduce / re-test once the swap bug is fixed
1. Data Input → From Device → upload `datasets/semantic-date-ddmm.csv` → select it → ▶.
2. Download the last node's output, then:
   `python data-validation/validate.py --case semantic-date-ddmm --input datasets/semantic-date-ddmm.csv --output <output.csv> --baseline-output data-validation/outputs/baseline-reference.csv`
