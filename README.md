# Rhombus AI — LLM Observability & QA Take-Home

Testing Rhombus AI as a customer would: an AI-built cleaning pipeline from a cloud source to a cloud destination, run on a schedule, then deliberately broken with schema and semantic drift.

**Short version:** the S3 → GCS scheduled journey could not be completed end to end. S3 verification failed with the platform's own generated policy, GCS is not an available destination, and an Active schedule never executed. Using direct upload and manual runs, I found that the AI-built pipeline **silently corrupted the clean baseline** (every amount ×100, every email wiped) while reporting success; that **switching the input file breaks the pipeline permanently**; and that a **chatbot fix re-introduced the corruption it had fixed earlier**. An external validation script caught every data problem; the platform caught none.

> TODO: **Demo video:** <add link>

---

## 1. Setup and how to run

```bash
git clone <this repo> && cd rhombus-ai-qa-takehome
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # pandas, boto3, google-cloud-storage
npm install && npx playwright install chromium
cp .env.example .env                     # fill in WORKFLOW_URL and API_* values
```

### Datasets — `/datasets/`
```bash
python datasets/generate_datasets.py     # deterministic (seed 42)
```
Generates `baseline.csv` (213 rows) with **planted, recorded defects** (exact duplicates, conflicting order_id duplicates, blanks, invalid emails, negative and non-numeric quantities, inconsistent country/status casing, `$` amounts, mixed date formats), the clean `ground_truth.csv`, `manifest.json` (every planted defect by order_id) and seven drifted files. Because the right answer is known for every row, validation checks *correctness*, not just "looks cleaner".

### Data validation — `/data-validation/`
```bash
# Pre-run drift guard: check a source file before the pipeline touches it
python data-validation/validate.py --case precheck-semantic-date-ddmm --input datasets/semantic-date-ddmm.csv

# Output check: compare a pipeline output with its input, the ground truth and the reference baseline
python data-validation/validate.py --case <name> --input datasets/baseline.csv \
    --output <rhombus-output.csv | gs://bucket/key> --baseline-output data-validation/outputs/baseline-reference.csv

# Determinism: same input run several times
python data-validation/validate.py --case <name> --input ... --output run1.csv --repeat-outputs run2.csv run3.csv
```
Paths can be local, `s3://` or `gs://`. Checks: schema, row counts, each cleaning rule, row-level comparison against ground truth (amounts, dates, day/month swaps), distribution shift against the baseline (cents detection), input profiling (DD/MM and cents detection before the run) and a content hash for determinism. Each run writes `data-validation/results/<case>.json` and exits non-zero on any FAIL.

### UI tests — `/ui-tests/` (Playwright)
Google blocks sign-in from automated browsers ("This browser or app may not be secure"), so the session is captured from a real Chrome window instead of logging in inside the test:
```bash
# 1. Real Chrome with a separate test profile and remote debugging; log in to Rhombus normally
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 \
    --user-data-dir="$HOME/rhombus-pw-profile" https://rhombusai.com
# 2. Copy that session (cookies + storage, no password) for Playwright
node scripts/save-auth.mjs
# 3. Run
npm run test:ui
```
Last run (6 Oct): **5 passed, 2 skipped** (40 s).

| Test | Asserts | Result |
|---|---|---|
| AI-built pipeline has the expected 7 steps | every node type and count on the canvas | Pass |
| Data Input lists the baseline dataset | dataset panel shows `baseline.csv` | Pass |
| 15-minute schedule is Active | schedule card shows Active and `*/15 * * * *` | Pass |
| Manual run completes and is logged | presses ▶, waits for a success log entry (polled, no sleeps) | Pass |
| BUG REPRO: Active schedule has no executions | Executions table shows "No results." | Pass (bug reproduced) |
| S3 source connection / GCS destination | — | Skipped (`fixme`, linked to observations 01/02) |

No fixed sleeps anywhere: every wait is an auto-retrying assertion. Icon-only buttons are located by their icon class (`svg.lucide-play`, `svg.lucide-history`). The viewport is 2200×1200 because the canvas only renders nodes inside the visible area. The bug-repro test asserts the bug *as observed*, so a broken selector fails loudly instead of being hidden behind `test.fail()`; once Rhombus fixes the schedule it fails and should be flipped to assert executions exist.

### API tests — `/api-tests/` (Playwright request)
```bash
npm run test:api
```
Endpoint and credentials come from a request captured in DevTools and live only in `.env` (git-ignored). The endpoint is `GET https://api.rhombusai.com/api/dataset/projects/all`, which returns the user's projects.

Last run (6 Oct): **3 passed, 1 skipped** (1 s).

| Test | Asserts | Result |
|---|---|---|
| Authenticated request | 200, JSON content type, body parses, contains `gat-pipeline` | Pass |
| **NEGATIVE:** no auth header | 401/403 **and** the body does not contain the project name | Pass |
| **NEGATIVE:** invalid Bearer token | 401/403 | Pass |
| **NEGATIVE:** non-existent id | 403/404, not 200/5xx | Skipped (this endpoint has no id in its path) |

The Bearer token is a short-lived Auth0 JWT; refresh it from DevTools if the authenticated test starts returning 401.

---

## 2. Observations summary

### Drift cases

