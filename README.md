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
├── ui/
│   ├── components/           # Streamlit-only reusable UI components
│   │   ├── sidebar.py        # Main menu + submenu navigation
│   │   ├── page_router.py    # Reusable submenu dispatch helpers
│   │   ├── layout.py         # Header and panel wrappers
│   │   ├── cards.py          # KPI cards and TODO callouts
│   │   ├── charts.py         # Plotly chart builders
│   │   └── styles.py         # Executive dashboard CSS
│   └── pages/                # One file per main menu section
│       ├── home.py
│       ├── technical.py
│       ├── fundamental.py
│       ├── news.py
│       ├── options_intelligence.py
│       ├── portfolio.py
│       ├── reports.py
│       └── settings.py
├── services/                 # Facades used by UI; future API/database adapters
├── analytics/                # UI-free market analytics engines
│   ├── technical/
│   ├── fundamental/
│   └── options/
├── ai/                       # AI interpretation and future agent orchestration
├── models/                   # Shared domain dataclasses/types
├── assets/
│   ├── logo.png              # Master logo (source)
│   ├── logo_header.png       # Header size (128px)
│   └── logo_sidebar.png      # Sidebar size (48px)
├── data/
│   └── mock_data.py          # Synthetic data provider only
└── utils/
    ├── constants.py          # Menu structure, colors, app name
    └── helpers.py            # Formatting helpers
```

## Architecture

StockInsightPro is separated into clear layers:

- `ui/` contains Streamlit rendering only.
- `services/` is the boundary the UI calls for data and analytics outputs.
- `analytics/` will contain calculation engines such as indicators, valuation scoring, IV rank, gamma exposure, and max pain.
- `ai/` will contain AI interpretation and future agent workflows.
- `models/` contains shared domain types that should remain framework-free.
- `data/` currently contains mock providers and will later hold adapters or repositories.

The UI should not import `data/mock_data.py` directly. It should call `services/` or `ai/`, which can later be backed by real APIs, databases, or advanced analytics engines.

## Navigation

| Main section | Submenus |
|---|---|
| Home Dashboard | — |
| Technical Analysis | Price chart, Moving averages, RSI, MACD, S/R, Volume, Candlesticks |
| Fundamental Analysis | Income, Balance, Cash flow, Valuation, Growth, Profitability, Debt |
| News & Sentiment | News, Sentiment, Risks, Catalysts, AI summary |
| Options Intelligence | Chain, OI, Put/Call, IV, IV Rank, Gamma, Max Pain, Dealer Positioning, Flow, AI |
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

## Alpha Vantage Setup

Phase A supports live market data through Alpha Vantage for:

- Quote cards
- Daily price charts
- Technical price charts
- Market overview using ETF/index proxies: `SPY`, `QQQ`, `DIA`, `IWM`, `VXX`

Create a local `.env` file:

```bash
cd ~/Documents/StockInsightPro
cp .env.example .env
```

Then edit `.env` so it contains your real key:

```bash
ALPHA_VANTAGE_API_KEY=your_real_key_here
```

Restart Streamlit after changing `.env`:

```bash
streamlit run stock_app.py
```

If the key is missing, invalid, rate-limited, or the provider fails, the app falls back to mock data automatically.

## Branding

- **Wordmark (primary):** `assets/wordmark.png` — icon + **StockInsightPro** text.
- **Icon-only:** `assets/logo.png` — fallback if wordmark is missing.
- **Theme:** Executive light dashboard — navy `#1e3a5f`, gold `#c9a227` accent (see `utils/constants.py`).
- **Header:** Current section title only; app branding lives in the sidebar.
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
