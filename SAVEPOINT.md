# Savepoint — May 24, 2026

Pause here. Resume from this milestone.

## Included in this version

- **Alpha Vantage Phase A (expanded):**
  - Live quotes (`GLOBAL_QUOTE`) + company overview (`OVERVIEW`)
  - Price source labels and mock fallback only when API fails
  - Index dashboard: tries `INDEX_DATA`, falls back to ETF proxies with visible source
  - Top 10 gainers / top 10 losers via `TOP_GAINERS_LOSERS` (compact volume K/M/B)
- **Technical charts:**
  - Candlesticks (green/red), MA20 (blue), MA40 (red), volume, RSI(9)
  - Timeframes: Daily, Weekly, Monthly, Hourly (60min, regular hours only)
  - Weekly/monthly from resampled adjusted daily OHLC (split-safe)
  - Trading-bar axis (no calendar gaps)
  - Written technical analysis (English) with generate button and trend badge (green/yellow/red)
- **Custom ticker input:**
  - Sidebar accepts arbitrary symbols (for example `DCTH`)
  - Suggested symbol dropdown shown only on Home Dashboard when no custom symbol is typed
- **Fundamental Analysis:**
  - Alpha Vantage P&L, Balance Sheet, and Cash Flow (Annual/Quarterly)
  - Period-over-period percentage variation
  - P&L margin analysis
  - Written financial health analysis with generate button and health badge (green/yellow/red)
- **Home Dashboard:**
  - Company overview block above chart
  - Recent news toggle with green/yellow/red sentiment badges
- **News & Sentiment:**
  - Latest news tab with live Alpha Vantage `NEWS_SENTIMENT`
  - Green/yellow/red sentiment summary tiles and per-headline badges
- **UI:** Data source captions; 2-decimal formatting

## Run later

```bash
cd ~/Documents/StockInsightPro
source .venv/bin/activate
streamlit run stock_app.py
```

Open http://localhost:8501/ — keep the terminal open while using the app.

Ensure `.env` has `ALPHA_VANTAGE_API_KEY=<your_key>`. Restart Streamlit after changing the key.

## Git checkpoint

Latest commit on `main`: `git log -1` to confirm.

## Next session ideas

- Alpha Vantage index entitlement (real indices vs ETF proxy)
- Options provider (Polygon / Tradier)
- Portfolio persistence and report export
- Optional LLM for richer narrative analysis