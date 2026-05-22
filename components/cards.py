"""Reusable metric and info card components."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from utils.helpers import change_color_class, format_currency, format_percent


def render_metric_card(
    label: str, value: str, delta: Optional[str] = None, delta_value: float = 0
) -> None:
    """Render a styled KPI metric card."""
    delta_class = change_color_class(delta_value)
    delta_html = ""
    if delta:
        delta_html = f'<div class="delta {delta_class}">{delta}</div>'

    st.markdown(
        f"""
        <div class="sip-metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quote_cards(quote: dict) -> None:
    """Render standard quote summary KPI row."""
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("Last Price", format_currency(quote["price"]), delta_value=0)
    with cols[1]:
        render_metric_card(
            "Day Change",
            format_percent(quote["change_pct"]),
            delta=format_currency(quote["change_abs"]),
            delta_value=quote["change_pct"],
        )
    with cols[2]:
        render_metric_card("Volume", f"{quote['volume']:,}", delta_value=0)
    with cols[3]:
        render_metric_card("Sector", quote["sector"], delta_value=0)


def render_todo_callout(message: str) -> None:
    """Display a visible TODO placeholder for future implementation."""
    st.markdown(f'<div class="sip-todo"><strong>TODO:</strong> {message}</div>', unsafe_allow_html=True)


def render_section_header(title: str, subtitle: str = "") -> None:
    """Render page section title with optional subtitle."""
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
