# Switching the input dataset permanently breaks the pipeline

| | |
|---|---|
| **Stage** | Introducing drift (replacing the input file) |
| **Pipeline stopped?** | **Yes** — fails at node 2 for *any* file, including the original |
| **Chatbot fix worked?** | Partially — pipeline ran again, but output was corrupted (see [06](06-chatbot-fix-regression.md)) |
| **Severity** | Critical — a pipeline that cannot accept a new input file cannot run as ETL |

## What I did
With S3 blocked ([01](01-setup-s3-connector-verification.md)), the way to change the input is the Data Input node: **Upload Data → From Device**, then pick the file under **Select Dataset**.
1. Uploaded `schema-type-change.csv`, selected it, ran ▶.
2. **Control:** re-selected the original `baseline.csv` (which had run successfully) and ran ▶.

## Expected
Step 1: either success or a failure that refers to `quantity`. Step 2: success, identical to the baseline.

## What happened
Both runs fail at the **first transformation node**, and every node after it turns red ([evidence](evidence/09-dataset-swap-all-nodes-fail.png)):

```
09:14:21 PM  Pipeline failed at orders_no_exact_dupes: DataFrameDuplicateRowRemover.transform() missing 1 required positional argument: 'columns'
09:15:22 PM  Pipeline execution started.
09:15:23 PM  Pipeline execution completed successfully.
09:15:23 PM  Pipeline failed at orders_no_exact_dupes: DataFrameDuplicateRowRemover.transform() missing 1 required positional argument: 'columns'
```

The control proves the cause is the **swap itself**, not the data: the original file, unchanged, now fails too. The de-duplication node appears to lose its column configuration when the selected dataset changes.

## Logs
- The error is a raw Python signature error. It names neither the column nor what changed, so a user cannot act on it.
- The same run is logged as both **"completed successfully"** and **"failed"** in the same second — see [07](07-logs-report-success-and-failure.md).

## Chatbot
Given the error and the context ("after I switched the input dataset and switched back"), it reported *"Applied 6 transformations: Remove Duplicates: columns: [order_id, customer_name, country, status, amount_usd, quantity, +2 more] · keep:"* (note the empty `keep:` value).

The next morning, after another switch, the chatbot stated the cause itself: the dataset switch **cleared the parameters of all four standard transformer nodes** (`orders_no_exact_dupes`, `orders_deduped`, `orders_title_case`, `orders_status_lower`), which must be re-applied after every input change, or switching avoided altogether ([evidence](evidence/11-chatbot-confirms-dataset-switch-wipes-params.png)). That confirms the control-test diagnosis in the platform's own words, and shows it is systematic behaviour rather than a one-off glitch.

## Did the fix work?
The pipeline ran green on `baseline.csv` again, **but** the output was corrupted — see [06](06-chatbot-fix-regression.md). Re-selecting `schema-type-change.csv` afterwards failed again with the same error.

## Consequence for drift testing
Every drift run dies at node 2 before the drifted data reaches any step that would react to it. So the schema and semantic drift questions could not be answered by running the canvas pipeline; see the drift files for what *was* established.
