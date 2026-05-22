# Savepoint — May 22, 2026

Pause here. Resume from this milestone.

## Included in this version

- **UI:** Executive light theme, sidebar branding, 8 main sections + submenus
- **Options Intelligence:** Mock institutional dashboards (chain, OI, IV, gamma, max pain, flow, AI)
- **Architecture:** `ui/`, `services/`, `analytics/`, `ai/`, `models/`, `data/`
- **Alpha Vantage Phase A:** Live quotes, daily history, index overview via ETF proxies (`SPY`, `QQQ`, `DIA`, `IWM`, `VXX`) with mock fallback
- **Formatting:** Prices and percentages shown with **2 decimal places**
- **Secrets:** API key via `.env` (`ALPHA_VANTAGE_API_KEY`) — never commit `.env`

## Run later

```bash
cd ~/Documents/StockInsightPro
source .venv/bin/activate
streamlit run stock_app.py
```

Open http://localhost:8501/ — keep the terminal open while using the app.

If live data does not appear, confirm `.env` exists in this folder and restart Streamlit.

## Next session ideas

- Alpha Vantage Phase B (fundamentals, news)
- Real technical indicators from price history
- Options provider (Polygon / Tradier, etc.)
- Report export and watchlist persistence
