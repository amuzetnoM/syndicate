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
import json
import sys


def _main():
    # Try to import old google.generativeai, fallback to compat shim or new google.genai
    try:
        import google.generativeai as genai  # type: ignore
        _GENAI_TYPE = "old"
    except Exception:
        try:
            from scripts import genai_compat as genai  # type: ignore

            _GENAI_TYPE = "compat"
        except Exception:
            try:
                import google.genai as genai_new  # type: ignore

                _GENAI_TYPE = "new"
            except Exception:
                print("No Google GenAI client available. Install google-genai or provide a compat shim.")
                sys.exit(1)

    # Usage: python scripts/list_gemini_models.py <api_key>
    if len(sys.argv) < 2:
        print("Usage: python scripts/list_gemini_models.py <API_KEY>")
        sys.exit(1)

    api_key = sys.argv[1]
    try:
        if _GENAI_TYPE in ("old", "compat"):
            genai.configure(api_key=api_key)
            models = genai.list_models() if hasattr(genai, "list_models") else []
        else:
            client = genai_new.Client(api_key=api_key)
            models = client.models.list()

        output = []
        for m in models:
            # Some model objects are more complex; print name and any supported methods
            output.append(
                {"name": getattr(m, "name", getattr(m, "model", None)), "description": getattr(m, "description", None)}
            )
        print(json.dumps(output, indent=2))
    except Exception as e:
        print("Error listing models:", e)


if __name__ == "__main__":
    _main()
