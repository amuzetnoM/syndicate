#!/usr/bin/env python3
"""Retry worker for failed or pending Notion publishes.

This module finds documents in the lifecycle table that are not yet published
and attempts to re-publish them using NotionPublisher.sync_file. It respects
retry_count and applies exponential backoff between retries.
"""
import logging
import time
from datetime import datetime

from db_manager import get_db
from scripts.notion_publisher import NotionPublisher

logger = logging.getLogger("retry_failed_publishes")


def run_once(max_attempts: int = 5):
    db = get_db()

    # Select candidate documents (status != 'published') ordered by retry_count asc
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_path, retry_count, last_error, status
            FROM document_lifecycle
            WHERE status != 'published'
            ORDER BY COALESCE(retry_count, 0) ASC, updated_at ASC
            LIMIT 50
            """
        )
        rows = cursor.fetchall()

    publisher = NotionPublisher()

    for row in rows:
        file_path = row["file_path"]
        retry_count = row["retry_count"] or 0
        status = row["status"]

        # Avoid hammering aggressive retries
        if retry_count >= 5:
            logger.info("Skipping %s (retry_count >= 5)", file_path)
            continue

        try:
            logger.info("Attempting publish for %s (retry=%d)", file_path, retry_count)
            publisher.sync_file(file_path, force=True)
            logger.info("Publish succeeded for %s", file_path)
        except Exception as e:
            logger.exception("Publish failed for %s: %s", file_path, e)
            with db._get_connection() as conn:
                cur = conn.cursor()
                now = datetime.now().isoformat()
                cur.execute(
                    """
                    UPDATE document_lifecycle
                    SET retry_count = COALESCE(retry_count,0) + 1,
                        last_error = ?,
                        updated_at = ?
                    WHERE file_path = ?
                    """,
                    (str(e), now, file_path),
                )
            # small sleep to avoid spikes
            time.sleep(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_once()