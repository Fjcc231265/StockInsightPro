"""Plotly chart builders for placeholder visualizations."""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots

from analytics.technical.engine import calculate_rsi, calculate_simple_moving_average
from utils.constants import COLORS


def _default_chart_height() -> int:
    try:
        from services.settings_service import get_user_settings

        return int(get_user_settings().get("chart_height_px", 400))
    except Exception:  # noqa: BLE001
        return 400


def _base_layout(title: str, height: int | None = None) -> dict:
    """Shared Plotly layout defaults."""
    resolved_height = height if height is not None else _default_chart_height()
    return dict(
        title=dict(text=title, font=dict(size=14, color=COLORS["primary"])),
        height=resolved_height,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor="white",
        plot_bgcolor="#fafbfc",
        font=dict(family="Inter, sans-serif", size=11),
        xaxis=dict(showgrid=True, gridcolor="#e8ecf0"),
        yaxis=dict(showgrid=True, gridcolor="#e8ecf0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )


def price_line_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Candlestick stock chart with moving averages, volume, and RSI(9)."""
    prices = _prepare_price_frame(df)
    x_values = _x_values_for_history(prices)
    volume_colors = [
        COLORS["positive"] if close >= open_ else COLORS["negative"]
        for close, open_ in zip(prices["Close"], prices["Open"])
    ]

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.7, 0.12, 0.18],
    )
    fig.add_trace(
        go.Candlestick(
            x=x_values,
            open=prices["Open"],
            high=prices["High"],
            low=prices["Low"],
            close=prices["Close"],
            name="Candles",
            increasing=dict(line=dict(color=COLORS["positive"]), fillcolor=COLORS["positive"]),
            decreasing=dict(line=dict(color=COLORS["negative"]), fillcolor=COLORS["negative"]),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=prices["MA20"],
            mode="lines",
            name="20 MA",
            line=dict(color="#1f77b4", width=2),
            connectgaps=True,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=prices["MA40"],
            mode="lines",
            name="40 MA",
            line=dict(color=COLORS["negative"], width=2),
            connectgaps=True,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=x_values,
            y=prices["Volume"],
            marker_color=volume_colors,
            name="Volume",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=prices["RSI9"],
            mode="lines",
            name="RSI(9)",
            line=dict(color="#6f42c1", width=2),
            connectgaps=True,
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["negative"], opacity=0.6, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["positive"], opacity=0.6, row=3, col=1)
    fig.update_layout(**_base_layout("", height=720))
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        hovermode="x unified",
        bargap=0.15,
    )
    fig.update_xaxes(type="category")
    fig.update_yaxes(title_text="Price", row=1, col=1, showgrid=True, gridcolor="#e8ecf0")
    fig.update_yaxes(title_text="Volume", row=2, col=1, showgrid=True, gridcolor="#e8ecf0")
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1, showgrid=True, gridcolor="#e8ecf0")
    return fig


def candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Stock chart alias retained for existing page calls."""
    return price_line_chart(df, ticker)


def volume_bar_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Volume bar chart."""
    colors = [
        COLORS["positive"] if c >= o else COLORS["negative"]
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig = go.Figure(
        go.Bar(x=df["Date"], y=df["Volume"], marker_color=colors, name="Volume")
    )
    fig.update_layout(**_base_layout(f"{ticker} — Volume (Mock)"))
    return fig


def rsi_chart(df: pd.DataFrame, ticker: str, time_period: int = 9) -> go.Figure:
    """RSI indicator chart with overbought/oversold zones."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["RSI"],
            mode="lines",
            name=f"RSI({time_period})",
            line=dict(color="#6f42c1", width=2),
        )
    )
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["negative"], annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["positive"], annotation_text="Oversold")
    fig.update_layout(**_base_layout(f"{ticker} — RSI({time_period})"))
    fig.update_layout(yaxis=dict(range=[0, 100]))
    return fig


