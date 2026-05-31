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
    "Market & Sector Analysis",
    "Technical Analysis",
    "Fundamental Analysis",
    "News & Sentiment",
    "Options Intelligence",
    "Portfolio Watchlist",
    "Reports",
    "Settings",
    "Education",
]

# Submenus keyed by main section
SUBMENUS = {
    "Market & Sector Analysis": [
        "Market overview",
        "Sector performance",
        "Sector rotation",
        "Breadth and movers",
    ],
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
        "Latest earnings release",
        "Earnings calendar",
        "Valuation ratios",
        "Growth metrics",
        "Profitability metrics",
        "Debt and liquidity",
    ],
    "News & Sentiment": [
        "Latest news",
        "Sentiment score",
        "Insider transactions",
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
        "AI Conclusions",
    ],
    "Portfolio Watchlist": [
        "Add ticker",
        "Track favorites",
        "Alerts placeholder",
        "Compare stocks",
    ],
    "Reports": [
        "AI summary report",
        "Export placeholder",
    ],
    "Settings": [
        "API keys placeholder",
        "Data source selection",
        "Theme options",
        "User preferences",
    ],
    "Education": [
        "Learning roadmap",
        "Rules playbook",
        "Stock P&L simulator",
        "Options P&L simulator",
        "Strategy payoff lab",
        "Market scenario lab",
    ],
}
