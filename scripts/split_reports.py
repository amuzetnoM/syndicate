#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
"""
Split Reports Generator
Generates weekly rundowns and monthly/yearly reports using the existing QuantEngine and Strategist.
"""

import argparse
import datetime
import os
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv

try:
    from syndicate.utils.env_loader import load_env

    load_env(PROJECT_ROOT / ".env")
except Exception:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

import pandas as pd

from main import Config, Cortex, QuantEngine, Strategist, create_llm_provider, setup_logging


def ensure_dirs(config: Config):
    out = config.OUTPUT_DIR
    reports = os.path.join(out, "reports")
    charts = os.path.join(reports, "charts")
    os.makedirs(reports, exist_ok=True)
    os.makedirs(charts, exist_ok=True)
    return reports, charts


def write_report(
    report_path: str,
    markdown: str,
    doc_type: str = "reports",
    ai_processed: bool = False,
    report_type: str = None,
    period: str = None,
):
    """
    Write report to file and register in lifecycle system.
    Also registers in reports table for frequency tracking.
    Frontmatter is applied in final pass by run.py.

    Args:
        report_path: Path to write the report
        markdown: Report content
        doc_type: Document type for lifecycle
        ai_processed: Whether AI was used
        report_type: 'weekly', 'monthly', 'yearly' for frequency tracking
        period: Period string like '2025-12', '2025-W49', '2025'
    """
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    # Register in database for tracking
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from db_manager import Report, get_db

        db = get_db()

        # Register in lifecycle database
        lifecycle_status = "in_progress" if ai_processed else "draft"
        db.register_document(report_path, doc_type=doc_type, status=lifecycle_status)

        # Register in reports table for frequency tracking
        if report_type and period:
            report = Report(
                report_type=report_type,
                period=period,
                content=markdown[:500],  # Store summary only
                summary=f"Generated on {datetime.date.today()}",
                ai_enabled=ai_processed,
            )
            db.save_report(report, overwrite=False)
            print(f"[REPORT] Registered {report_type} report for period {period}")
    except Exception as e:
        print(f"[REPORT] DB registration failed: {e}")  # Log but don't fail


