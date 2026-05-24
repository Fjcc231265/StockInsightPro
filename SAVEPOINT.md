# Savepoint — May 24, 2026

Pause here. Resume from this milestone.

## Included in this version

- **Alpha Vantage Phase A (expanded):**
  - Live quotes (`GLOBAL_QUOTE`) + company overview (`OVERVIEW`) for name, sector, market cap
  - Price source labels and mock fallback only when API fails
  - Index dashboard: tries `INDEX_DATA` (SPX, COMP, DJI, RUT, VIX), falls back to ETF proxies with visible source
  - Top 10 gainers / top 10 losers via `TOP_GAINERS_LOSERS` (compact volume K/M/B)
- **Technical charts:**
  - Candlesticks (green/red), MA20 (blue), MA40 (red), volume, RSI(9)
  - Timeframes: Daily, Weekly, Monthly, Hourly (60min, regular hours only)
  - Weekly/monthly from resampled adjusted daily OHLC (split-safe)
  - Trading-bar axis (no calendar gaps) — aligned with broker-style charts
- **Written technical analysis (English):** Daily + weekly + monthly narrative under Technical Analysis → Price chart
- **UI:** Data source captions on home/sidebar/footer; 2-decimal formatting

## Run later

```bash
cd ~/Documents/StockInsightPro
source .venv/bin/activate
streamlit run stock_app.py
```

Open http://localhost:8501/ — keep the terminal open while using the app.

Ensure `.env` has `ALPHA_VANTAGE_API_KEY=<your_key>`. Restart Streamlit after changing the key.

## Git checkpoint

After saving, latest commit on `main` should reflect this session. Run `git log -1` to confirm.

## Next session ideas

- Alpha Vantage index entitlement (real indices vs ETF proxy)
- Phase B: fundamentals + news/sentiment
- Optional: OpenAI/LLM for richer written analysis from chart snapshots
- Options provider (Polygon / Tradier)
- Portfolio persistence, report export