def _prepare_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return OHLCV data with MA20, MA40, and RSI(9) columns."""
    prices = df.sort_values("Date").copy()
    prices["MA20"] = calculate_simple_moving_average(prices["Close"], 20)
    prices["MA40"] = calculate_simple_moving_average(prices["Close"], 40)
    prices["RSI9"] = calculate_rsi(prices["Close"], 9)
    return prices


def _x_values_for_history(prices: pd.DataFrame) -> pd.Series:
    """Return evenly spaced trading-bar labels for all chart timeframes."""
    if not pd.api.types.is_datetime64_any_dtype(prices["Date"]):
        return prices["Date"]

    has_intraday_times = (prices["Date"].dt.time != pd.Timestamp("00:00").time()).any()
    if has_intraday_times:
        return prices["Date"].dt.strftime("%Y-%m-%d %H:%M")

    median_spacing_days = prices["Date"].diff().dt.total_seconds().dropna().median() / 86_400
    if median_spacing_days >= 25:
        return prices["Date"].dt.strftime("%Y-%m")
    if median_spacing_days >= 6:
        return prices["Date"].dt.strftime("%Y-%m-%d")
    return prices["Date"].dt.strftime("%Y-%m-%d")


def macd_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """MACD line, signal, and histogram."""
    signal_column = "MACD Signal" if "MACD Signal" in df.columns else "Signal"
    histogram_column = "MACD Hist" if "MACD Hist" in df.columns else "Histogram"
    histogram_colors = [
        COLORS["positive"] if value >= 0 else COLORS["negative"]
        for value in df[histogram_column]
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD", line=dict(color=COLORS["secondary"])))
    fig.add_trace(go.Scatter(x=df["Date"], y=df[signal_column], name="Signal", line=dict(color=COLORS["accent"])))
    fig.add_trace(
        go.Bar(x=df["Date"], y=df[histogram_column], name="Histogram", marker_color=histogram_colors, opacity=0.55)
    )
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["neutral"], opacity=0.7)
    fig.update_layout(**_base_layout(f"{ticker} — MACD(12,26,9)"))
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=40, r=40, t=70, b=80),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
    )
    return fig


def sentiment_gauge(score: float) -> go.Figure:
    """Gauge chart for composite sentiment score."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title=dict(text="Composite Sentiment"),
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=COLORS["secondary"]),
                steps=[
                    dict(range=[0, 40], color="#fde8e8"),
                    dict(range=[40, 60], color="#f5f0e0"),
                    dict(range=[60, 100], color="#e0f2e8"),
                ],
            ),
        )
    )
    fig.update_layout(height=280, margin=dict(l=30, r=30, t=50, b=20))
    return fig


def comparison_bar_chart(df: pd.DataFrame, metric: str) -> go.Figure:
    """Grouped bar chart for stock comparison."""
    fig = go.Figure(go.Bar(x=df["Ticker"], y=df[metric], marker_color=COLORS["secondary"]))
    fig.update_layout(**_base_layout(f"Comparison — {metric} (Mock)", height=350))
    return fig


def open_interest_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Grouped bar chart for call/put open interest."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Strike"], y=df["Call OI"], name="Call OI", marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(x=df["Strike"], y=df["Put OI"], name="Put OI", marker_color=COLORS["negative"]))
    fig.update_layout(**_base_layout(f"{ticker} — Open Interest by Strike", height=380))
    fig.update_layout(
        barmode="group",
        margin=dict(l=40, r=40, t=85, b=45),
        title=dict(text=f"{ticker} — Open Interest by Strike", font=dict(size=14, color=COLORS["primary"]), y=0.96),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
    )
    return fig


def options_line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    """Reusable line chart for options intelligence indicators."""
    fig = go.Figure(
        go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode="lines+markers",
            name=y_col,
            line=dict(color=COLORS["secondary"], width=2),
            marker=dict(color=COLORS["accent"], size=6),
        )
    )
    fig.update_layout(**_base_layout(title, height=360))
    return fig


def gamma_exposure_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Bar chart for gamma exposure by strike."""
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in df["Gamma Exposure ($MM)"]]
    fig = go.Figure(
        go.Bar(
            x=df["Strike"],
            y=df["Gamma Exposure ($MM)"],
            name="Gamma Exposure",
            marker_color=colors,
        )
    )
    fig.update_layout(**_base_layout(f"{ticker} — Gamma Exposure", height=380))
    fig.add_hline(y=0, line_color=COLORS["neutral"], line_dash="dash")
    return fig


def max_pain_chart(df: pd.DataFrame, max_pain: float, ticker: str) -> go.Figure:
    """Open interest chart with a max-pain reference line."""
    fig = open_interest_chart(df, ticker)
    fig.update_layout(title=dict(text=f"{ticker} — Max Pain Map", font=dict(size=14, color=COLORS["primary"])))
    fig.add_vline(
        x=max_pain,
        line_dash="dash",
        line_color=COLORS["accent"],
        annotation_text=f"Max Pain ${max_pain:.2f}",
        annotation_position="top",
    )
    return fig
