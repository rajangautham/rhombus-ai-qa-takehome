# Semantic drift — dollars become cents

| | |
|---|---|
| **Pipeline stopped?** | Not reached |
| **Chatbot fix worked?** | N/A |
| **Severity** | Critical (blocked) |

## What I changed
`amount_usd` values ×100 as integers (114.12 → 11412); header unchanged ([dataset](../datasets/semantic-dollars-to-cents.csv)).

## What I expected
Structure is valid, so the pipeline runs and publishes amounts 100× too large. Nothing in the generated code checks ranges.

## What happened on Rhombus
Not run on the platform: switching the input dataset breaks the pipeline at node 2 for any file ([05](05-dataset-swap-breaks-pipeline.md)), so the result would describe the swap bug, not this drift.

## What my validation caught (before the pipeline runs)
`python data-validation/validate.py --case precheck-semantic-dollars-to-cents --input datasets/semantic-dollars-to-cents.csv` ([result](../data-validation/results/precheck-semantic-dollars-to-cents.json)):

| group | check | status | detail |
|---|---|---|---|
| input-profile | amounts look like dollars (not integer cents) | **FAIL** | median=27241.00, share of whole numbers=100% |

The baseline passes the same pre-check with 0 FAIL/WARN, so these flags are caused by the drift alone.

## Related evidence
**This exact corruption already happened on the clean baseline**, introduced by the platform itself ([03](03-baseline-text-cleanup-corrupts-email-and-amount.md)): Rhombus reported success and did not notice; the output validation caught it (median ratio ×100.0, 187/187 amounts mismatched).

## To reproduce / re-test once the swap bug is fixed
1. Data Input → From Device → upload `datasets/semantic-dollars-to-cents.csv` → select it → ▶.
2. Download the last node's output, then:
   `python data-validation/validate.py --case semantic-dollars-to-cents --input datasets/semantic-dollars-to-cents.csv --output <output.csv> --baseline-output data-validation/outputs/baseline-reference.csv`