def monthly_yearly_report(config: Config, logger, model=None, dry_run=False, no_ai=False) -> str:
    """Generate a combined monthly and yearly report."""
    logger.info("Generating monthly and yearly report")
    reports_dir, charts_dir = ensure_dirs(config)

    # Use QuantEngine to fetch full year+ data for each asset
    q = QuantEngine(config, logger)

    # No intermediate results structure needed; we'll collect monthly and yearly tables

    # We'll iterate ASSETS directly to fetch dataframes
    from main import ASSETS

    asset_monthly: Dict[str, pd.DataFrame] = {}
    asset_yearly: Dict[str, pd.DataFrame] = {}
    for key, conf in ASSETS.items():
        try:
            df = q._fetch(conf["p"], conf["b"])
            if df is None or df.empty:
                logger.warning(f"No data for {key}")
                continue

            # Ensure index is a datetime index and sorted
            df = df.sort_index()
            df.index = pd.to_datetime(df.index)

            # Monthly aggregation (ME = Month End)
            monthly = df.resample("ME").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
            monthly["Return"] = monthly["Close"].pct_change() * 100

            # Yearly aggregation (YE = Year End)
            yearly = df.resample("YE").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
            yearly["Return"] = yearly["Close"].pct_change() * 100

            asset_monthly[key] = monthly
            asset_yearly[key] = yearly

            # Generate a chart for the monthly range (last 12 months)
            q._chart(key, df.tail(365))
            # copy chart to reports/charts
            src = os.path.join(config.CHARTS_DIR, f"{key}.png")
            dst = os.path.join(charts_dir, f"{key}_1y.png")
            try:
                if os.path.exists(src):
                    import shutil

                    shutil.copy2(src, dst)
            except Exception as e:
                logger.warning(f"Failed to copy chart {key}: {e}")

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")

    # Build markdown
    now = datetime.date.today()
    filename = f"monthly_yearly_report_{now}.md"
    path = os.path.join(reports_dir, filename)

    md = []
    md.append(f"# Monthly & Yearly Report - {now}\n")
    md.append("## Summary\n")
    # Aggregated summary: latest snapshot from QuantEngine.get_data
    snapshot = q.get_data()
    if snapshot is None:
        md.append("Data fetch failed - no snapshot available.\n")
    else:
        for k, v in snapshot.items():
            if not isinstance(v, dict):
                continue
            md.append(
                f"- **{k}**: Price: ${v.get('price')} | Change: {v.get('change')}% | RSI: {v.get('rsi')} | ADX: {v.get('adx')}\n"
            )

    # Monthly tables
    md.append("\n## Monthly Breakdowns\n")
    for key, table in asset_monthly.items():
        md.append(f"### {key}\n\n")
        md.append("| Month | Open | High | Low | Close | Return (%) |\n")
        md.append("|---|---:|---:|---:|---:|---:|\n")
        for idx, row in table.iterrows():
            md.append(
                f"| {idx.strftime('%Y-%m')} | {row['Open']:.2f} | {row['High']:.2f} | {row['Low']:.2f} | {row['Close']:.2f} | {row['Return']:.2f} |\n"
            )
        md.append("\n")

    # Yearly tables
    md.append("\n## Yearly Breakdowns\n")
    for key, table in asset_yearly.items():
        md.append(f"### {key}\n\n")
        md.append("| Year | Open | High | Low | Close | Return (%) |\n")
        md.append("|---|---:|---:|---:|---:|---:|\n")
        for idx, row in table.iterrows():
            md.append(
                f"| {idx.year} | {row['Open']:.2f} | {row['High']:.2f} | {row['Low']:.2f} | {row['Close']:.2f} | {row['Return']:.2f} |\n"
            )
        md.append("\n")

    # AI forecast: next year
    ai_success = False
    if not no_ai and model is not None:
        strategist = Strategist(
            config, logger, snapshot or {}, q.news, Cortex(config, logger).get_formatted_history(), model=model
        )
        prompt = strategist._build_prompt(
            gsr=snapshot.get("RATIOS", {}).get("GSR", "N/A"),
            vix_price=snapshot.get("VIX", {}).get("price", "N/A"),
            data_dump=strategist._format_data_summary(),
        )
        try:
            response = model.generate_content(prompt)
            response_text = response.text
            md.append("\n## AI Forecast for Next Year\n")
            md.append(response_text + "\n")
            ai_success = True
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            md.append("\n## AI Forecast for Next Year\n")
            md.append("*AI analysis pending - quota limit reached or error occurred.*\n")

    # Register both monthly AND yearly reports
    write_report(
        path,
        "\n".join(md),
        doc_type="reports",
        ai_processed=ai_success,
        report_type="monthly",
        period=f"{now.year:04d}-{now.month:02d}",
    )
    # Also register yearly
    try:
        from db_manager import Report, get_db

        db = get_db()
        yearly_report = Report(
            report_type="yearly",
            period=f"{now.year:04d}",
            content=f"Generated on {now}",
            summary=f"Yearly report for {now.year}",
            ai_enabled=ai_success,
        )
        db.save_report(yearly_report, overwrite=False)
    except Exception:
        pass
    logger.info(f"Monthly & Yearly report written to {path}")
    return path


