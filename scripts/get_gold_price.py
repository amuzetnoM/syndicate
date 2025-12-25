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
import yfinance as yf

# Compatibility shim for yfinance versions without `download`
if yf is not None and not hasattr(yf, "download"):
    def _yf_download(ticker, *args, **kwargs):
        t = yf.Ticker(ticker)
        return t.history(*args, **kwargs)

    yf.download = _yf_download

if __name__ == "__main__":
    df = yf.download("GC=F", period="5d", interval="1d", progress=False)
    if not df.empty:
        print(df["Close"].dropna().iloc[-1])
    else:
        print("No data")
