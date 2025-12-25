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
Syndicate Project Initialization.

Creates project structure and template files for a new Syndicate installation.
"""

from pathlib import Path

ENV_TEMPLATE = """# Syndicate Configuration
# ==========================

# Required: Google Gemini API Key
# Get yours free at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Notion Integration
# NOTION_API_KEY=your_notion_api_key
# NOTION_DATABASE_ID=your_database_id
"""

CORTEX_TEMPLATE = """{
  "model_version": "3.4.0",
  "session_id": null,
  "last_updated": null,
  "predictions": [],
  "grades": [],
  "win_streak": 0,
  "loss_streak": 0,
  "total_predictions": 0,
  "correct_predictions": 0,
  "accuracy": 0.0
}
"""

GITIGNORE_TEMPLATE = """# Syndicate
.env
*.pyc
__pycache__/
venv/
venv312/
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
.ruff_cache/
.coverage
coverage.xml
*.db

# Output (optional - uncomment to ignore generated reports)
# output/
"""


def initialize_project(target_dir: Path = None):
    """
    Initialize a new Syndicate project in the target directory.

    Creates:
    - Directory structure (output, data, scripts)
    - Template files (.env.template, cortex_memory.template.json)
    - .gitignore

    Args:
        target_dir: Target directory (defaults to current directory)
    """
    target = target_dir or Path.cwd()

    print(f"\n[INIT] Initializing Syndicate in: {target}\n")

    # Create directories
    directories = [
        "output",
        "output/reports",
        "output/charts",
        "data",
        "scripts",
    ]

    for dir_name in directories:
        dir_path = target / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  [DIR] Created: {dir_name}/")

    # Create .env.template
    env_template_path = target / ".env.template"
    if not env_template_path.exists():
        env_template_path.write_text(ENV_TEMPLATE)
        print("  [FILE] Created: .env.template")

    # Create .env if it doesn't exist
    env_path = target / ".env"
    if not env_path.exists():
        env_path.write_text(ENV_TEMPLATE)
        print("  [FILE] Created: .env (please add your API keys)")

    # Create cortex_memory.template.json
    cortex_template_path = target / "cortex_memory.template.json"
    if not cortex_template_path.exists():
        cortex_template_path.write_text(CORTEX_TEMPLATE)
        print("  [FILE] Created: cortex_memory.template.json")

    # Create cortex_memory.json if it doesn't exist
    cortex_path = target / "cortex_memory.json"
    if not cortex_path.exists():
        cortex_path.write_text(CORTEX_TEMPLATE)
        print("  [FILE] Created: cortex_memory.json")

    # Create .gitignore
    gitignore_path = target / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(GITIGNORE_TEMPLATE)
        print("  [FILE] Created: .gitignore")

    print("\n" + "=" * 60)
    print("  GOLD STANDARD INITIALIZED")
    print("=" * 60)
    print("""
  Next steps:

  1. Add your Gemini API key to .env:
     GEMINI_API_KEY=your_key_here

  2. (Optional) Add Notion credentials for auto-publishing

  3. Run Syndicate:
     gost --once         # Single analysis run
     gost                # Start autonomous daemon
     gost --interactive  # Interactive menu

  Documentation: https://github.com/amuzetnoM/gold_standard
""")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    initialize_project()
