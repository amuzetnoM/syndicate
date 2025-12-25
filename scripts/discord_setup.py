#!/usr/bin/env python3
"""Helper: test and persist Discord webhook and Notion env vars.

Usage:
  scripts/discord_setup.py --webhook <url> [--persist-systemd] [--services <svc1,svc2>] [--notion-api <key> --notion-db <id>]

Actions:
- Tests a provided Discord webhook by sending a short test message.
- Writes `DISCORD_WEBHOOK_URL` to the project's `.env` file (idempotent).
- Optionally writes a systemd drop-in to persist the variable for the specified services and restarts them (requires sudo).
- Optionally stores Notion env vars (`NOTION_API_KEY`, `NOTION_DATABASE_ID`) into `.env`.
"""

import argparse
import os
import sys
import logging
from typing import List

try:
    import requests
except Exception:
    requests = None

ROOT = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(ROOT, ".env")

LOG = logging.getLogger("discord_setup")
logging.basicConfig(level=logging.INFO)


def write_env_var(key: str, value: str, env_path: str = ENV_PATH) -> None:
    """Idempotently write or update a key in .env file."""
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    updated = False
    new_lines = []
    for l in lines:
        if not l.strip() or l.lstrip().startswith("#"):
            new_lines.append(l)
            continue
        if l.split("=", 1)[0] == key:
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(l)

    if not updated:
        new_lines.append(f"{key}={value}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")

    LOG.info("Wrote %s to %s", key, env_path)


def test_webhook(url: str, message: str = "[Syndicate] Test message") -> bool:
    if requests is None:
        LOG.error("requests package is not installed. Install with: pip install requests")
        return False

    try:
        r = requests.post(url, json={"content": message}, timeout=10)
        # Discord returns 204 No Content for successful webhook posts
        if r.status_code in (200, 204):
            LOG.info("Webhook test succeeded (status=%s)", r.status_code)
            return True
        else:
            LOG.warning("Webhook test returned HTTP %s: %s", r.status_code, r.text[:200])
            return False
    except Exception as e:
        LOG.exception("Webhook test failed: %s", e)
        return False


def write_systemd_env(services: List[str], key: str, value: str) -> None:
    """Create a systemd drop-in override file for each service to persist env var.
    Requires privilege to write under /etc/systemd/system.
    """
    for svc in services:
        unit_dir = f"/etc/systemd/system/{svc}.d"
        override = os.path.join(unit_dir, "override.conf")
        os.system(f"sudo mkdir -p {unit_dir}")
        conf = f"[Service]\nEnvironment=\"{key}={value}\"\n"
        with open("/tmp/override.conf", "w", encoding="utf-8") as f:
            f.write(conf)
        os.system(f"sudo mv /tmp/override.conf {override}")
        LOG.info("Wrote override for %s -> %s", svc, override)

    # reload and restart
    os.system("sudo systemctl daemon-reload")
    for svc in services:
        os.system(f"sudo systemctl restart {svc}")
        LOG.info("Restarted %s", svc)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--webhook", required=False, help="Discord webhook URL to test and persist")
    p.add_argument("--persist-systemd", action="store_true", help="Persist the env var into systemd unit(s) via drop-in")
    p.add_argument("--services", help="Comma-separated list of services to apply systemd env to (default: syndicate-llm-worker.service,syndicate-premarket-watcher.service)")
    p.add_argument("--notion-api", help="NOTION_API_KEY to write to .env")
    p.add_argument("--notion-db", help="NOTION_DATABASE_ID to write to .env")
    p.add_argument("--no-test", action="store_true", help="Do not send a test message to webhook")

    args = p.parse_args(argv)

    services = [s.strip() for s in (args.services or "syndicate-llm-worker.service,syndicate-premarket-watcher.service").split(",")]

    if args.webhook:
        if not args.no_test:
            ok = test_webhook(args.webhook)
            if not ok:
                LOG.error("Webhook test failed; aborting write")
                sys.exit(2)
        write_env_var("DISCORD_WEBHOOK_URL", args.webhook)
        if args.persist_systemd:
            write_systemd_env(services, "DISCORD_WEBHOOK_URL", args.webhook)

    if args.notion_api:
        write_env_var("NOTION_API_KEY", args.notion_api)

    if args.notion_db:
        write_env_var("NOTION_DATABASE_ID", args.notion_db)

    LOG.info("Done.")


if __name__ == "__main__":
    main()
