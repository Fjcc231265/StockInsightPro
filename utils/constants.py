"""Application-wide constants for StockInsightPro."""

APP_NAME = "StockInsightPro"
APP_TAGLINE = "Executive Stock Market Analysis Platform"
DEFAULT_TICKER = "AAPL"

# Executive dashboard color palette
COLORS = {
    "primary": "#1e3a5f",
    "secondary": "#2d6a9f",
    "accent": "#c9a227",
    "positive": "#1a7f4e",
    "negative": "#c0392b",
    "neutral": "#5a6a7a",
    "background": "#f4f6f9",
    "card_border": "#d8dee6",
    "text_muted": "#6b7c93",
}

# Main navigation sections (sidebar)
MAIN_SECTIONS = [
    "Home Dashboard",
    "Technical Analysis",
    "Fundamental Analysis",
    "News & Sentiment",
    "Options Intelligence",
    "Portfolio Watchlist",
    "Reports",
    "Settings",
]

# Submenus keyed by main section
SUBMENUS = {
    "Technical Analysis": [
        "Price chart",
        "Moving averages",
        "RSI",
        "MACD",
        "Support and resistance",
        "Volume analysis",
        "Candlestick patterns",
    ],
    "Fundamental Analysis": [
        "Income statement",
        "Balance sheet",
        "Cash flow statement",
        "Valuation ratios",
        "Growth metrics",
        "Profitability metrics",
        "Debt and liquidity",
    ],
    "News & Sentiment": [
        "Latest news",
        "Sentiment score",
        "Key risks",
        "Market catalysts",
        "AI summary placeholder",
    ],
    "Options Intelligence": [
        "Options Chain Viewer",
        "Open Interest Analysis",
        "Put/Call Ratio",
        "Implied Volatility",
        "IV Rank",
        "Gamma Exposure",
        "Max Pain",
        "Dealer Positioning",
        "Options Flow",
        "AI Conclusions",
    ],
    "Portfolio Watchlist": [
        "Add ticker",
        "Track favorites",
        "Alerts placeholder",
        "Compare stocks",
    ],
    "Reports": [
        "Generate technical report",
        "Generate fundamental report",
        "Combined investment thesis",
        "Export placeholder",
    ],
    "Settings": [
        "API keys placeholder",
        "Data source selection",
        "Theme options",
        "User preferences",
    ],
}
