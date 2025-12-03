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
import sys
import json
import google.generativeai as genai

# Usage: python scripts/list_gemini_models.py <api_key>
if len(sys.argv) < 2:
    print('Usage: python scripts/list_gemini_models.py <API_KEY>')
    sys.exit(1)

api_key = sys.argv[1]
try:
    genai.configure(api_key=api_key)
    models = genai.list_models()
    output = []
    for m in models:
        # Some model objects are more complex; print name and any supported methods
        output.append({'name': getattr(m, 'name', getattr(m, 'model', None)), 'description': getattr(m, 'description', None)})
    print(json.dumps(output, indent=2))
except Exception as e:
    print('Error listing models:', e)
