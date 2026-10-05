# Chatbot fix silently re-introduces a previously fixed bug

| | |
|---|---|
| **Stage** | Applying the chatbot's fix from [05](05-dataset-swap-breaks-pipeline.md) |
| **Pipeline stopped?** | **No — green run** |
| **Chatbot fix worked?** | **No** — fixed the crash, corrupted the data |
| **Severity** | Critical |

## What happened
After the chatbot "applied 6 transformations", the pipeline ran successfully on the original `baseline.csv`. Validation (`baseline-run3-after-second-chatbot-fix`, [result](../data-validation/results/baseline-run3-after-second-chatbot-fix.json)) against the reference baseline:

| | Reference (after first fix) | After this fix |
|---|---|---|
| order_id | `ORD-1002` | `ORD1002` — hyphen stripped, IDs no longer match the source |
| email | 179 valid | **all 197 blank** |
| amount_usd | `114.12` | `11412.0` — **×100 again** |
| rows | 193 | 197 — the 4 negative quantities lost their `-` sign (`-3` → `3`), so rows that should be dropped now pass as positive orders |

The rebuild brought back the punctuation-stripping behaviour fixed in [03](03-baseline-text-cleanup-corrupts-email-and-amount.md), and widened it to `order_id` and `quantity`.

## Why it matters
A fix for one error undid an earlier fix, with no diff shown and a success status. A user who trusts the green run publishes data with wrong IDs, wrong money and invalid orders. Only the external validation caught it.

## Suggestion
Show a diff of node configuration before applying a chatbot fix, and re-run a small row-level check (or the previous run's output comparison) automatically after any AI change.
