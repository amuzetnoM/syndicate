#!/usr/bin/env python3
from __future__ import annotations
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("DISCORD_BOT_TOKEN not set in .env")
    raise SystemExit(1)

headers = {"Authorization": f"Bot {TOKEN}"}

r = requests.get("https://discord.com/api/v10/users/@me/guilds", headers=headers)
r.raise_for_status()
for g in r.json():
    print(f"Guild: {g['id']} - {g['name']}")
    # list channels for this guild
    ch = requests.get(f"https://discord.com/api/v10/guilds/{g['id']}/channels", headers=headers)
    ch.raise_for_status()
    names = [c['name'] for c in ch.json() if c['type'] == 0]
    print("  Text channels:", ", ".join(names))
