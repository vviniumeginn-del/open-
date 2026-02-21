# Error Playbook

## json_parse_error
- Cause: model output not valid JSON.
- Action: write raw payload to `inbox/Failed` and continue.

## schema_validation_error
- Cause: missing required fields.
- Action: reject note, store payload, keep source unarchived if no note succeeds.

## merge_empty_result
- Cause: merge logic produced empty content.
- Action: fallback to side-by-side append, never overwrite with empty.

## write_error
- Cause: filesystem permission/path issues.
- Action: log to `logs/write_error.log`, keep source for retry.
