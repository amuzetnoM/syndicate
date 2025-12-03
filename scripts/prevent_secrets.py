#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__            
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____   
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \  
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/ 
#
# Gold Standard - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
"""
Pre-commit check to prevent committing .env files and obvious secret patterns.

This script checks the staged files for filenames like .env and simple patterns
like `GEMINI_API_KEY`, `API_KEY`, `aws_secret_access_key` and private key blocks.
It is intended to be run as a pre-commit hook and will exit non-zero if any
suspect content is found.
"""
import subprocess
import sys
import re

PATTERNS = [
    r"GEMINI_API_KEY",
    r"API_KEY",
    r"aws_secret_access_key",
    r"AIza[0-9A-Za-z\-_]{35}",  # common Google API key prefix
    r"-----BEGIN .* PRIVATE KEY-----",
    r"BEGIN RSA PRIVATE KEY",
]


def get_staged_files():
    try:
        out = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True)
        return [p.strip() for p in out.splitlines() if p.strip()]
    except subprocess.CalledProcessError:
        return []


def get_staged_content(path):
    try:
        return subprocess.check_output(["git", "show", f":{path}"], text=True, errors="ignore")
    except subprocess.CalledProcessError:
        return ""


def check_patterns(content):
    for p in PATTERNS:
        if re.search(p, content, re.I):
            return p
    return None


def main():
    staged = get_staged_files()
    suspect = []
    for f in staged:
        # Block filenames called .env or that end with .env
        if f == ".env" or f.endswith("/.env") or f.endswith(".env"):
            suspect.append((f, "filename: .env"))
            continue
        content = get_staged_content(f)
        if not content:
            continue
        p = check_patterns(content)
        if p:
            suspect.append((f, p))

    if suspect:
        print("ERROR: Prevent commit: detected candidate secrets in the staged files:")
        for fname, reason in suspect:
            print(f" - {fname}: {reason}")
        print("\nRemove secrets from staged files (e.g. move them into .env, ensure .env is in .gitignore),")
        print("and rotate any credentials if they have been committed previously.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
