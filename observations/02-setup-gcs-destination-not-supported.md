# Setup — Google Cloud Storage destination not available

| | |
|---|---|
| **Stage** | Pipeline setup |
| **Pipeline stopped?** | N/A — destination could not be configured |
| **Chatbot fix worked?** | N/A — chatbot confirmed GCS is not a supported destination |
| **Severity** | High — the brief's target architecture (S3 → GCS) cannot be built |

## What I did
Asked the AI Builder how to export the pipeline output to GCS.

## What happened
The AI Builder said GCS is not on the destination list and offered three workarounds: export to S3 then sync to GCS externally, download from Rhombus-managed storage and upload manually, or ask support to prioritise GCS.

## Decision
None of the workarounds tests Rhombus: option 1 depends on the S3 connector that already fails verification ([01](01-setup-s3-connector-verification.md)), and option 2 is a manual copy. I validated outputs **from Rhombus-managed storage** directly against the input and the seeded ground truth. `data-validation/validate.py` reads `gs://` paths (via `google-cloud-storage`), so it can be pointed at GCS without changes once a destination exists.
