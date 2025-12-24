"""Discord embed and message templates for digest bot.

Small templating helpers to keep channel-specific formatting consistent.
"""
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime


def build_daily_embed(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return a Discord embed dict for the daily report summary."""
    title = f"Gold Standard — Daily Digest ({summary.get('hours',24)}h)"
    description = f"Queue: **{summary.get('queue_length',0)}** · Completed: **{summary.get('completed',0)}** · Corrections: **{summary.get('corrections',0)}**"
    embed = {
        "title": title,
        "description": description,
        "color": 0x2E86AB,
        "fields": [],
        "timestamp": datetime.utcnow().isoformat()
    }

    pm = summary.get("premarket") or {}
    if pm.get("bias"):
        v = f"**{pm.get('bias')}** — {pm.get('rationale','') }"
        if pm.get("notion_url"):
            v += f"\nNotion: {pm.get('notion_url')}"
        embed["fields"].append({"name": "Pre-Market", "value": v, "inline": False})

    # Add short samples (strings) if present
    if summary.get("recent_audits"):
        sample = "\n".join([f"id={a['id']} c={a['corrections']}" for a in summary['recent_audits'][:6]])
        embed["fields"].append({"name": "Recent audits", "value": sample or "None", "inline": False})

    if summary.get("flagged"):
        sample = "\n".join([f"{ (f"{f['document_path'].split('/')[-1]}" ) }" for f in summary['flagged'][:6]])
        embed["fields"].append({"name": "Flagged tasks", "value": sample or "None", "inline": False})

    if summary.get("errors"):
        sample = "\n".join([f"{e.get('document_path','?').split('/')[-1]}" for e in summary['errors'][:6]])
        embed["fields"].append({"name": "Errors", "value": sample or "None", "inline": False})

    return embed


def plain_daily_text(summary: Dict[str, Any]) -> str:
    lines = [f"Gold Standard — Daily Digest ({summary.get('hours',24)}h)"]
    lines.append("")
    pm = summary.get("premarket") or {}
    if pm.get("bias"):
        lines.append(f"Pre-Market: {pm.get('bias')} — {pm.get('rationale','')}")
        if pm.get("notion_url"):
            lines.append(f"Notion: {pm.get('notion_url')}")
        lines.append("")
    lines.append(f"Queue length: {summary.get('queue_length',0)}")
    lines.append(f"Completed: {summary.get('completed',0)}")
    lines.append(f"Sanitizer corrections: {summary.get('corrections',0)}")
    return "\n".join(lines)
