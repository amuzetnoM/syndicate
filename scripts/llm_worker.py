#!/usr/bin/env python3
"""LLM Worker

Polls the `llm_tasks` table and processes pending tasks using the configured LLM provider.
"""
import os
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db_manager import get_db
from main import Config, create_llm_provider, setup_logging
from scripts.frontmatter import add_frontmatter, detect_type

# Optional Notion publish
try:
    from scripts.notion_publisher import NotionPublisher
    NOTION_AVAILABLE = True
except Exception:
    NOTION_AVAILABLE = False

LOG = logging.getLogger("llm_worker")

# Config via env
WORKER_CONCURRENCY = int(os.environ.get("LLM_WORKER_CONCURRENCY", "2"))
POLL_INTERVAL = float(os.environ.get("LLM_WORKER_POLL_INTERVAL", "5"))
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
TASK_BATCH_SIZE = int(os.environ.get("LLM_TASK_BATCH_SIZE", str(WORKER_CONCURRENCY)))
GOLD_LLM_TIMEOUT = int(os.environ.get("GOLDSTANDARD_LLM_TIMEOUT", "120"))


def process_task(task: dict, cfg: Config) -> None:
    db = get_db()
    task_id = task["id"]
    doc_path = task["document_path"]
    prompt = task.get("prompt", "")

    LOG.info("Processing LLM task id=%s doc=%s", task_id, doc_path)

    attempts = task.get("attempts", 0) + 1

    try:
        task_type = task.get("task_type", "generate")

        if task_type == "generate":
            provider = create_llm_provider(cfg, LOG)
            if not provider:
                raise RuntimeError("No LLM provider available")

            # Perform generation with a local timeout (worker enforces wall time)
            # Provider-level timeouts are respected (OLLAMA_TIMEOUT_S, etc.).
            resp = provider.generate_content(prompt)
            text = getattr(resp, "text", str(resp))

            # Write content to file and update frontmatter
            try:
                # Overwrite file body with AI output and set frontmatter (auto-publish may occur)
                doc_type = detect_type(os.path.basename(doc_path))
                final_content = add_frontmatter(text, os.path.basename(doc_path), doc_type=doc_type, ai_processed=True)
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
            except Exception as e:
                LOG.exception("Failed to write generated content to %s: %s", doc_path, e)
                db.update_llm_task_result(task_id, "failed", response=None, error=str(e), attempts=attempts)
                return

            # Attempt Notion publish if available
            if NOTION_AVAILABLE:
                try:
                    pub = NotionPublisher()
                    pub.sync_file(doc_path)
                except Exception as e:
                    LOG.warning("Notion publish failed (task=%s): %s", task_id, e)

            db.update_llm_task_result(task_id, "completed", response=text, error=None, attempts=attempts)
            LOG.info("Task %s completed (generate)", task_id)

        elif task_type == "insights":
            # Perform insights extraction and save action insights
            try:
                from scripts.insights_engine import InsightsExtractor

                content = ""
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()

                provider = create_llm_provider(cfg, LOG)
                extractor = InsightsExtractor(cfg, LOG, model=provider)
                actions = extractor.extract_actions(content, os.path.basename(doc_path))

                if actions:
                    db.save_action_insights(actions)

                db.update_llm_task_result(task_id, "completed", response=f"insights:{len(actions)}", error=None, attempts=attempts)
                LOG.info("Task %s completed (insights) - actions=%s", task_id, len(actions))
            except Exception as e:
                LOG.exception("Insights extraction failed for %s: %s", doc_path, e)
                if attempts >= MAX_RETRIES:
                    db.update_llm_task_result(task_id, "failed", response=None, error=str(e), attempts=attempts)
                else:
                    db.update_llm_task_result(task_id, "pending", response=None, error=str(e), attempts=attempts)
                return

        else:
            LOG.warning("Unknown task_type '%s' for task %s", task_type, task_id)
            db.update_llm_task_result(task_id, "failed", response=None, error=f"unknown task_type {task_type}", attempts=attempts)
            return
    except Exception as e:
        LOG.exception("LLM generation failed for task %s: %s", task_id, e)
        if attempts >= MAX_RETRIES:
            db.update_llm_task_result(task_id, "failed", response=None, error=str(e), attempts=attempts)
        else:
            # Re-queue (backoff could be added)
            db.update_llm_task_result(task_id, "pending", response=None, error=str(e), attempts=attempts)

def main():
    cfg = Config()
    setup_logging(cfg)
    LOG.setLevel(os.environ.get("LLM_WORKER_LOG_LEVEL", "INFO"))

    db = get_db()

    LOG.info("LLM Worker starting (concurrency=%s poll_interval=%s)" % (WORKER_CONCURRENCY, POLL_INTERVAL))

    executor = ThreadPoolExecutor(max_workers=WORKER_CONCURRENCY)

    try:
        while True:
            # Claim a batch of tasks (up to TASK_BATCH_SIZE)
            tasks = db.claim_llm_tasks(limit=TASK_BATCH_SIZE)
            if not tasks:
                time.sleep(POLL_INTERVAL)
                continue

            futures = {executor.submit(process_task, t, cfg): t for t in tasks}
            # Wait for current batch to finish but do not block polling forever
            for fut in as_completed(futures):
                try:
                    fut.result(timeout=GOLD_LLM_TIMEOUT)
                except Exception as e:
                    t = futures[fut]
                    LOG.exception("Task %s raised: %s", t.get("id"), e)

    except KeyboardInterrupt:
        LOG.info("LLM Worker stopping (KeyboardInterrupt)")
    finally:
        executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
