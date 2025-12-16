#!/usr/bin/env bash
set -euo pipefail

# End-to-end smoke test: generate reports, extract actions, run executor to completion
# Usage: ./scripts/e2e_smoke.sh

VENV=${VENV:-$HOME/worxpace/.venv_ai}
if [[ ! -d "$VENV" ]]; then
  echo "Virtualenv $VENV not found. Activate the AI venv first or set VENV env var." >&2
  exit 1
fi

source "$VENV/bin/activate"

export LLM_PROVIDER=${LLM_PROVIDER:-ollama}
export OLLAMA_TIMEOUT_S=${OLLAMA_TIMEOUT_S:-120}
export LLM_MAX_RETRIES=${LLM_MAX_RETRIES:-3}

# Disable Notion publishing for this test
python - <<'PY'
from db_manager import get_db
print('Disabling Notion publishing for E2E test')
get_db().set_notion_publishing_enabled(False)
get_db().set_task_execution_enabled(True)
get_db().set_insights_extraction_enabled(True)
PY

# Run one complete analysis (creates reports, extracts actions)
python run.py --once

# Run executor daemon once to drain queue
python scripts/executor_daemon.py --once

# Run verification checks
python scripts/verify_completion.py

# Done
echo "E2E smoke test completed successfully (no publishing)."