def weekly_rundown(config: Config, logger, model=None, dry_run=False, no_ai=False) -> str:
    logger.info("Generating weekly rundown report")
    reports_dir, charts_dir = ensure_dirs(config)
    q = QuantEngine(config, logger)
    snapshot = q.get_data()
    if not snapshot:
        logger.warning("Data fetch failed - building a report with available data (may be missing entries)")
        snapshot = {}

    # produce weekly tactical guidance using Strategist with a short-horizon prompt
    md = []
    now = datetime.date.today()
    filename = f"weekly_rundown_{now}.md"
    report_path = os.path.join(reports_dir, filename)

    md.append(f"# Weekly Rundown - {now}\n")
    md.append("## Overview\n")
    for k, v in snapshot.items():
        if not isinstance(v, dict):
            continue
        md.append(
            f"- **{k}**: Price: ${v.get('price')} | Change: {v.get('change')}% | RSI: {v.get('rsi')} | ADX: {v.get('adx')}\n"
        )

    ai_success = False
    if not no_ai and model is not None:
        strategist = Strategist(
            config, logger, snapshot, q.news, Cortex(config, logger).get_formatted_history(), model=model
        )
        # Build a short weekly-focused prompt
        prompt = strategist._build_prompt(
            gsr=snapshot.get("RATIOS", {}).get("GSR", "N/A"),
            vix_price=snapshot.get("VIX", {}).get("price", "N/A"),
            data_dump=strategist._format_data_summary(),
        )
        try:
            response = model.generate_content(prompt)
            md.append("## AI Tactical Thesis\n")
            md.append(response.text + "\n")
            ai_success = True
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            md.append("## AI Tactical Thesis\n")
            md.append("*AI analysis pending - quota limit reached or error occurred.*\n")
    else:
        md.append("## Tactical Thesis (No AI Mode)\n")
        md.append("AI disabled; provide your own tactical notes or re-run with AI enabled for an automated thesis.\n")

    # Create short timeframe charts (1 week) for assets
    # For weekly charts, we use the full recent data for chart generation (which includes SMAs)
    # but then just copy the main chart rather than trying to generate a separate short-period chart
    for key, conf in __import__("main").ASSETS.items():
        try:
            # Use existing chart from QuantEngine (already generated during get_data)
            src = os.path.join(config.CHARTS_DIR, f"{key}.png")
            dst = os.path.join(charts_dir, f"{key}_week.png")
            if os.path.exists(src):
                import shutil

                shutil.copy2(src, dst)
                md.append(f"![{key} Weekly](charts/{key}_week.png)\n")
        except Exception:
            continue

    # Get ISO week for period tracking
    iso_cal = now.isocalendar()
    week_period = f"{iso_cal[0]:04d}-W{iso_cal[1]:02d}"

    write_report(
        report_path,
        "\n".join(md),
        doc_type="reports",
        ai_processed=ai_success,
        report_type="weekly",
        period=week_period,
    )
    logger.info(f"Weekly rundown written to {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Split Reports: generate weekly, monthly, and yearly reports")
    parser.add_argument("--mode", choices=["weekly", "monthly", "yearly", "all"], default="weekly")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files")
    parser.add_argument("--no-ai", action="store_true", help="Do not use AI")
    parser.add_argument("--gemini-key", default=None, help="Override API key")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    config = Config()
    if args.gemini_key:
        config.GEMINI_API_KEY = args.gemini_key

    logger = setup_logging(config)
    logger.setLevel(getattr(logger, args.log_level.upper(), "INFO"))

    # Configure AI (uses local LLM if available, falls back to Gemini)
    model_obj = None
    if not args.no_ai:
        try:
            model_obj = create_llm_provider(config, logger)
            if model_obj:
                logger.info(f"Using LLM provider: {model_obj.name}")
            else:
                logger.warning("No LLM provider available")
        except Exception as e:
            logger.error(f"Failed to configure LLM: {e}")
            model_obj = None

    if args.mode in ("monthly", "all", "yearly"):
        monthly_yearly_report(config, logger, model=model_obj, dry_run=args.dry_run, no_ai=args.no_ai)
    if args.mode in ("weekly", "all"):
        weekly_rundown(config, logger, model=model_obj, dry_run=args.dry_run, no_ai=args.no_ai)


if __name__ == "__main__":
    main()
