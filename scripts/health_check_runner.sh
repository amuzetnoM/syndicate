#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run health_check.py using the project's venv. On failure, attempt
# simple remediation and send an alert via the notifier module.

ENV_FILE="/mnt/disk/syndicate/.env"
PROJECT="/mnt/disk/syndicate"
VENV="$PROJECT/.venv/bin/activate"

# Source project env if available
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a && . "$ENV_FILE" && set +a
fi

# Activate venv
if [ -f "$VENV" ]; then
  # shellcheck disable=SC1091
  . "$VENV"
fi

python "$PROJECT/scripts/health_check.py"
EXIT_CODE=$?
if [ "$EXIT_CODE" -ne 0 ]; then
  # Try simple remediation: restart the scheduled run service and send an alert
  /bin/systemctl restart syndicate-run-once.service || true
  # Fire an alert via Python notifier (non-fatal if notifier fails)
  python - <<PY || true
from scripts.notifier import send_discord
send_discord('Syndicate healthcheck failed on host; attempted restart of run-once service')
PY
  exit "$EXIT_CODE"
fi

exit 0
