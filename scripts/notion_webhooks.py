#!/usr/bin/env python3
"""Utilities to parse and normalize Notion webhook event payloads.

These helpers are small and intentionally dependency-free so they can be used
from webhook handlers or healthcheck scripts.
"""
from typing import Dict, Any


def extract_data_source_id(event: Dict[str, Any]) -> str | None:
    """Return the data_source_id when present in common webhook shapes.

    Notion 2025-09-03 sends `data.parent.data_source_id` for page events when
    the page belongs to a data source. Fall back to None when not present.
    """
    try:
        return event["data"]["parent"].get("data_source_id")
    except Exception:
        return None


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Return a normalized dictionary with top-level event type and data_source_id.

    Also provide a convenience hook to indicate whether this event should
    trigger a Notion re-sync for affected files (we currently only emit a
    boolean flag that callers can use to schedule a retry worker).
    """
    ds = extract_data_source_id(event) if isinstance(event, dict) else None
    ev_type = event.get("type")
    trigger_sync = False
    if ev_type in ("page.created", "page.updated", "data_source.content_updated", "data_source.schema_updated"):
        trigger_sync = True

    return {
        "type": ev_type,
        "entity": event.get("entity", {}),
        "data_source_id": ds,
        "trigger_sync": trigger_sync,
        "raw": event,
    }
