#!/usr/bin/env python3
"""Deploy the Grafana dashboard JSON to Grafana if credentials are present."""
from __future__ import annotations

import os
import json
import logging
import requests

LOG = logging.getLogger("deploy_grafana")

GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")
DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "..", "deploy", "grafana", "syndicate_llm_dashboard.json")


def deploy():
    if not GRAFANA_URL or not GRAFANA_API_KEY:
        LOG.info("Grafana credentials not set; skipping dashboard deploy")
        return False

    with open(DASHBOARD_PATH, "r") as f:
        payload = json.load(f)

    url = f"{GRAFANA_URL.rstrip('/')}/api/dashboards/db"
    headers = {"Authorization": f"Bearer {GRAFANA_API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        LOG.info("Deployed dashboard to Grafana: %s", r.json())
        return True
    except Exception as e:
        LOG.exception("Failed to deploy Grafana dashboard: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Deploying dashboard...")
    deploy()