| Case | Change | Pipeline stopped? | Chatbot fix worked? | Severity |
|---|---|---|---|---|
| [schema-type-change](observations/schema-type-change.md) | `quantity` int → `"3 units"` | Yes, at node 2 — caused by the dataset swap, not the drift | N/A | Critical (blocked) |
| [schema-rename-column](observations/schema-rename-column.md) | `amount_usd` → `order_amount` | Not reached (swap bug) | N/A | High (blocked) |
| [schema-drop-column](observations/schema-drop-column.md) | drop `country` | Not reached | N/A | High (blocked) |
| [schema-add-column](observations/schema-add-column.md) | add `discount_code` | Not reached | N/A | Medium (blocked) |
| [schema-combined](observations/schema-combined.md) | all four | Not reached | N/A | High (blocked) |
| [semantic-dollars-to-cents](observations/semantic-dollars-to-cents.md) | amounts ×100 | Not reached as drift — **but the platform produced this exact corruption on the clean baseline** | — | Critical |
| [semantic-date-ddmm](observations/semantic-date-ddmm.md) | MM/DD → DD/MM | Not reached | N/A | Critical (blocked) |

Every drift file is flagged by the pre-run guard (the baseline passes with 0 FAIL/WARN), so a check outside the pipeline would have stopped each one before publication.

### Platform findings

| Finding | Pipeline stopped? | Chatbot fix worked? | Severity |
|---|---|---|---|
| [01 S3 connector rejects its own generated policy](observations/01-setup-s3-connector-verification.md) | Yes (setup) | No — misdiagnosed twice | Critical |
| [02 GCS destination not available](observations/02-setup-gcs-destination-not-supported.md) | N/A | N/A | High |
| [03 "Trim" step corrupts emails and amounts on baseline](observations/03-baseline-text-cleanup-corrupts-email-and-amount.md) | **No (success)** | **Yes** — verified | Critical |
| [04 Active schedule never executes](observations/04-schedule-never-executes.md) | Never runs | Not tested | Critical |
| [05 Switching input dataset breaks the pipeline](observations/05-dataset-swap-breaks-pipeline.md) | Yes, any file | Partially | Critical |
| [06 Chatbot fix re-introduces the corruption](observations/06-chatbot-fix-regression.md) | **No (success)** | **No** | Critical |
| [07 Same run logged as success and failure](observations/07-logs-report-success-and-failure.md) | — | — | High |

### Top three findings
1. **Silent corruption with a green status.** Asked to "trim whitespace", the AI Builder chose a punctuation-stripping step and applied it to `email` and `amount_usd`: every amount became ×100 and every email was blanked, on clean data, with a successful run. The preview even highlighted the changed cells, but nothing warned the user.
2. **AI fixes are not verified.** The chatbot fixed #1 correctly when given only the symptom. But a later fix for an unrelated crash rebuilt the pipeline and brought the corruption back, now also stripping hyphens from order IDs and minus signs from negative quantities — again with a green run and no diff shown.
3. **Run status can't be trusted.** An Active schedule never executed: zero executions over a whole night of `*/15` runs, not even failed ones; a single run was logged as both successful and failed; and the pipeline fails permanently once the input dataset is switched, even back to the original file. A pipeline that can't accept a new file and a schedule that silently doesn't run means the core ETL use case doesn't work yet.

---

## 3. Usability feedback


The most enjoyable part was the AI Builder itself: describing the cleaning rules in plain English and getting a seven-step pipeline in under a minute was impressive, and the generated Custom-node code was readable and mostly correct (de-duplication, country and status standardisation and date parsing all validated exactly). The orange highlighting of changed cells and the ability to open any node's preview and code made root-causing the corruption fast — that transparency is genuinely useful.

The frustrating part was trust. Every serious problem I hit came with a success signal or no signal at all: a green corrupting run, an "Active" schedule that never ran, contradictory log lines. The setup connectors also cost hours — the S3 form generated a policy that its own verification then rejected, and the chatbot pointed at a CloudFormation stack I had never created. Suggestions: show a diff and re-run a quick row-level check after every AI change; warn when a step changes the type or meaning of a column it wasn't asked to touch (e.g. a "trim" step altering numeric or email values); surface schedule misfires as visible failed executions; keep node configuration stable when the input dataset changes; and make the chatbot aware of which setup path the user actually took.

---

## 4. Decisions and limitations
- **Direct upload instead of S3, Rhombus storage instead of GCS, manual instead of scheduled runs** — each forced by a documented blocker (01, 02, 04). The validation script supports `s3://` and `gs://` so it works unchanged on the intended architecture.
- **Drift cases not executed on the platform** — after finding the dataset-swap bug (05, confirmed with a control run of the unchanged original file), any drift run would have measured the swap bug, not the drift. Expected platform behaviour is documented per case from reading the generated code; the pre-run guard results are real.
- **UI run test** relies on the log panel starting empty on page load (verified: 0 success entries before a run), so a match can only come from the run it triggered. A version that counted entries before and after was attempted, but a floating panel that opens on ▶ intercepts clicks inconsistently; tightening this is the next step.
- **Determinism / dashboard bonus** — not done: the schedule never produced repeated runs, and time went to isolating root causes.
- **Time:** 18 hours across 3 days

## Repository layout
```
datasets/          generator, baseline, ground truth, manifest, 7 drifted files
data-validation/   validate.py, outputs/ (every Rhombus output), results/ (JSON per run)
ui-tests/          Playwright UI journey
api-tests/         Playwright API tests (positive + negative)
observations/      one file per finding / drift case; evidence/ screenshots, logs, generated code
```
