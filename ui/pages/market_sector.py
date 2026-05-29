"""Market and sector analysis page."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.market_data_service import (
    get_market_breadth,
    get_market_data_status,
    get_market_overview,
    get_sector_performance,
    get_sector_rotation_history,
    get_top_movers_by_direction,
)
from ui.components.cards import render_metric_card
from ui.components.page_router import render_submenu_page
from utils.constants import COLORS
from utils.helpers import format_percent


def render(submenu: str) -> None:
    """Route market and sector analysis submenu."""
    handlers = {
        "Market overview": _market_overview,
        "Sector performance": _sector_performance,
        "Sector rotation": _sector_rotation,
        "Breadth and movers": _breadth_and_movers,
    }
    render_submenu_page(
        "Market & Sector Analysis",
        submenu,
        handlers,
        default_handler=_market_overview,
        subtitle=f"View: {submenu or 'Market overview'} · Source: {get_market_data_status()}",
    )


def _load_sector_performance(force_refresh: bool = False) -> None:
    """Load sector performance with optional refresh."""
    with st.spinner("Loading sector performance..."):
        st.session_state.sector_performance_df = get_sector_performance(force_refresh=force_refresh)


def _load_sector_rotation(force_refresh: bool = False) -> None:
    """Load sector rotation with optional refresh."""
    with st.spinner("Loading sector rotation..."):
        st.session_state.sector_rotation_df = get_sector_rotation_history(force_refresh=force_refresh)


def _market_overview() -> None:
    """Render broad market, sector, and mover overview."""
    overview = get_market_overview()
    cols = st.columns(len(overview))
    for i, row in overview.iterrows():
        with cols[i]:
            value = f"{row['Value']:,.2f}" if row["Index"] != "VIX" else f"{row['Value']:.2f}"
            render_metric_card(
                row["Index"],
                value,
                delta=format_percent(row["Change %"]),
                delta_value=row["Change %"],
            )

    st.caption(f"Index source: {overview.attrs.get('source', get_market_data_status())}")
    st.divider()

    st.markdown("**Breadth & Top Movers**")
    _render_breadth_and_movers()
    st.divider()

    if "sector_performance_df" not in st.session_state:
        _load_sector_performance()

    sector_df = _format_sector_performance(st.session_state.sector_performance_df)
    st.markdown("**Sector Performance**")
    st.caption(f"Sector source: {sector_df.attrs.get('source', 'Unknown')} · cached snapshot")
    chart_df = sector_df.sort_values("1D %", ascending=True)
    st.plotly_chart(_sector_performance_chart(chart_df, "1D %"), use_container_width=True)
    sector_columns = _sector_display_columns(sector_df)
    _render_sector_dataframe(sector_df.sort_values("1D %", ascending=False), sector_columns)


def _sector_performance() -> None:
    """Render ranked sector performance table and bar chart."""
    if "sector_performance_df" not in st.session_state:
        _load_sector_performance()

    refresh_col, _ = st.columns([1, 3])
    with refresh_col:
        if st.button("Refresh sector performance"):
            _load_sector_performance(force_refresh=True)
            st.rerun()

    sector_df = _format_sector_performance(st.session_state.sector_performance_df)
    st.caption(f"Sector source: {sector_df.attrs.get('source', 'Unknown')}")
    timeframe_options = [column for column in ["1D %", "1W %", "1M %", "YTD %", "1Y %", "3Y %"] if column in sector_df]
    selected_timeframe = st.selectbox(
        "Performance timeframe",
        timeframe_options,
        index=0,
        help="Choose which return period to plot in the sector performance chart.",
    )
    chart_df = sector_df.sort_values(selected_timeframe, ascending=True)
    st.plotly_chart(_sector_performance_chart(chart_df, selected_timeframe), use_container_width=True)
    _render_sector_momentum_explanation()
    sector_columns = _sector_display_columns(sector_df)
    sorted_sector_df = sector_df.sort_values(selected_timeframe, ascending=False).reset_index(drop=True)
    _render_sector_dataframe(sorted_sector_df, sector_columns)


def _sector_display_columns(sector_df) -> list[str]:
    """Return columns available for sector leader/laggard tables."""
    preferred_columns = ["Sector", "ETF", "Price", "1D %", "1W %", "1M %", "YTD %", "1Y %", "3Y %", "Momentum"]
    return [column for column in preferred_columns if column in sector_df.columns]


def _format_sector_performance(sector_df):
    """Round sector display metrics to two decimals while preserving metadata."""
    formatted = sector_df.copy()
    formatted.attrs.update(sector_df.attrs)
    numeric_columns = ["Price", "1D %", "1W %", "1M %", "YTD %", "1Y %", "3Y %"]
    for column in numeric_columns:
        if column in formatted.columns:
            formatted[column] = formatted[column].astype(float).round(2)
    return formatted


def _sector_column_config(columns: list[str]) -> dict:
    """Build Streamlit column config so tables sort numerically and display two decimals."""
    config: dict = {}
    if "Price" in columns:
        config["Price"] = st.column_config.NumberColumn("Price", format="%.2f")
    for column in ["1D %", "1W %", "1M %", "YTD %", "1Y %", "3Y %"]:
        if column in columns:
            config[column] = st.column_config.NumberColumn(column, format="%.2f%%")
    return config


def _render_sector_dataframe(sector_df, columns: list[str]) -> None:
    """Render a sector table with numeric sorting and two-decimal formatting."""
    st.dataframe(
        sector_df[columns],
        use_container_width=True,
        hide_index=True,
        column_config=_sector_column_config(columns),
    )


def _render_sector_momentum_explanation() -> None:
    """Explain sector momentum classification."""
    st.info(
        "**Momentum calculation:** Momentum is based on each sector ETF proxy's 1-month performance. "
        "If `1M %` is above `+1.00%`, the sector is labeled **Bullish**. "
        "If `1M %` is between `-1.00%` and `+1.00%`, it is labeled **Neutral / Sideways**. "
        "If `1M %` is below `-1.00%`, it is labeled **Bearish**. "
        "Sector data is cached on disk for faster navigation (22 compact API calls: daily + monthly per ETF)."
    )


def _sector_rotation() -> None:
    """Render sector rotation relative strength lines."""
    if "sector_rotation_df" not in st.session_state:
        _load_sector_rotation()

    refresh_col, _ = st.columns([1, 3])
    with refresh_col:
        if st.button("Refresh sector rotation"):
            _load_sector_rotation(force_refresh=True)
            st.rerun()

    rotation = st.session_state.sector_rotation_df
    st.caption(f"Rotation source: {rotation.attrs.get('source', 'Unknown')} · Daily 14-period RSI")
    if rotation.attrs.get("source", "").startswith("Mock") and rotation.attrs.get("error"):
        st.warning(f"Live sector rotation unavailable: {rotation.attrs['error']}")
    if rotation.empty or len(rotation.columns) <= 1:
        st.info("No sector rotation data is available yet.")
        return
    st.plotly_chart(_sector_rotation_chart(rotation), use_container_width=True)
    st.caption("Click a sector in the legend to add it to the chart; click again to hide it.")
    st.info(
        "RSI above 70 can indicate overbought momentum, RSI below 30 can indicate oversold momentum, "
        "and crosses around 50 often show a shift between strengthening and weakening sector trends."
    )


def _breadth_and_movers() -> None:
    """Render market breadth indicators and top mover tables."""
    _render_breadth_and_movers()


def _render_breadth_and_movers() -> None:
    """Render market breadth and top mover content."""
    breadth = get_market_breadth()
    st.caption(
        f"Breadth source: {breadth.attrs.get('source', 'Unknown')}"
        f" · Last updated: {breadth.attrs.get('last_updated', 'Unknown')}"
    )
    if breadth.attrs.get("source", "").startswith("Mock") and breadth.attrs.get("error"):
        st.warning(f"Live top movers/breadth unavailable: {breadth.attrs['error']}")
    elif breadth.attrs.get("warning"):
        st.warning(f"Using cached breadth because live refresh failed: {breadth.attrs['warning']}")
    st.dataframe(breadth, use_container_width=True, hide_index=True)
    st.info(
        "Alpha Vantage does not provide full exchange breadth like stocks above 50D/200D here, "
        "so these live breadth readings are derived from its top gainers, top losers, and most-active lists."
    )

    movers = get_top_movers_by_direction(limit=10)
    st.caption(f"Movers source: {movers['source']} · Last updated: {movers['last_updated']}")
    if movers.get("source", "").startswith("Mock") and movers.get("error"):
        st.warning(f"Live top movers unavailable: {movers['error']}")
    elif movers.get("warning"):
        st.warning(f"Using cached top movers because live refresh failed: {movers['warning']}")
    left, right = st.columns(2)
    with left:
        st.markdown("**Top Gainers**")
        st.dataframe(movers["gainers"], use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Top Losers**")
        st.dataframe(movers["losers"], use_container_width=True, hide_index=True)
    if "most_active" in movers and not movers["most_active"].empty:
        st.markdown("**Most Active**")
        st.dataframe(movers["most_active"], use_container_width=True, hide_index=True)


def _sector_performance_chart(sector_df, timeframe: str = "1D %") -> go.Figure:
    """Build a sector performance bar chart."""
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in sector_df[timeframe]]
    fig = go.Figure(
        go.Bar(
            x=sector_df[timeframe],
            y=sector_df["Sector"],
            orientation="h",
            marker_color=colors,
            name=timeframe,
        )
    )
    fig.update_layout(
        title=dict(text=f"Sector Performance — {timeframe}", font=dict(size=14, color=COLORS["primary"])),
        height=430,
        margin=dict(l=30, r=30, t=50, b=35),
        paper_bgcolor="white",
        plot_bgcolor="#fafbfc",
        xaxis=dict(title="Change %", showgrid=True, gridcolor="#e8ecf0"),
        yaxis=dict(showgrid=False),
    )
    fig.add_vline(x=0, line_color=COLORS["neutral"], line_dash="dash")
    return fig


def _sector_rotation_chart(rotation) -> go.Figure:
    """Build a sector rotation RSI chart."""
    fig = go.Figure()
    line_colors = [
        COLORS["secondary"],
        COLORS["accent"],
        COLORS["positive"],
        COLORS["negative"],
        COLORS["neutral"],
        "#7b3f98",
        "#00a3a3",
        "#f39c12",
        "#8e6e53",
        "#34495e",
        "#27ae60",
    ]
    sector_columns = [column for column in rotation.columns if column != "Date"]
    for index, column in enumerate(sector_columns):
        fig.add_trace(
            go.Scatter(
                x=rotation["Date"],
                y=rotation[column],
                mode="lines",
                name=column,
                line=dict(color=line_colors[index % len(line_colors)], width=2),
                visible=True if index == 0 else "legendonly",
            )
        )
    fig.update_layout(
        title=dict(
            text="Sector ETF RSI Rotation",
            font=dict(size=14, color=COLORS["primary"]),
            x=0.01,
            xanchor="left",
        ),
        height=500,
        margin=dict(l=40, r=30, t=60, b=110),
        paper_bgcolor="white",
        plot_bgcolor="#fafbfc",
        xaxis=dict(showgrid=True, gridcolor="#e8ecf0"),
        yaxis=dict(title="RSI", range=[0, 100], showgrid=True, gridcolor="#e8ecf0"),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
    )
    fig.add_hline(y=70, line_color=COLORS["negative"], line_dash="dash", opacity=0.55)
    fig.add_hline(y=50, line_color=COLORS["neutral"], line_dash="dot", opacity=0.45)
    fig.add_hline(y=30, line_color=COLORS["positive"], line_dash="dash", opacity=0.55)
    return fig
