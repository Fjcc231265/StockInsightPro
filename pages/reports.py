"""Reports generation page (placeholders)."""

import streamlit as st

from components.cards import render_section_header, render_todo_callout


def render(submenu: str) -> None:
    """Route reports submenu."""
    ticker = st.session_state.selected_ticker
    render_section_header("Reports", f"View: {submenu}")
    st.divider()

    handlers = {
        "Generate technical report": lambda: _technical_report(ticker),
        "Generate fundamental report": lambda: _fundamental_report(ticker),
        "Combined investment thesis": lambda: _investment_thesis(ticker),
        "Export placeholder": _export_placeholder,
    }
    handlers.get(submenu, lambda: _technical_report(ticker))()


def _technical_report(ticker: str) -> None:
    """Technical report preview placeholder."""
    st.markdown(f"### Technical Report — {ticker}")
    st.text_area(
        "Report preview (mock)",
        value=(
            f"TECHNICAL ANALYSIS REPORT — {ticker}\n"
            "─────────────────────────────────\n"
            "Trend: Bullish (mock)\n"
            "RSI: 58 — Neutral\n"
            "MACD: Positive crossover (mock)\n"
            "Support: $175 | Resistance: $195\n"
            "\n"
            "DISCLAIMER: Placeholder content. Not investment advice."
        ),
        height=220,
    )
    if st.button("Generate PDF (Mock)", key="tech_pdf"):
        st.info("PDF export not implemented.")
    render_todo_callout("Auto-generate technical report from live indicators.")


def _fundamental_report(ticker: str) -> None:
    """Fundamental report preview placeholder."""
    st.markdown(f"### Fundamental Report — {ticker}")
    st.text_area(
        "Report preview (mock)",
        value=(
            f"FUNDAMENTAL ANALYSIS REPORT — {ticker}\n"
            "────────────────────────────────────\n"
            "Valuation: Fairly valued vs sector (mock)\n"
            "Growth: Revenue +12% YoY (mock)\n"
            "Profitability: Above sector average (mock)\n"
            "Balance sheet: Moderate leverage (mock)\n"
            "\n"
            "DISCLAIMER: Placeholder content. Not investment advice."
        ),
        height=220,
    )
    render_todo_callout("Pull fundamentals into templated PDF/HTML reports.")


def _investment_thesis(ticker: str) -> None:
    """Combined thesis placeholder."""
    st.markdown(f"### Combined Investment Thesis — {ticker}")
    st.markdown(
        """
        **Bull Case (Mock)**
        - Strong technical momentum and institutional accumulation
        - Solid earnings growth and margin expansion

        **Bear Case (Mock)**
        - Valuation premium vs historical averages
        - Macro sensitivity and sector headwinds

        **Conclusion (Mock)**
        Maintain **Hold** rating — awaiting Q2 catalysts.
        """
    )
    render_todo_callout("Merge technical + fundamental signals into scored thesis.")


def _export_placeholder() -> None:
    """Export options placeholder."""
    st.markdown("**Export Options**")
    st.selectbox("Format", ["PDF", "HTML", "CSV", "Excel"], key="export_fmt")
    st.multiselect("Include sections", ["Technical", "Fundamental", "News", "Watchlist"], default=["Technical", "Fundamental"])
    if st.button("Export Report (Mock)"):
        st.success("Export queued (mock) — file would download here.")
    render_todo_callout("Implement report export with branding and charts embedded.")
