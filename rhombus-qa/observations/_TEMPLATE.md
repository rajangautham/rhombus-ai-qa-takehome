# <case name, e.g. Schema drift — rename column>

| | |
|---|---|
| **Dataset** | [`datasets/<file>.csv`](../datasets/<file>.csv) |
| **Run type** | Scheduled / manual (and why) |
| **Run time (UTC)** | |
| **Pipeline stopped?** | Yes / No / Partially |
| **Chatbot fix worked?** | Yes / No / Partially / N/A |
| **Severity** | Critical / High / Medium / Low |

## What I changed
One or two sentences plus the exact diff (old header → new header, sample row before/after).

## What I expected
What a customer would reasonably expect: fail loudly, warn, or adapt, and why.

## What happened
- Run status in the UI:
- What reached GCS (file present? columns? row count?):
- Validation result: `python data-validation/validate.py --case <case> ...` → PASS/WARN/FAIL summary

![run status](evidence/<case>-run-status.png)

## What the logs said
```
<paste the relevant log lines>
```
Does it name the column and the step that failed? Could a user act on it?

## What the chatbot said
Prompt I gave it (verbatim) → its diagnosis → its suggested fix.

![chatbot](evidence/<case>-chatbot.png)

## Did the fix work?
What I applied, the re-run result, and whether the output was correct (validation result again).

## Schedule afterwards
Did the next scheduled run still fire? Is the pipeline disabled, retrying, or unchanged?

## Steps to reproduce
1. Upload `datasets/<file>.csv` to `s3://<bucket>/<key>`, overwriting the baseline file
2. Wait for the next scheduled run (or trigger a run)
3. `python data-validation/validate.py --case <case> --input datasets/<file>.csv --output gs://<bucket>/<key> --baseline-output data-validation/outputs/baseline.csv`
