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
            provider_hint = task.get("provider_hint")

            # Honor provider_hint when present
            if provider_hint == "gemini_only":
                try:
                    from main import GeminiProvider

                    gem = GeminiProvider(cfg.GEMINI_MODEL)
                    resp = gem.generate_content(prompt)
                    text = getattr(resp, "text", str(resp))
                except Exception as e:
                    LOG.exception("Gemini-only generation failed for task %s: %s", task_id, e)
                    # Mark task failed (no fallback per 'gemini_only' contract)
                    db.update_llm_task_result(task_id, "failed", response=None, error=str(e), attempts=attempts)
                    return

            elif provider_hint in ("ollama_slow", "ollama_offload"):
                try:
                    # Use the digest-bot Ollama provider which accepts a custom timeout
                    from digest_bot.llm.ollama import OllamaProvider as OllamaSlowProvider

                    ol = OllamaSlowProvider(host=cfg.OLLAMA_HOST, model=cfg.OLLAMA_MODEL, timeout=None)
                    resp = ol.generate(prompt)
                    text = getattr(resp, "text", str(resp))
                except Exception as e:
                    LOG.exception("Ollama slow generation failed for task %s: %s", task_id, e)
                    if attempts >= MAX_RETRIES:
                        db.update_llm_task_result(task_id, "failed", response=None, error=str(e), attempts=attempts)
                    else:
                        db.update_llm_task_result(task_id, "pending", response=None, error=str(e), attempts=attempts)
                    return

            else:
                provider = create_llm_provider(cfg, LOG)
                if not provider:
                    raise RuntimeError("No LLM provider available")

                # Perform generation with a local timeout (worker enforces wall time)
                # Provider-level timeouts are respected (OLLAMA_TIMEOUT_S, etc.).
                resp = provider.generate_content(prompt)
                text = getattr(resp, "text", str(resp))

            # Sanitize generated content using canonical values embedded in prompt
            def _parse_canonical_from_prompt(p: str):
                import re
                values = {}
                # Look for lines like: '* GOLD: $4362.4'
                for m in re.finditer(r"\*\s*([A-Z]+)\s*:\s*\$?([0-9\.,]+)", p):
                    asset = m.group(1).upper()
                    num = float(m.group(2).replace(",", ""))
                    values[asset] = num
                return values

            def _sanitize_text(text: str, canonical: dict):
                import re
                corrected = 0
                notes = []

                def _replace_price(match, canonical_price):
                    nonlocal corrected
                    full = match.group(0)
                    # Tolerate trailing punctuation (e.g., '98.72.'), strip commas, and sanitize
                    import re as _re
                    raw = match.group(2).replace(",", "")
                    clean = _re.sub(r"[^0-9.\-]", "", raw)
                    try:
                        num = float(clean)
                    except Exception:
                        # If we cannot parse, skip replacement
                        return full

                    if abs((num - canonical_price) / canonical_price) > 0.05:
                        corrected += 1
                        notes.append(f"Replaced {num} with {canonical_price}")
                        return match.group(1) + str(canonical_price)
                    return full

                # For each canonical asset, replace nearby mentions (handle plural and different casings)
                import re

                for asset, price in canonical.items():
                    # Build likely token variants so 'YIELD' matches 'Yields' in natural text
                    variants = {asset, asset.lower(), asset.title(), asset.capitalize()}
                    if asset.upper() == "YIELD":
                        variants.update({"Yields", "Yield", "YIELD"})

                    for tok in variants:
                        # Replace patterns like 'Gold: $1234' or 'gold ... $1234' where the token appears
                        text = re.sub(rf"(\b{re.escape(tok)}\b[^\n]{{0,40}}\$)([0-9\.,]+)", lambda m, p=price: _replace_price(m, p), text, flags=re.IGNORECASE)

                        # Replace 'Current Gold Price: $1234' pattern for variants too
                        text = re.sub(rf"(Current\s+{re.escape(tok)}\s+Price:\s*\$)\s*[0-9\.,]+", lambda m, p=price: m.group(1) + str(p), text, flags=re.IGNORECASE)

                return text, corrected, notes

            canonical = _parse_canonical_from_prompt(prompt or "")
            sanitized_text = text
            corrections = 0
            notes = []
            if canonical:
                sanitized_text, corrections, notes = _sanitize_text(text, canonical)

            # Persist audit if corrections occurred
            try:
                if corrections:
                    try:
                        # Increment Prometheus counter if available
                        from syndicate.metrics.server import METRICS

                        if "llm_sanitizer_corrections_total" in METRICS:
                            METRICS["llm_sanitizer_corrections_total"].inc(corrections)
                    except Exception:
                        pass

                    db.save_llm_sanitizer_audit(task_id, corrections, "; ".join(notes))

            except Exception:
                LOG.exception("Failed to write sanitizer audit for task %s", task_id)

            # If many corrections, flag the report for review instead of auto-publishing
            flag_threshold = int(os.environ.get("LLM_SANITIZER_FLAG_THRESHOLD", "2"))
            if corrections >= flag_threshold:
                LOG.warning("Task %s sanitized with %s corrections - flagging for review", task_id, corrections)
                try:
                    # Write sanitized content to file, but mark status as flagged
                    doc_type = detect_type(os.path.basename(doc_path))
                    final_content = add_frontmatter(sanitized_text, os.path.basename(doc_path), doc_type=doc_type, ai_processed=True)
                    # add a flag in frontmatter
                    final_content = final_content.replace("\n---\n", "\n---\nsanitizer_flagged: true\n", 1)
                    with open(doc_path, "w", encoding="utf-8") as f:
                        f.write(final_content)
                    db.update_llm_task_result(task_id, "flagged", response=sanitized_text, error=None, attempts=attempts)
                except Exception as e:
                    LOG.exception("Failed to write flagged report for %s: %s", doc_path, e)
                    db.update_llm_task_result(task_id, "failed", response=None, error=str(e), attempts=attempts)
                return

            # Write sanitized content to file and update frontmatter
            try:
                doc_type = detect_type(os.path.basename(doc_path))
                final_content = add_frontmatter(sanitized_text, os.path.basename(doc_path), doc_type=doc_type, ai_processed=True)
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

            db.update_llm_task_result(task_id, "completed", response=sanitized_text, error=None, attempts=attempts)
            LOG.info("Task %s completed (generate) - corrections=%s", task_id, corrections)

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
    # Metrics integration (optional)
    try:
        from syndicate.metrics.server import METRICS
    except Exception:
        METRICS = None

    # Initialize
    cfg = Config()
    setup_logging(cfg)
    LOG.setLevel(os.environ.get("LLM_WORKER_LOG_LEVEL", "INFO"))

    db = get_db()

    # Set running metric
    if METRICS is not None:
        try:
            METRICS["llm_worker_running"].set(1)
        except Exception:
            pass

    LOG.info("LLM Worker starting (concurrency=%s poll_interval=%s)" % (WORKER_CONCURRENCY, POLL_INTERVAL))

    executor = ThreadPoolExecutor(max_workers=WORKER_CONCURRENCY)

    try:
        while True:
            # Update queue length metric
            if METRICS is not None:
                try:
                    METRICS["llm_queue_length"].set(db.get_llm_queue_length() or 0)
                except Exception:
                    pass

            # Claim a batch of tasks (up to TASK_BATCH_SIZE)
            tasks = db.claim_llm_tasks(limit=TASK_BATCH_SIZE)
            if not tasks:
                time.sleep(POLL_INTERVAL)
                continue

            # Update processing metric
            if METRICS is not None:
                try:
                    METRICS["llm_tasks_processing"].set(len(tasks))
                except Exception:
                    pass

            futures = {executor.submit(process_task, t, cfg): t for t in tasks}
            # Wait for current batch to finish but do not block polling forever
            for fut in as_completed(futures):
                try:
                    fut.result(timeout=GOLD_LLM_TIMEOUT)
                except Exception as e:
                    t = futures[fut]
                    LOG.exception("Task %s raised: %s", t.get("id"), e)

            # Reset processing metric
            if METRICS is not None:
                try:
                    METRICS["llm_tasks_processing"].set(0)
                except Exception:
                    pass

    except KeyboardInterrupt:
        LOG.info("LLM Worker stopping (KeyboardInterrupt)")
    finally:
        if METRICS is not None:
            try:
                METRICS["llm_worker_running"].set(0)
                METRICS["llm_tasks_processing"].set(0)
            except Exception:
                pass
        executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
