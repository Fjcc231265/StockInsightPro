# StockInsightPro

Executive-style stock market analysis platform — **UI shell only** (mock data, no live APIs).

Built with Python, Streamlit, Plotly, and Pandas.

## Project structure

```
StockInsightPro/
├── stock_app.py              # Main entry point and page router
├── requirements.txt          # Python dependencies
├── README.md
├── .streamlit/
│   └── config.toml           # Theme and sidebar settings
├── components/
│   ├── sidebar.py            # Main menu + submenu navigation
│   ├── layout.py             # Header and panel wrappers
│   ├── cards.py              # KPI cards and TODO callouts
│   ├── charts.py             # Plotly chart builders
│   └── styles.py             # Executive dashboard CSS
├── pages/
│   ├── home.py               # Home Dashboard
│   ├── technical.py          # Technical Analysis views
│   ├── fundamental.py        # Fundamental Analysis views
│   ├── news.py               # News & Sentiment views
│   ├── portfolio.py          # Portfolio Watchlist views
│   ├── reports.py            # Reports placeholders
│   └── settings_page.py      # Settings views
├── assets/
│   ├── logo.png              # Master logo (source)
│   ├── logo_header.png       # Header size (128px)
│   └── logo_sidebar.png      # Sidebar size (48px)
├── data/
│   └── mock_data.py          # Synthetic data generators
└── utils/
    ├── constants.py          # Menu structure, colors, app name
    └── helpers.py            # Formatting helpers
```

## Navigation

| Main section | Submenus |
|---|---|
| Home Dashboard | — |
| Technical Analysis | Price chart, Moving averages, RSI, MACD, S/R, Volume, Candlesticks |
| Fundamental Analysis | Income, Balance, Cash flow, Valuation, Growth, Profitability, Debt |
| News & Sentiment | News, Sentiment, Risks, Catalysts, AI summary |
| Portfolio Watchlist | Add ticker, Favorites, Alerts, Compare |
| Reports | Technical, Fundamental, Thesis, Export |
| Settings | API keys, Data sources, Theme, Preferences |

## Quick start

### 1. Create a virtual environment (recommended)

```bash
cd ~/Documents/StockInsightPro
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
streamlit run stock_app.py
```

The app opens in your browser at `http://localhost:8501`.

## Branding

- **Wordmark (primary):** `assets/wordmark.png` — icon + **StockInsightPro** text (header & sidebar).
- **Icon-only:** `assets/logo.png` — fallback if wordmark is missing.
- **Theme:** Executive light dashboard — navy `#1e3a5f`, gold `#c9a227` accent (see `utils/constants.py`).
- **Header:** Wordmark on the left; current section title (e.g. Home Dashboard) on the right.
- Regenerate sizes after replacing artwork:
  ```bash
  sips -Z 200 assets/wordmark.png --out assets/wordmark_header.png
  sips -Z 120 assets/wordmark.png --out assets/wordmark_sidebar.png
  ```

## Development notes

- All financial values are **mock / placeholder** data.
- Look for `TODO` comments in code for future API, calculation, and persistence work.
- Do not use this app for real trading decisions.

## Roadmap (planned)

- [ ] Market data API integration
- [ ] Real technical indicator calculations
- [ ] SEC / fundamentals data providers
- [ ] News and NLP sentiment pipeline
- [ ] Persistent watchlist and alerts
- [ ] PDF report generation and export
