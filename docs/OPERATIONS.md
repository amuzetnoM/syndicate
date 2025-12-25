# Syndicate Operations

This document summarizes operations for the offloaded executor and model cleanup utilities.

## Offloaded Executor (GGUF-only fast tasks)

- Script: `scripts/offloaded_executor.py`
- Purpose: Run short, low-latency LLM tasks locally using GGUF models (via `llama-cpp-python` or native `pyvdb`).
- Invocation:
  - Single run: `python scripts/offloaded_executor.py --once`
  - Service: `systemctl start syndicate-offloaded-executor.service`
- Env vars:
  - `OFFLOAD_POLL_S` (default: 30) — interval between polling cycles
  - `OFFLOAD_MAX_TASKS` (default: 5) — tasks per cycle
  - `OFFLOAD_MAX_ATTEMPTS` (default: 3) — per-task retry count
  - `KEEP_LOCAL_MODELS` — comma-separated model names to prefer/keep (e.g., `phi3-mini,fast`)
  - `AUTO_PRUNE_DAYS` — if set (>0), offloaded executor will check for unused models not used in N days
  - `AUTO_PRUNE_CONFIRM` — if set (`1`/`true`), the auto-prune will actually delete (move) model files; otherwise dry-run only
  - `AUTO_PRUNE_MIN_KEEP` — minimum number of models to retain when pruning

### Robustness
- The offloaded executor attempts to load a preferred model and will retry up to 3 times with backoff.
- If a task fails due to a model error, the executor will try a model swap (reload an alternative model) and retry the task once before marking it for retry/failure.
- Model usage is recorded in the DB (`model_usage` table) for safe pruning decisions.

## Model Cleanup

- Script: `scripts/cleanup_models.py`
- Purpose: List GGUF models and delete unused models to reclaim disk space.
- Usage:
  - Dry-run (default): `python scripts/cleanup_models.py`
  - Confirm deletion: `python scripts/cleanup_models.py --confirm`
  - Prune based on DB last-used: `python scripts/cleanup_models.py --prune-days 30 --min-keep 1 --confirm`
- Env vars:
  - `KEEP_LOCAL_MODELS` — comma-separated model name hints to keep

### Safety
- Deletion is dry-run by default; `--confirm` must be passed for actual deletion.
- When `--prune-days` is specified, the script consults the DB (`model_usage`) and only considers models not used within the threshold.
- When `AUTO_PRUNE_CONFIRM=1` is set, the offloaded executor may move models to `.model_trash/` as a safe-step for manual review.

## Tips
- Always run `python scripts/cleanup_models.py` first to inspect candidates.
- If you rely on certain models, set `KEEP_LOCAL_MODELS` to include names or paths to keep.

