"""Discord embed and message templates for digest bot.

Small templating helpers to keep channel-specific formatting consistent.
"""
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime


_FIELD_CHAR_LIMIT = 900  # keep under Discord 1024 limit with buffer for markdown


def _truncate(text: str, limit: int = _FIELD_CHAR_LIMIT) -> str:
    if not text:
        return "None"
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _join_bullets(items: List[str], max_items: int = 8) -> str:
    if not items:
        return "None"
    bullets = []
    for i, it in enumerate(items[:max_items]):
        bullets.append(f"- {it}")
    if len(items) > max_items:
        bullets.append(f"...and {len(items)-max_items} more")
    return "\n".join(bullets)


def build_daily_embed(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return a Discord embed dict for the daily report summary.

    Expects a structured `summary` produced by `daily_report.build_structured_report`.
    """
    title = f"Syndicate — LLM Daily Report ({summary.get('hours', 24)}h)"
    desc = f"Queue: **{summary.get('queue_length', 0)}** · Completed: **{summary.get('completed', 0)}** · Corrections: **{summary.get('corrections', 0)}**"

    embed = {
        "title": title,
        "description": desc,
        "color": 0x2E86AB,
        "fields": [],
        "timestamp": datetime.utcnow().isoformat(),
    }

    pm = summary.get("premarket") or {}
    if pm.get("bias"):
        v = f"**{pm.get('bias')}** — {pm.get('rationale','') }"
        if pm.get("notion_url"):
            v += f"\nNotion: {pm.get('notion_url')}"
        embed["fields"].append({"name": "Pre-Market", "value": _truncate(v), "inline": False})

    # Recent sanitizer audits (compact bullets)
    if summary.get("recent_audits"):
        items = [f"id={a['id']} t={a['task_id']} c={a['corrections']}" for a in summary['recent_audits']]
        embed["fields"].append({"name": "Recent sanitizer audits", "value": _truncate(_join_bullets(items)), "inline": False})

    # Flagged tasks (show filename only)
    if summary.get("flagged"):
        items = [f"{ (f.get('document_path') or '').split('/')[-1]}" for f in summary['flagged']]
        embed["fields"].append({"name": "Flagged tasks", "value": _truncate(_join_bullets(items)), "inline": False})

    # Errors
    if summary.get("errors"):
        items = [f"{ (e.get('document_path') or '').split('/')[-1]}" for e in summary['errors']]
        embed["fields"].append({"name": "Recent errors", "value": _truncate(_join_bullets(items)), "inline": False})

    # Footer-like metadata as a field to keep embed compact
    meta = f"Generated: {summary.get('generated_at', '')} · Window: {summary.get('hours',24)}h"
    embed["fields"].append({"name": "Metadata", "value": meta, "inline": False})

    return embed


def plain_daily_text(summary: Dict[str, Any]) -> str:
    lines = [f"Syndicate — LLM Daily Report ({summary.get('hours',24)}h)"]
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
    lines.append("")
    if summary.get('recent_audits'):
        lines.append("Recent sanitizer audits:")
        for a in summary['recent_audits']:
            lines.append(f"- id={a['id']} t={a['task_id']} c={a['corrections']}")
    if summary.get('flagged'):
        lines.append("")
        lines.append("Flagged tasks:")
        for f in summary['flagged']:
            lines.append(f"- { (f.get('document_path') or '').split('/')[-1] }")
    if summary.get('errors'):
        lines.append("")
        lines.append("Recent errors:")
        for e in summary['errors']:
            lines.append(f"- { (e.get('document_path') or '').split('/')[-1] }")

    return "\n".join(lines)
