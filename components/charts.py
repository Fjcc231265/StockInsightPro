"""Plotly chart builders for placeholder visualizations."""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from utils.constants import COLORS


def _base_layout(title: str, height: int = 400) -> dict:
    """Shared Plotly layout defaults."""
    return dict(
        title=dict(text=title, font=dict(size=14, color=COLORS["primary"])),
        height=height,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor="white",
        plot_bgcolor="#fafbfc",
        font=dict(family="Inter, sans-serif", size=11),
        xaxis=dict(showgrid=True, gridcolor="#e8ecf0"),
        yaxis=dict(showgrid=True, gridcolor="#e8ecf0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )


def price_line_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Line chart for closing prices."""
    # TODO: Add interactive range selectors and real-time updates
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines",
            name="Close",
            line=dict(color=COLORS["secondary"], width=2),
        )
    )
    fig.update_layout(**_base_layout(f"{ticker} — Price Chart (Mock)"))
    return fig


def candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Candlestick OHLC chart."""
    # TODO: Overlay technical indicators on candlestick chart
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["Date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
            )
        ]
    )
    fig.update_layout(**_base_layout(f"{ticker} — Candlestick (Mock)", height=450))
    fig.update_layout(xaxis_rangeslider_visible=False)
    return fig


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


def rsi_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """RSI indicator chart with overbought/oversold zones."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df["Date"], y=df["RSI"], mode="lines", name="RSI", line=dict(color=COLORS["accent"]))
    )
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["negative"], annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["positive"], annotation_text="Oversold")
    fig.update_layout(**_base_layout(f"{ticker} — RSI (Mock)"))
    fig.update_layout(yaxis=dict(range=[0, 100]))
    return fig


def macd_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """MACD line, signal, and histogram."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD", line=dict(color=COLORS["secondary"])))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal", line=dict(color=COLORS["accent"])))
    fig.add_trace(
        go.Bar(x=df["Date"], y=df["Histogram"], name="Histogram", marker_color=COLORS["neutral"], opacity=0.5)
    )
    fig.update_layout(**_base_layout(f"{ticker} — MACD (Mock)"))
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
