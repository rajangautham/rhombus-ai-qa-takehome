# Logs report the same run as both successful and failed

| | |
|---|---|
| **Severity** | High — any monitoring or alerting built on these events is unreliable |

## Evidence
```
09:15:22 PM  Pipeline execution started.
09:15:23 PM  Pipeline execution completed successfully.
09:15:23 PM  Pipeline failed at orders_no_exact_dupes: DataFrameDuplicateRowRemover.transform() missing 1 required positional argument: 'columns'
```
One run, one second, two contradictory terminal states. The canvas showed every node after Data Input in red.

## Related
Combined with [04](04-schedule-never-executes.md) (Active schedule, no executions) and [03](03-baseline-text-cleanup-corrupts-email-and-amount.md) (corrupting run marked success), the platform's run status was wrong or missing in three different ways during this exercise.
