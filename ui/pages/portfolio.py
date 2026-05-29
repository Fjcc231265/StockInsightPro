"""Portfolio Watchlist page."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st
import pandas as pd

from data.providers import alpha_vantage_provider
from ui.components.cards import render_todo_callout
from ui.components.charts import comparison_bar_chart
from ui.components.page_router import render_submenu_page
from services.market_data_service import (
    add_favorite_symbol,
    get_available_tickers,
    get_quote_summary,
    save_favorite_symbols,
    validate_symbol,
)
from services.universe_service import (
    get_stock_universe_symbols,
    import_stock_universe_csv,
    load_stock_universe,
    save_stock_universe,
    universe_file_status,
)
from utils.helpers import format_large_number
from utils.helpers import normalize_ticker

RSI_SCAN_RESULTS_FILE = Path(__file__).resolve().parents[2] / "data" / "rsi_scan_results.csv"


def render(submenu: str) -> None:
    """Route portfolio watchlist submenu."""
    handlers = {
        "Add ticker": _add_ticker,
        "Track favorites": _track_favorites,
        "Alerts placeholder": _alerts,
        "Compare stocks": _compare_stocks,
    }
    render_submenu_page(
        "Portfolio Watchlist",
        submenu,
        handlers,
        default_handler=_track_favorites,
    )


def _add_ticker() -> None:
    """Add ticker to watchlist form with Alpha Vantage validation."""
    st.markdown("**Add Symbol to Watchlist**")
    proposed_symbol = normalize_ticker(
        st.text_input(
            "Ticker symbol",
            placeholder="e.g. PLTR, SMCI, DCTH",
            key="add_ticker_symbol",
        )
    )
    persist = st.checkbox("Save favorites to disk", value=True, key="persist_added_ticker")

    if st.button("Validate and Add to Watchlist", type="primary"):
        validation = validate_symbol(proposed_symbol)
        if not validation["valid"]:
            st.error(validation["message"])
            return
        symbol = validation["symbol"]
        if symbol in st.session_state.watchlist:
            st.info(f"{symbol} is already in your favorites.")
            return
        st.session_state.watchlist = add_favorite_symbol(symbol, st.session_state.watchlist, persist=persist)
        st.session_state.selected_ticker = symbol
        st.success(f"{validation['message']} Added {symbol} to favorites.")
        if persist:
            st.caption("Saved to disk and available next session.")
        else:
            st.caption("Added for this session only.")

    if st.session_state.watchlist:
        st.caption(f"Current favorites: {', '.join(st.session_state.watchlist)}")


def _track_favorites() -> None:
    """Display current watchlist."""
    rows = []
    for t in st.session_state.watchlist:
        q = get_quote_summary(t)
        rows.append(
            {
                "Ticker": t,
                "Price": round(q["price"], 2),
                "Change %": round(q["change_pct"], 2),
                "Sector": q["sector"],
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    remove = st.multiselect(
        "Remove tickers",
        options=st.session_state.watchlist,
        help="Select one or more favorites, then remove them all at once.",
    )
    persist = st.checkbox("Save removal to disk", value=True, key="persist_removed_ticker")
    if st.button("Remove Selected", disabled=not remove):
        removed = set(remove)
        remaining = [symbol for symbol in st.session_state.watchlist if symbol not in removed]
        st.session_state.watchlist = save_favorite_symbols(remaining) if persist else remaining
        if st.session_state.selected_ticker in removed and st.session_state.watchlist:
            st.session_state.selected_ticker = st.session_state.watchlist[0]
        elif st.session_state.selected_ticker in removed:
            st.session_state.selected_ticker = ""
        st.success(f"Removed {len(remove)} symbols from favorites: {', '.join(remove)}.")
        st.rerun()

    if st.button("Save Current Favorites to Disk"):
        st.session_state.watchlist = save_favorite_symbols(st.session_state.watchlist)
        st.success("Favorites saved to disk.")
    render_todo_callout("Add drag-and-drop sorting and portfolio grouping.")


def _alerts() -> None:
    """Screen symbols for low-to-high RSI alert candidates."""
    st.markdown("**RSI Alert Screener**")
    st.caption(
        "Stage 1 scans only RSI from your symbol CSV and adds low-RSI names to favorites. "
        "Stage 2 loads quote, volume, exchange, sector, and filters only for favorites. "
        "Stage 3 scores the filtered shortlist with RSI, MACD, and ADX."
    )

    if not alpha_vantage_provider.is_configured():
        st.error("Alpha Vantage API key is required for the live RSI screener. Mock data is not used here.")
        return

    _render_universe_manager()

    scan_symbols = _resolve_scan_universe()
    if not scan_symbols:
        return

    st.markdown("#### Stage 1 — Add low-RSI symbols to favorites")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rsi_limit = st.number_input(
            "Add to favorites when RSI is <= ",
            min_value=0.0,
            max_value=100.0,
            value=30.0,
            step=1.0,
        )
    with col2:
        rsi_period = st.number_input(
            "RSI period",
            min_value=2,
            max_value=50,
            value=9,
            step=1,
            help="Matches your standalone script by default: RSI(9).",
        )
    with col3:
        pause_every = st.number_input(
            "Pause after this many symbols",
            min_value=25,
            max_value=1000,
            value=250,
            step=25,
            help="The scan pauses after each batch to reduce the risk of exceeding Alpha Vantage limits.",
        )
    with col4:
        pause_seconds = st.number_input(
            "Pause duration in seconds",
            min_value=0,
            max_value=600,
            value=0,
            step=5,
        )

    st.caption(
        f"Ready to scan **{len(scan_symbols)}** symbols from the CSV file. "
        "This first pass calls only Alpha Vantage RSI, updates the UI in batches, and saves the full RSI table to disk."
    )

    if st.button("Scan CSV RSI and Add to Favorites", type="primary"):
        with st.spinner(f"Scanning RSI for {len(scan_symbols)} CSV symbols..."):
            candidates, unavailable, all_rsi = _scan_csv_for_rsi_candidates(
                scan_symbols,
                rsi_limit=float(rsi_limit),
                time_period=int(rsi_period),
                pause_every=int(pause_every),
                pause_seconds=int(pause_seconds),
            )
            if not all_rsi.empty:
                RSI_SCAN_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
                all_rsi.to_csv(RSI_SCAN_RESULTS_FILE, index=False)
            current_favorites = list(st.session_state.watchlist)
            candidate_symbols = candidates["Ticker"].tolist() if not candidates.empty else []
            st.session_state.watchlist = save_favorite_symbols([*current_favorites, *candidate_symbols])
            st.session_state.rsi_all_results = all_rsi
            st.session_state.rsi_candidate_results = candidates
            st.session_state.rsi_screener_unavailable = unavailable
            elapsed = all_rsi.attrs.get("elapsed_seconds", 0)
            st.success(
                f"Added {len([symbol for symbol in candidate_symbols if symbol not in current_favorites])} "
                f"new symbols to favorites from {len(candidates)} RSI matches. "
                f"RSI pass completed in {elapsed:.1f} seconds."
            )
            if not all_rsi.empty:
                st.caption(f"Saved full RSI scan to `{RSI_SCAN_RESULTS_FILE}`.")

    all_rsi = st.session_state.get("rsi_all_results")
    if all_rsi is not None and not all_rsi.empty:
        with st.expander(f"Latest full RSI-only scan ({len(all_rsi)} symbols)", expanded=False):
            st.dataframe(
                all_rsi.head(25),
                use_container_width=True,
                hide_index=True,
                column_config={"RSI Daily": st.column_config.NumberColumn("RSI Daily", format="%.1f")},
            )

    candidates = st.session_state.get("rsi_candidate_results")
    unavailable = st.session_state.get("rsi_screener_unavailable", pd.DataFrame())
    if candidates is not None and not candidates.empty:
        st.caption(f"Latest RSI-only candidates at or below {rsi_limit:.2f}.")
        st.dataframe(
            candidates.sort_values("RSI", ascending=True).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={"RSI": st.column_config.NumberColumn("RSI", format="%.2f")},
        )
    _render_unavailable_symbols(unavailable)

    st.divider()
    st.markdown("#### Stage 2 — Load details for favorites")
    st.caption(f"Favorites available for details: **{len(st.session_state.watchlist)}**")
    if st.button("Load Favorite Details"):
        with st.spinner(f"Loading quote, RSI, exchange, volume, and sector for {len(st.session_state.watchlist)} favorites..."):
            results, detail_unavailable = _load_favorite_details(st.session_state.watchlist, time_period=int(rsi_period))
            st.session_state.rsi_screener_results = results
            st.session_state.rsi_favorite_detail_unavailable = detail_unavailable

    screener = st.session_state.get("rsi_screener_results")
    detail_unavailable = st.session_state.get("rsi_favorite_detail_unavailable", pd.DataFrame())
    if screener is None or screener.empty:
        _render_unavailable_symbols(detail_unavailable)
        st.info("Load favorite details to populate the filtered table.")
        return

    _render_screener_results(screener)
    _render_unavailable_symbols(detail_unavailable)


def _render_universe_manager() -> None:
    """Manage the saved stock universe used by the RSI screener."""
    status = universe_file_status()
    with st.expander("Symbol CSV file", expanded=not status["exists"]):
        if status["exists"]:
            st.success(f"Loaded **{status['count']:,}** symbols from `{status['path']}`.")
            if status.get("parse_method") == "lenient_text":
                st.info(
                    "The symbol file was read in lenient mode because it is not a strict one-column CSV. "
                    "Use **Rewrite as clean CSV** to save one symbol per row."
                )
                if st.button("Rewrite as clean CSV"):
                    cleaned = save_stock_universe(load_stock_universe())
                    st.success(f"Saved {len(cleaned):,} symbols in clean CSV format.")
                    st.rerun()
        else:
            st.warning(f"No symbol file found yet. Add or upload a CSV at `{status['path']}`.")

        uploaded = st.file_uploader(
            "Upload symbol CSV",
            type=["csv"],
            help="Use one `symbol` column, or a one-column CSV where the first column contains symbols.",
        )
        if uploaded is not None:
            try:
                imported = import_stock_universe_csv(uploaded.getvalue())
                st.success(f"Imported {len(imported):,} symbols from file and saved a clean CSV.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"CSV import failed: {exc}")

        preview = load_stock_universe().head(20)
        if not preview.empty:
            st.markdown("**Symbol file preview (first 20 rows)**")
            st.dataframe(preview, use_container_width=True, hide_index=True)


def _resolve_scan_universe() -> list[str]:
    """Resolve all symbols from the local CSV file."""
    universe_status = universe_file_status()
    if not universe_status["exists"]:
        st.warning("Add symbols to the CSV file or upload one before running the scan.")
        return []

    symbols = get_stock_universe_symbols()
    if not symbols:
        st.warning("The symbol CSV is empty.")
    return symbols


def _render_screener_results(screener: pd.DataFrame) -> None:
    """Render post-scan filters and the top 20 lowest-RSI matches."""
    price_min = float(screener["Price"].min())
    price_max = float(screener["Price"].max())
    slider_max = price_max if price_max > price_min else price_min + 1.0

    col1, col2, col3 = st.columns(3)
    with col1:
        price_range = st.slider(
            "Price range",
            min_value=price_min,
            max_value=slider_max,
            value=(price_min, slider_max),
            step=1.0,
        )
    with col2:
        min_volume = st.number_input("Minimum volume", min_value=0, value=0, step=100_000)
    with col3:
        max_rsi = st.slider("Maximum RSI", min_value=0.0, max_value=100.0, value=100.0, step=1.0)

    sector_options = sorted(sector for sector in screener["Sector"].dropna().unique() if sector and sector != "Unknown")
    market_options = sorted(market for market in screener["Market"].dropna().unique() if market and market != "Unknown")
    sector_filter = st.multiselect(
        "Sector filter",
        options=sector_options,
        default=sector_options,
        help="Sector is filled when Alpha Vantage company overview is available for the scanned symbol.",
    )
    market_filter = st.multiselect("Market filter", options=market_options, default=market_options)

    sector_mask = screener["Sector"].isin(sector_filter) if sector_filter else True
    market_mask = screener["Market"].isin(market_filter) if market_filter else True
    filtered = screener[
        (screener["Price"].between(price_range[0], price_range[1]))
        & (screener["Volume"] >= min_volume)
        & (screener["RSI"] <= max_rsi)
        & sector_mask
        & market_mask
    ].sort_values("RSI", ascending=True)

    selected = filtered.head(20).reset_index(drop=True)
    st.caption(
        f"Scanned {len(screener)} symbols with live data · "
        f"Showing {len(selected)} of {len(filtered)} matches, sorted by lowest RSI first."
    )
    st.dataframe(
        selected,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
            "Volume": st.column_config.NumberColumn("Volume", format="%d"),
            "RSI": st.column_config.NumberColumn("RSI", format="%.2f"),
        },
    )

    st.markdown("#### Stage 3 — Score filtered shortlist")
    st.caption(
        "Scores the current Stage 2 filtered symbols out of 60: "
        "20 for RSI within the selected filter, 20 for MACD bullish below zero, "
        "and 20 for rising ADX."
    )
    if filtered.empty:
        st.info("Adjust Stage 2 filters until at least one symbol remains before scoring.")
        return

    if st.button("Score Current Filtered Shortlist"):
        with st.spinner(f"Scoring {len(filtered)} filtered symbols with MACD and ADX..."):
            st.session_state.rsi_stage3_scores = _score_stage3_candidates(
                filtered.reset_index(drop=True),
                max_rsi=float(max_rsi),
            )

    scored = st.session_state.get("rsi_stage3_scores")
    if scored is not None and not scored.empty:
        st.caption(f"Stage 3 scored {len(scored)} symbols, sorted by highest score first.")
        st.dataframe(
            scored,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.NumberColumn("Score", format="%d"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                "Volume": st.column_config.NumberColumn("Volume", format="%d"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.2f"),
                "ADX": st.column_config.NumberColumn("ADX", format="%.2f"),
                "MACD": st.column_config.NumberColumn("MACD", format="%.4f"),
                "MACD Signal": st.column_config.NumberColumn("MACD Signal", format="%.4f"),
                "MACD Hist": st.column_config.NumberColumn("MACD Hist", format="%.4f"),
            },
        )


def _scan_csv_for_rsi_candidates(
    symbols: list[str],
    rsi_limit: float,
    time_period: int,
    pause_every: int,
    pause_seconds: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Scan CSV symbols using only Alpha Vantage RSI and return favorites candidates."""
    rows = []
    all_rows = []
    unavailable_rows = []
    progress = st.progress(0.0, text="Starting RSI-only scan...")
    status = st.empty()
    started_at = time.perf_counter()
    update_every = max(25, min(100, len(symbols) // 20 or 25))

    for index, symbol in enumerate(symbols):
        if index == 0 or (index + 1) % update_every == 0 or index + 1 == len(symbols):
            elapsed = time.perf_counter() - started_at
            status.caption(
                f"Checking RSI for {symbol} ({index + 1}/{len(symbols)}) · "
                f"{len(all_rows)} valid · {len(unavailable_rows)} unavailable · {elapsed:.1f}s"
            )
            progress.progress((index + 1) / len(symbols), text=f"Checking RSI batch through {symbol}...")
        try:
            latest_rsi = alpha_vantage_provider.get_latest_rsi(symbol, time_period=time_period)
        except Exception as exc:  # noqa: BLE001 - skip unavailable symbols in screeners
            unavailable_rows.append(
                {
                    "Symbol": symbol,
                    "Reason": _short_unavailable_reason(str(exc)),
                }
            )
            continue

        rsi_value = float(latest_rsi["rsi"])
        rsi_date = latest_rsi["date"]
        all_rows.append(
            {
                "date": rsi_date,
                "RSI Daily": round(rsi_value, 1),
                "Symbol": symbol,
            }
        )
        if rsi_value <= rsi_limit:
            rows.append(
                {
                    "Ticker": symbol,
                    "Date": rsi_date,
                    "RSI": round(rsi_value, 1),
                    "Source": "Daily OHLC RSI",
                }
            )

        if pause_every > 0 and pause_seconds > 0 and (index + 1) % pause_every == 0 and index + 1 < len(symbols):
            status.caption(
                f"Paused after {index + 1} symbols for {pause_seconds} seconds to respect Alpha Vantage limits."
            )
            time.sleep(pause_seconds)

    progress.empty()
    status.empty()
    candidates = pd.DataFrame(rows).sort_values("RSI", ascending=True) if rows else pd.DataFrame(rows)
    all_rsi = pd.DataFrame(all_rows).sort_values("RSI Daily", ascending=True).reset_index(drop=True) if all_rows else pd.DataFrame(all_rows)
    all_rsi.attrs["elapsed_seconds"] = time.perf_counter() - started_at
    return candidates, pd.DataFrame(unavailable_rows), all_rsi


def _score_stage3_candidates(candidates: pd.DataFrame, max_rsi: float) -> pd.DataFrame:
    """Score filtered favorites with RSI, MACD, and ADX signals."""
    rows = []
    unique_candidates = candidates.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)
    progress = st.progress(0.0, text="Starting Stage 3 scoring...")
    status = st.empty()

    for index, row in unique_candidates.iterrows():
        symbol = row["Ticker"]
        status.caption(f"Scoring {symbol} ({index + 1}/{len(unique_candidates)})")
        progress.progress((index + 1) / len(unique_candidates), text=f"Scoring {symbol}...")

        notes = []
        rsi_value = float(row["RSI"])
        rsi_pass = rsi_value <= max_rsi
        macd_signal = False
        adx_rising = False
        macd_latest = pd.Series(dtype="float64")
        adx_latest = pd.Series(dtype="float64")

        try:
            history = alpha_vantage_provider.get_price_history(symbol, periods=60, timeframe="Daily").sort_values("Date")
            macd_history = alpha_vantage_provider.macd_from_history(history, days=5)
            macd_latest = macd_history.iloc[-1]
            macd_signal = _has_macd_oversold_signal(macd_history)
            adx_history = alpha_vantage_provider.adx_from_history(history, days=5)
            adx_latest = adx_history.iloc[-1]
            adx_rising = _is_adx_rising(adx_history)
        except Exception as exc:  # noqa: BLE001 - show partial scores instead of dropping symbols
            notes.append(f"Indicators unavailable: {_short_unavailable_reason(str(exc))}")

        rsi_score = 20 if rsi_pass else 0
        macd_score = 20 if macd_signal else 0
        adx_score = 20 if adx_rising else 0
        rows.append(
            {
                **row.to_dict(),
                "Score": rsi_score + macd_score + adx_score,
                "RSI Score": rsi_score,
                "MACD Score": macd_score,
                "ADX Score": adx_score,
                "RSI Filter Match": rsi_pass,
                "MACD Oversold Signal": macd_signal,
                "ADX Rising": adx_rising,
                "MACD": _optional_round(macd_latest.get("MACD")),
                "MACD Signal": _optional_round(macd_latest.get("MACD Signal")),
                "MACD Hist": _optional_round(macd_latest.get("MACD Hist")),
                "ADX": _optional_round(adx_latest.get("ADX")),
                "Stage 3 Notes": "; ".join(notes) if notes else "",
            }
        )

    progress.empty()
    status.empty()
    if not rows:
        return pd.DataFrame(rows)
    return (
        pd.DataFrame(rows)
        .sort_values(["Score", "RSI"], ascending=[False, True])
        .reset_index(drop=True)
    )


def _has_macd_oversold_signal(macd_history: pd.DataFrame) -> bool:
    """Treat bullish MACD momentum below zero as an oversold reversal signal."""
    if macd_history.empty:
        return False

    latest = macd_history.iloc[-1]
    macd_value = float(latest["MACD"])
    signal_value = float(latest["MACD Signal"])
    hist_value = float(latest["MACD Hist"])
    return macd_value < 0 and macd_value > signal_value and hist_value > 0


def _is_adx_rising(adx_history: pd.DataFrame) -> bool:
    """Return True when the latest ADX is above the prior ADX value."""
    if len(adx_history) < 2:
        return False

    latest_adx = float(adx_history["ADX"].iloc[-1])
    previous_adx = float(adx_history["ADX"].iloc[-2])
    return latest_adx > previous_adx


def _optional_round(value: object, digits: int = 4) -> float | None:
    """Round numeric indicator values while preserving unavailable values."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _load_favorite_details(symbols: list[str], time_period: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load quote, overview, and RSI details for current favorites only."""
    rows = []
    unavailable_rows = []
    unique_symbols = list(dict.fromkeys(symbols))
    if not unique_symbols:
        return pd.DataFrame(), pd.DataFrame()

    progress = st.progress(0.0, text="Starting favorite detail lookup...")
    status = st.empty()
    for index, symbol in enumerate(unique_symbols):
        status.caption(f"Loading details for {symbol} ({index + 1}/{len(unique_symbols)})")
        progress.progress((index + 1) / len(unique_symbols), text=f"Loading {symbol} details...")
        try:
            quote = alpha_vantage_provider.get_quote(symbol)
            rsi_history = alpha_vantage_provider.get_rsi_history(symbol, days=1, time_period=time_period)
            overview = alpha_vantage_provider.get_company_overview(symbol)
        except Exception as exc:  # noqa: BLE001 - keep favorites but show unavailable details
            unavailable_rows.append({"Symbol": symbol, "Reason": _short_unavailable_reason(str(exc))})
            continue

        if rsi_history.empty:
            unavailable_rows.append({"Symbol": symbol, "Reason": "Alpha Vantage returned no RSI values."})
            continue

        rows.append(
            {
                "Ticker": symbol,
                "Name": overview.get("name") or quote.get("name") or symbol,
                "Price": round(float(quote.get("price", 0)), 2),
                "Change %": round(float(quote.get("change_pct", 0)), 2),
                "Volume": int(quote.get("volume", 0) or 0),
                "RSI": round(float(rsi_history["RSI"].iloc[-1]), 2),
                "Sector": overview.get("sector") or "Unknown",
                "Market": overview.get("exchange") or "Unknown",
                "Source": "Alpha Vantage quote/overview · RSI from daily OHLC",
            }
        )

    progress.empty()
    status.empty()
    return pd.DataFrame(rows), pd.DataFrame(unavailable_rows)


def _render_unavailable_symbols(unavailable: pd.DataFrame) -> None:
    """Show symbols skipped because Alpha Vantage did not return complete data."""
    if unavailable is None or unavailable.empty:
        return

    with st.expander(f"Unavailable symbols skipped ({len(unavailable)})", expanded=True):
        st.warning("These symbols were skipped. Remove or correct them in `data/rsi_screener_symbols.csv`.")
        st.dataframe(unavailable, use_container_width=True, hide_index=True)


def _short_unavailable_reason(reason: str) -> str:
    """Keep provider errors readable in the cleanup table."""
    if len(reason) <= 180:
        return reason
    return f"{reason[:177]}..."


def _compare_stocks() -> None:
    """Side-by-side stock comparison."""
    comparison_options = list(dict.fromkeys([*st.session_state.watchlist, *get_available_tickers()]))
    selected = st.multiselect(
        "Select tickers to compare",
        options=comparison_options,
        default=st.session_state.watchlist[:3],
        max_selections=5,
    )
    if not selected:
        st.warning("Select at least one ticker.")
        return

    rows = []
    for t in selected:
        q = get_quote_summary(t)
        rows.append(
            {
                "Ticker": t,
                "Price": round(q["price"], 2),
                "Change %": round(q["change_pct"], 2),
                "Volume": format_large_number(q["volume"]),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.plotly_chart(comparison_bar_chart(df, "Change %"), use_container_width=True)
    render_todo_callout("Add multi-metric comparison and correlation matrix.")
