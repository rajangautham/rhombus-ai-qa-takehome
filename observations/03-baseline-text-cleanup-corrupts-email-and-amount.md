# Baseline — AI-built "trim" step silently corrupts emails and amounts (×100)

| | |
|---|---|
| **Stage** | Baseline run, no drift |
| **Pipeline stopped?** | **No — run reported success** |
| **Chatbot fix worked?** | **Yes** (verified by validation: 0 amount mismatches, no valid email lost) |
| **Severity** | Critical — silent corruption of financial values and loss of a whole column |

## What I did
Built the pipeline with `/pipeline` only ([canvas](evidence/02-ai-built-pipeline-canvas.png)). The prompt included *"Trim whitespace in all text columns"*. The AI produced 7 nodes: Data Input → Remove Duplicates (exact) → Remove Duplicates (order_id) → **Comprehensive Text Cleanup** → Text Case ×2 → Custom (generated Python, [code](evidence/custom-node-code.py)).

## Expected
Whitespace trimmed; emails kept unless invalid (6 planted invalid + 8 planted blank); amounts unchanged apart from removing `$`.

## What happened
`python data-validation/validate.py --case baseline-run1-original ...` ([result](../data-validation/results/baseline-run1-original.json)):

| order_id | true amount | output | true email | output |
|---|---|---|---|---|
| ORD-1002 | 114.12 | **11412.0** | ravi.garcia2@example.com | *(blank)* |
| ORD-1180 | 404.57 | **40457.0** | diya.kim180@example.com | *(blank)* |
| ORD-1014 | 80.66 | **8066.0** | chen.smith14@example.com | *(blank)* |

- 187 of 187 non-blank amounts exactly ×100. All 193 emails blank.
- Rows, de-duplication, country, status, names and dates were all correct.

## Root cause (isolated node by node)
- **Data Input** has correct values ([evidence](evidence/06-data-input-correct-values.png)).
- **Comprehensive Text Cleanup** is the first node where they change: `ravigarcia2examplecom`, `11412` ([evidence](evidence/05-text-cleanup-root-cause.png)). Its *Target Columns* included `email` and `amount_usd` (still text because of `$` signs), and it strips punctuation, not just whitespace.
- The Custom node's email regex (correct in itself) then rejected every punctuation-less email and blanked it ([evidence](evidence/03-final-node-emails-null.png)). Amounts reached the end ×100 ([evidence](evidence/04-final-node-amounts-x100.png)).

The preview highlights changed cells in orange, so the platform *knows* those values changed — but nothing warns that a "trim" step altered emails and money.

## Logs
Run completed successfully; no warning.

## Chatbot
Given **only the symptom** ("every email is empty and amount_usd is 100x too large, e.g. ORD-1002 should be 114.12 but is 11412"), it removed `email` and `amount_usd` from the Text Cleanup node's target columns, leaving `customer_name`, `country`, `status`. A minimal, correct fix.

## Did the fix work?
Yes. `baseline-run2-after-first-chatbot-fix`: **0 FAIL**. 179 valid emails kept; the 14 blanks are exactly the 8 missing + 6 invalid planted ones; 0 amount mismatches against ground truth. This output is the reference baseline (`data-validation/outputs/baseline-reference.csv`).

But see [06](06-chatbot-fix-regression.md): a later chatbot fix re-introduced this bug.
