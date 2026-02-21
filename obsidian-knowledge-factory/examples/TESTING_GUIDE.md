# Testing Guide (RED/GREEN/REFACTOR)

## Test files prepared
- `D:/vivi/vi/inbox/TEST_01_noisy_mixed.md`
- `D:/vivi/vi/inbox/TEST_02_similar_partA.md`
- `D:/vivi/vi/inbox/TEST_03_similar_partB.md`

## 1) GREEN: basic run
Run once and verify pipeline summary:

```bash
python engine/main.py --once --config engine/config.yaml --env-file engine/.env
```

Expected:
- `scanned` >= 3
- `succeeded` > 0
- `archived` > 0 after successful writes

## 2) REFACTOR: dedupe/merge behavior
Focus on `TEST_02` and `TEST_03` (high similarity pair).

Expected:
- One note may be merged instead of duplicated.
- Summary should show `merged` >= 1 when similarity threshold triggers.

## 3) RED: error path validation
Temporarily set wrong API key in `.env`.

Expected:
- Run fails with clear API error.
- Error logs written under `<vault>/logs/`.
- Source files stay available for retry.
