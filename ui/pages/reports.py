"""Reports generation page."""

from __future__ import annotations

import streamlit as st

from services.report_summary_service import build_summary_report
from ui.components.page_router import render_submenu_page
from utils.constants import COLORS


def render(submenu: str) -> None:
    """Route reports submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "AI summary report": lambda: _ai_summary_report(ticker),
        "Export placeholder": lambda: _export_placeholder(ticker),
    }
    render_submenu_page(
        "Reports",
        submenu,
        handlers,
        default_handler=lambda: _ai_summary_report(ticker),
    )


def _ai_summary_report(ticker: str) -> None:
    """Render a combined AI-style directional report."""
    st.markdown(f"### AI Summary Report — {ticker}")
    st.caption("Wrap-up of technical analysis, fundamental health, and options intelligence.")

    with st.spinner("Building combined analysis..."):
        report = build_summary_report(ticker)

    _render_direction_badge(report["direction"], report["color"], report["score"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Technical takeaway", report["technical"]["label"].title(), _score_delta(report["technical"]["score"]))
    with col2:
        st.metric("Fundamental takeaway", report["fundamental"]["label"], _score_delta(report["fundamental"]["score"]))
    with col3:
        st.metric("Options takeaway", report["options"]["label"], _score_delta(report["options"]["score"]))

    st.markdown("#### Rationale")
    for rationale in report["rationales"]:
        st.markdown(f"- {rationale}")

    st.text_area("Report narrative", value=report["narrative"], height=360)

    with st.expander("Technical analysis used"):
        st.markdown(report["technical"]["analysis"])
    with st.expander("Fundamental analysis used"):
        st.markdown(report["fundamental"]["analysis"])

    st.caption("This report is analytical commentary only, not financial advice.")


def _render_direction_badge(direction: str, color: str, score: float) -> None:
    color_map = {
        "green": COLORS["positive"],
        "yellow": COLORS["accent"],
        "red": COLORS["negative"],
    }
    bg = color_map[color]
    st.markdown(
        f"""
        <div style="border-left: 8px solid {bg}; padding: 1rem; background: #ffffff; border-radius: 0.5rem; border-top: 1px solid #d8dee6; border-right: 1px solid #d8dee6; border-bottom: 1px solid #d8dee6;">
            <div style="font-size: 0.85rem; color: {COLORS["text_muted"]}; text-transform: uppercase;">Overall opinion</div>
            <div style="font-size: 1.6rem; font-weight: 700; color: {bg};">{direction}</div>
            <div style="color: {COLORS["neutral"]};">Composite score: {score:+.1f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _score_delta(score: float) -> str:
    return f"{score:+.1f}"


def _export_placeholder(ticker: str) -> None:
    """Show and download the complete AI summary report."""
    st.markdown(f"### Export AI Summary Report — {ticker}")
    st.caption("This is the complete report shown in AI summary report, prepared as plain text for export.")

    with st.spinner("Preparing export..."):
        report = build_summary_report(ticker)

    st.text_area("Export preview", value=report["narrative"], height=420)
    st.download_button(
        "Download report as .txt",
        data=report["narrative"],
        file_name=f"{ticker}_ai_summary_report.txt",
        mime="text/plain",
    )
