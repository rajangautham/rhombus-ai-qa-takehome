# Schedule — "Active" schedule never executes

| | |
|---|---|
| **Stage** | Scheduling |
| **Pipeline stopped?** | Pipeline never ran on schedule |
| **Chatbot fix worked?** | Not tested — the limited AI credits (50) were prioritised for the data-corruption bugs |
| **Severity** | Critical — a silently non-running schedule is worse than a visibly failing one |

## Steps to reproduce
1. Schedule tab → Add Schedule → Custom → `*/15 * * * *` → save ([evidence](evidence/07-schedule-active-every-15-min.png)).
2. Card shows **Active** and "Next run: in N secs/mins".
3. When the countdown ends, open the schedule's history (Executions).

## Expected
An execution appears every 15 minutes.

## What happened
- Executions: **"No results"** ([evidence](evidence/08-executions-empty.png)).
- "Next run:" becomes **blank**; the status stays **Active**.
- Reproduced on every edit + save and on toggling off/on: a fresh countdown appears, then nothing runs.
- Left **Active overnight** (from about 9:30pm on 5 Oct to the morning of 6 Oct, roughly 50 expected runs at `*/15`): Executions still shows **"No results"** ([evidence](evidence/10-executions-empty-overnight.png)). Not one execution, successful or failed.

## Why it matters
A user sees "Active" and assumes their data is refreshing. There is no alert, failed-execution row or error to look at.

## Consequence for this exercise
All drift tests had to use manual runs (canvas ▶). The brief's question "what happens to the schedule afterwards?" is answered as: the schedule never ran at all, before or after drift.
