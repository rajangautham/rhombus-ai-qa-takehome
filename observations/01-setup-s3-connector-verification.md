# Setup — Amazon S3 source connector fails verification

| | |
|---|---|
| **Stage** | Pipeline setup (step 1 of the customer journey) |
| **Pipeline stopped?** | Yes — connection could not be created |
| **Chatbot fix worked?** | No (two attempts, both misdiagnosed) |
| **Severity** | Critical — blocks the first step of the intended S3 → GCS journey |

## What I did
1. Created bucket `gautham-rhombus` (ap-southeast-2, general purpose, SSE-S3, Block Public Access on, versioning on) and uploaded `baseline.csv` ([evidence](evidence/01-s3-bucket-with-baseline.png)).
2. In Rhombus: **+ → Third Party Sources → Amazon S3**. Bucket `gautham-rhombus`, region ap-southeast-2, folder/path blank.
3. The form generated a bucket policy granting `s3:GetBucketLocation`, `s3:ListBucket` and `s3:GetObject` to two Rhombus-owned roles in account `730335216038`. I applied it **unchanged** as the bucket policy.

## Expected
Verification succeeds once the generated policy is applied.

## What happened
Verification consistently failed:

```
AWS denied Rhombus AI access to the whole bucket. Folder / path is blank. The required whole-bucket
read-only policy is missing or does not match this bucket. Apply the generated policy, or update the
CloudFormation stack so SourceBucket matches the connection form and SourcePrefix is empty, then retry.
```

Ruled out, one at a time:

| Possible cause | Check | Result |
|---|---|---|
| Policy not saved / truncated | Compared saved policy with generated policy | Identical (AWS only normalises single-item arrays to strings) |
| Stale role ARNs | Re-created the connection, compared generated policy | Same role ARNs |
| KMS encryption | Object properties | SSE-S3 |
| Region mismatch | Bucket list | ap-southeast-2 on both sides |
| Block Public Access | Policy names specific principals, so it is non-public | Not applicable |
| Explicit Deny / SCP | Personal account, no Organization, policy contains only Rhombus statements | None |
| Propagation delay | Retried after several minutes | Same error |

## Chatbot
- **Answer 1:** update a CloudFormation stack — none exists, because I used the bucket-policy route the form itself offered.
- **Answer 2:** "attach the generated policy to the IAM role/user Rhombus uses". Not possible: the policy is a resource policy (it has a `Principal`), and the roles live in Rhombus's AWS account. It also suggested loosening account-level Block Public Access, which would not affect a non-public policy and weakens security for no benefit.
- When given full details it produced a reasonable generic checklist; every item was already ruled out.

## Outcome / workaround
Reported to Rhombus by email. Continued with **+ → Add new file** (direct upload) so the rest of the exercise could proceed. The validation script still accepts `s3://` paths, so it works unchanged once the connector does.

## Question for the team (not tested)
The generated policy trusts shared production roles with no condition (such as an external ID or source-account condition) tying access to my Rhombus account. Is anything preventing another Rhombus user from configuring a connection to a bucket they know the name of? I did not attempt this, and would not against anyone else's bucket.
