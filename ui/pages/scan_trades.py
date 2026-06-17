"""Scan Trades page — multi-criteria trade scanners."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from analytics.technical.pullback_scan import PullbackScanConfig, evaluate_pullback_setup, score_pullback_refinement
from data.providers import alpha_vantage_provider
from services.market_data_service import save_favorite_symbols
from services.universe_service import (
    get_stock_universe_symbols,
    import_stock_universe_csv,
    load_stock_universe,
    save_stock_universe,
    universe_file_status,
)
from ui.components.page_router import render_submenu_page

RSI_SCAN_RESULTS_FILE = Path(__file__).resolve().parents[2] / "data" / "rsi_scan_results.csv"
PULLBACK_SCAN_RESULTS_FILE = Path(__file__).resolve().parents[2] / "data" / "pullback_scan_results.csv"


def render(submenu: str) -> None:
    """Route Scan Trades submenu."""
    handlers = {
        "Bottom Phising": _bottom_phising,
        "Breakout scan": _breakout_scan,
        "Pullback scan": _pullback_scan,
        "Volume surge scan": _volume_surge_scan,
    }
    render_submenu_page(
        "Scan Trades",
        submenu,
        handlers,
        default_handler=_bottom_phising,
        subtitle="Run technical scans against your symbol universe and shortlist trade ideas.",
    )


def _bottom_phising() -> None:
    """Screen symbols for low-to-high RSI bottom-fishing candidates."""
    st.markdown("**Bottom Phising**")
    st.caption(
        "Three-stage bottom-fishing workflow: scan the symbol universe for low RSI, load details for favorites, "
        "then score the shortlist with RSI, MACD, and ADX."
    )

    if not alpha_vantage_provider.is_configured():
        st.error("Alpha Vantage API key is required for live scans. Mock data is not used here.")
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
            key="scan_bottom_rsi_limit",
        )
    with col2:
        rsi_period = st.number_input(
            "RSI period",
            min_value=2,
            max_value=50,
            value=9,
            step=1,
            help="Matches your standalone script by default: RSI(9).",
            key="scan_bottom_rsi_period",
        )
    with col3:
        pause_every = st.number_input(
            "Pause after this many symbols",
            min_value=25,
            max_value=1000,
            value=250,
            step=25,
            help="The scan pauses after each batch to reduce the risk of exceeding Alpha Vantage limits.",
            key="scan_bottom_pause_every",
        )
    with col4:
        pause_seconds = st.number_input(
            "Pause duration in seconds",
            min_value=0,
            max_value=600,
            value=0,
            step=5,
            key="scan_bottom_pause_seconds",
        )

    st.caption(
        f"Ready to scan **{len(scan_symbols)}** symbols from the CSV file. "
        "This first pass calls only Alpha Vantage RSI, updates the UI in batches, and saves the full RSI table to disk."
    )

    if st.button("Scan CSV RSI and Add to Favorites", type="primary", key="scan_bottom_run_stage1"):
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
    if st.button("Load Favorite Details", key="scan_bottom_run_stage2"):
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


def _breakout_scan() -> None:
    """Placeholder for breakout-style scans."""
    st.markdown("**Breakout scan**")
    st.caption("Find symbols breaking above resistance with expanding volume and constructive momentum.")
    st.info(
        "Planned criteria: price above recent resistance or 20/40-day moving averages, "
        "volume above its 20-day average, RSI between 55 and 75, and MACD histogram turning positive."
    )
    st.markdown(
        """
**Example workflow (coming next)**

1. Scan the symbol CSV for closes above the prior 20-day high.
2. Require volume at least 1.5x the 20-day average.
3. Filter by sector and minimum price.
4. Rank by relative volume and distance above breakout level.
"""
    )


def _pullback_scan() -> None:
    """Scan for bullish pullbacks into the 20/40 MA zone with support and hammer confirmation."""
    st.markdown("**Pullback scan**")
    st.caption(
        "Find uptrend pullbacks into the 20/40 MA zone or sideways names retesting support. "
        "Stage 1 detects the pattern; Stage 2 filters; Stage 3 refines with MACD, ADX, and RSI."
    )

    if not alpha_vantage_provider.is_configured():
        st.error("Alpha Vantage API key is required for live scans. Mock data is not used here.")
        return

    _render_universe_manager()

    scan_symbols = _resolve_scan_universe()
    if not scan_symbols:
        return

    st.markdown("#### Scan settings")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rsi_period = st.number_input("RSI period", min_value=2, max_value=50, value=9, step=1, key="pullback_rsi_period")
        min_red_candles = st.number_input(
            "Minimum recent red candles",
            min_value=1,
            max_value=10,
            value=3,
            step=1,
            key="pullback_min_reds",
        )
    with col2:
        ma_proximity_pct = st.number_input(
            "MA20 proximity %",
            min_value=0.5,
            max_value=8.0,
            value=2.5,
            step=0.5,
            help="How close price must be to the 20 MA, or inside the 20/40 MA pullback zone.",
            key="pullback_ma_proximity",
        )
        min_prior_rsi = st.number_input(
            "Prior RSI high threshold",
            min_value=45.0,
            max_value=85.0,
            value=55.0,
            step=1.0,
            key="pullback_min_prior_rsi",
        )
    with col3:
        support_proximity_pct = st.number_input(
            "Support proximity %",
            min_value=1.0,
            max_value=10.0,
            value=4.0,
            step=0.5,
            key="pullback_support_proximity",
        )
        red_candle_lookback = st.number_input(
            "Red-candle lookback (days)",
            min_value=3,
            max_value=15,
            value=8,
            step=1,
            key="pullback_red_lookback",
        )
    with col4:
        include_sideways = st.checkbox(
            "Include sideways support setups",
            value=True,
            help="Also scan range-bound stocks sitting near support, even without a rising 20/40 MA trend.",
            key="pullback_include_sideways",
        )
        pause_every = st.number_input(
            "Pause after this many symbols",
            min_value=25,
            max_value=1000,
            value=250,
            step=25,
            key="pullback_pause_every",
        )
        pause_seconds = st.number_input(
            "Pause duration in seconds",
            min_value=0,
            max_value=600,
            value=0,
            step=5,
            key="pullback_pause_seconds",
        )

    scan_config = PullbackScanConfig(
        rsi_period=int(rsi_period),
        min_red_candles=int(min_red_candles),
        ma_proximity_pct=float(ma_proximity_pct),
        min_prior_rsi=float(min_prior_rsi),
        support_proximity_pct=float(support_proximity_pct),
        red_candle_lookback=int(red_candle_lookback),
        include_sideways_support=include_sideways,
    )

    st.caption(
        f"Ready to scan **{len(scan_symbols)}** symbols. "
        "Each symbol uses daily OHLC history to test trend, MA pullback, red candles, support, and hammer shape."
    )

    if st.button("Run Pullback Scan", type="primary", key="pullback_run_scan"):
        with st.spinner(f"Scanning pullback setups across {len(scan_symbols)} symbols..."):
            results, unavailable = _scan_universe_for_pullbacks(
                scan_symbols,
                scan_config,
                pause_every=int(pause_every),
                pause_seconds=int(pause_seconds),
            )
            st.session_state.pullback_scan_results = results
            st.session_state.pullback_scan_unavailable = unavailable
            if not results.empty:
                PULLBACK_SCAN_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
                results.to_csv(PULLBACK_SCAN_RESULTS_FILE, index=False)
            elapsed = results.attrs.get("elapsed_seconds", 0)
            st.success(
                f"Found {len(results)} pullback matches out of {len(scan_symbols)} symbols in {elapsed:.1f} seconds."
            )
            if not results.empty:
                st.caption(f"Saved pullback scan to `{PULLBACK_SCAN_RESULTS_FILE}`.")

    results = st.session_state.get("pullback_scan_results")
    unavailable = st.session_state.get("pullback_scan_unavailable", pd.DataFrame())
    if results is None or results.empty:
        _render_unavailable_symbols(unavailable)
        st.info("Run the pullback scan to populate matches.")
        return

    _render_pullback_results(results)
    _render_unavailable_symbols(unavailable)


def _scan_universe_for_pullbacks(
    symbols: list[str],
    config: PullbackScanConfig,
    pause_every: int,
    pause_seconds: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Scan the symbol universe for pullback setups."""
    rows = []
    unavailable_rows = []
    progress = st.progress(0.0, text="Starting pullback scan...")
    status = st.empty()
    started_at = time.perf_counter()
    update_every = max(25, min(100, len(symbols) // 20 or 25))

    for index, symbol in enumerate(symbols):
        if index == 0 or (index + 1) % update_every == 0 or index + 1 == len(symbols):
            elapsed = time.perf_counter() - started_at
            status.caption(
                f"Checking {symbol} ({index + 1}/{len(symbols)}) · "
                f"{len(rows)} matches · {len(unavailable_rows)} unavailable · {elapsed:.1f}s"
            )
            progress.progress((index + 1) / len(symbols), text=f"Pullback scan through {symbol}...")

        try:
            history = alpha_vantage_provider.get_price_history(symbol, periods=config.history_periods, timeframe="Daily")
            metrics = evaluate_pullback_setup(history, config)
        except Exception as exc:  # noqa: BLE001
            unavailable_rows.append({"Symbol": symbol, "Reason": _short_unavailable_reason(str(exc))})
            continue

        if metrics is None:
            continue

        metrics["Ticker"] = symbol
        rows.append(metrics)

        if pause_every > 0 and pause_seconds > 0 and (index + 1) % pause_every == 0 and index + 1 < len(symbols):
            status.caption(
                f"Paused after {index + 1} symbols for {pause_seconds} seconds to respect Alpha Vantage limits."
            )
            time.sleep(pause_seconds)

    progress.empty()
    status.empty()
    if not rows:
        frame = pd.DataFrame(rows)
    else:
        frame = (
            pd.DataFrame(rows)
            .sort_values(["Total Score", "Hammer", "Prior Support Hammers"], ascending=[False, False, False])
            .reset_index(drop=True)
        )
    frame.attrs["elapsed_seconds"] = time.perf_counter() - started_at
    return frame, pd.DataFrame(unavailable_rows)


def _render_pullback_results(results: pd.DataFrame) -> None:
    """Render pullback scan filters, refinement scoring, and ranked shortlist."""
    st.markdown("#### Stage 2 — Filter pullback matches")
    price_min = float(results["Price"].min())
    price_max = float(results["Price"].max())
    slider_max = price_max if price_max > price_min else price_min + 1.0
    rsi_min = float(results["RSI"].min())
    rsi_max = float(results["RSI"].max())
    setup_types = sorted(results["Setup Type"].dropna().unique().tolist())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        price_range = st.slider(
            "Price range",
            min_value=price_min,
            max_value=slider_max,
            value=(price_min, slider_max),
            step=1.0,
            key="pullback_price_range",
        )
    with col2:
        rsi_range = st.slider(
            "RSI range",
            min_value=max(0.0, rsi_min),
            max_value=min(100.0, max(rsi_max, rsi_min + 1)),
            value=(max(0.0, rsi_min), min(100.0, max(rsi_max, rsi_min + 1))),
            step=1.0,
            key="pullback_rsi_range",
        )
    with col3:
        min_volume = st.number_input(
            "Minimum latest volume",
            min_value=0,
            value=0,
            step=100_000,
            key="pullback_min_volume",
        )
    with col4:
        min_pattern_score = st.slider(
            "Minimum pattern score",
            min_value=0,
            max_value=65,
            value=40,
            step=5,
            key="pullback_min_pattern_score",
        )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        setup_filter = st.multiselect(
            "Setup type",
            options=setup_types,
            default=setup_types,
            key="pullback_setup_filter",
        )
    with col2:
        min_prior_hammers = st.number_input(
            "Minimum prior support hammers",
            min_value=0,
            max_value=5,
            value=0,
            step=1,
            key="pullback_min_prior_hammers",
        )
    with col3:
        hammer_only = st.checkbox("Latest hammer only", value=False, key="pullback_hammer_only")
    with col4:
        support_only = st.checkbox("Near support only", value=False, key="pullback_support_only")

    col1, col2 = st.columns(2)
    with col1:
        prior_rsi_only = st.checkbox("Prior RSI was elevated only", value=False, key="pullback_prior_rsi_only")
    with col2:
        sideways_only = st.checkbox("Sideways support setups only", value=False, key="pullback_sideways_only")

    filtered = results[
        (results["Price"].between(price_range[0], price_range[1]))
        & (results["RSI"].between(rsi_range[0], rsi_range[1]))
        & (results["Volume"] >= min_volume)
        & (results["Pattern Score"] >= min_pattern_score)
    ]
    if setup_filter:
        filtered = filtered[filtered["Setup Type"].isin(setup_filter)]
    if min_prior_hammers > 0:
        filtered = filtered[filtered["Prior Support Hammers"] >= min_prior_hammers]
    if hammer_only:
        filtered = filtered[filtered["Hammer"]]
    if support_only:
        filtered = filtered[filtered["Near Support"]]
    if prior_rsi_only:
        filtered = filtered[filtered["Prior RSI High"].notna()]
    if sideways_only:
        filtered = filtered[filtered["Setup Type"].str.contains("Sideways", na=False)]

    filtered = filtered.reset_index(drop=True)
    if filtered.empty:
        st.warning("No symbols match the current filters.")
        return

    hammer_count = int(filtered["Hammer"].sum())
    prior_hammer_symbols = int((filtered["Prior Support Hammers"] > 0).sum())
    st.caption(
        f"Showing {len(filtered)} of {len(results)} pullback matches · "
        f"{hammer_count} with latest hammer · {prior_hammer_symbols} with prior support hammers."
    )

    st.markdown("#### Stage 3 — Refine with MACD, ADX, and RSI")
    refine_col1, refine_col2, refine_col3 = st.columns(3)
    with refine_col1:
        refinement_rsi_min = st.number_input(
            "Refinement RSI min",
            min_value=0.0,
            max_value=100.0,
            value=30.0,
            step=1.0,
            key="pullback_refine_rsi_min",
        )
    with refine_col2:
        refinement_rsi_max = st.number_input(
            "Refinement RSI max",
            min_value=0.0,
            max_value=100.0,
            value=58.0,
            step=1.0,
            key="pullback_refine_rsi_max",
        )
    with refine_col3:
        min_total_score = st.slider(
            "Minimum total score after refinement",
            min_value=0,
            max_value=100,
            value=70,
            step=5,
            key="pullback_min_total_score",
        )

    refine_config = PullbackScanConfig(
        refinement_rsi_min=float(refinement_rsi_min),
        refinement_rsi_max=float(refinement_rsi_max),
    )

    if st.button("Refine & Score Filtered Shortlist", type="primary", key="pullback_refine_score"):
        with st.spinner(f"Refining {len(filtered)} symbols with MACD, ADX, and RSI..."):
            st.session_state.pullback_refined_results = _score_pullback_refinements(filtered, refine_config)

    display_source = st.session_state.get("pullback_refined_results")
    if display_source is not None and not display_source.empty:
        display_frame = display_source[display_source["Total Score"] >= min_total_score].reset_index(drop=True)
        st.caption(
            "Refinement adds up to 40 points: MACD reversal (15), ADX rising (15), RSI in pullback zone (10)."
        )
    else:
        display_frame = filtered
        st.info("Run Stage 3 refinement to add MACD, ADX, and RSI scoring to the filtered shortlist.")

    if display_frame.empty:
        st.warning("No symbols remain after the total-score threshold.")
        return

    display = display_frame.copy()
    for column in ("Hammer", "Near Support", "MACD Reversal", "ADX Rising", "RSI In Pullback Zone"):
        if column in display.columns and display[column].dtype == bool:
            display[column] = display[column].map({True: "Yes", False: "No"})

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
            "Volume": st.column_config.NumberColumn("Volume", format="%d"),
            "Avg Volume 20D": st.column_config.NumberColumn("Avg Volume 20D", format="%d"),
            "RSI": st.column_config.NumberColumn("RSI", format="%.2f"),
            "Prior RSI High": st.column_config.NumberColumn("Prior RSI High", format="%.2f"),
            "MA20": st.column_config.NumberColumn("MA20", format="$%.2f"),
            "MA40": st.column_config.NumberColumn("MA40", format="$%.2f"),
            "Distance to MA20 %": st.column_config.NumberColumn("Distance to MA20 %", format="%.2f%%"),
            "Support Level": st.column_config.NumberColumn("Support Level", format="$%.2f"),
            "Distance to Support %": st.column_config.NumberColumn("Distance to Support %", format="%.2f%%"),
            "Range Position %": st.column_config.NumberColumn("Range Position %", format="%.2f%%"),
            "Pattern Score": st.column_config.NumberColumn("Pattern Score", format="%d"),
            "Refinement Score": st.column_config.NumberColumn("Refinement Score", format="%d"),
            "Total Score": st.column_config.NumberColumn("Total Score", format="%d"),
            "MACD": st.column_config.NumberColumn("MACD", format="%.4f"),
            "MACD Signal": st.column_config.NumberColumn("MACD Signal", format="%.4f"),
            "MACD Hist": st.column_config.NumberColumn("MACD Hist", format="%.4f"),
            "ADX": st.column_config.NumberColumn("ADX", format="%.2f"),
        },
    )

    if hammer_count:
        st.success(
            f"{hammer_count} filtered symbol(s) show a latest hammer candle, suggesting buyers defended the pullback."
        )
    if prior_hammer_symbols:
        st.info(
            f"{prior_hammer_symbols} symbol(s) also had earlier hammer candles testing support, "
            "which can strengthen the reversal case."
        )

    add_symbols = st.multiselect(
        "Add filtered symbols to favorites",
        options=display_frame["Ticker"].tolist(),
        default=[],
        key="pullback_add_favorites",
    )
    if st.button("Add Selected to Favorites", disabled=not add_symbols, key="pullback_save_favorites"):
        current_favorites = list(st.session_state.watchlist)
        st.session_state.watchlist = save_favorite_symbols([*current_favorites, *add_symbols])
        st.success(f"Added {len(add_symbols)} symbol(s) to favorites.")


def _score_pullback_refinements(filtered: pd.DataFrame, config: PullbackScanConfig) -> pd.DataFrame:
    """Score filtered pullback matches with MACD, ADX, and RSI refinement."""
    rows = []
    progress = st.progress(0.0, text="Starting pullback refinement...")
    status = st.empty()

    for index, row in filtered.reset_index(drop=True).iterrows():
        symbol = row["Ticker"]
        status.caption(f"Refining {symbol} ({index + 1}/{len(filtered)})")
        progress.progress((index + 1) / len(filtered), text=f"Refining {symbol}...")

        try:
            history = alpha_vantage_provider.get_price_history(symbol, periods=config.history_periods, timeframe="Daily")
            refined = score_pullback_refinement(history, row.to_dict(), config)
        except Exception as exc:  # noqa: BLE001
            refined = {
                **row.to_dict(),
                "Refinement Score": 0,
                "Total Score": int(row.get("Pattern Score", 0) or 0),
                "MACD Reversal": False,
                "ADX Rising": False,
                "RSI In Pullback Zone": False,
                "Stage 3 Notes": _short_unavailable_reason(str(exc)),
            }
        rows.append(refined)

    progress.empty()
    status.empty()
    if not rows:
        return pd.DataFrame(rows)
    return (
        pd.DataFrame(rows)
        .sort_values(["Total Score", "Hammer", "Prior Support Hammers"], ascending=[False, False, False])
        .reset_index(drop=True)
    )


def _volume_surge_scan() -> None:
    """Placeholder for unusual-volume scans."""
    st.markdown("**Volume surge scan**")
    st.caption("Find symbols with abnormal volume that may signal institutional participation.")
    st.info(
        "Planned criteria: today's volume at least 2x the 20-day average, "
        "price change above a minimum threshold, and liquidity filter for tradable names."
    )
    st.markdown(
        """
**Example workflow (coming next)**

1. Compare latest volume to the 20-day average.
2. Filter out illiquid symbols below a minimum average volume.
3. Require a minimum absolute or percentage price move.
4. Rank by volume ratio and price change together.
"""
    )


def _render_universe_manager() -> None:
    """Manage the saved stock universe used by scanners."""
    status = universe_file_status()
    with st.expander("Symbol CSV file", expanded=not status["exists"]):
        if status["exists"]:
            st.success(f"Loaded **{status['count']:,}** symbols from `{status['path']}`.")
            if status.get("parse_method") == "lenient_text":
                st.info(
                    "The symbol file was read in lenient mode because it is not a strict one-column CSV. "
                    "Use **Rewrite as clean CSV** to save one symbol per row."
                )
                if st.button("Rewrite as clean CSV", key="scan_rewrite_universe_csv"):
                    cleaned = save_stock_universe(load_stock_universe())
                    st.success(f"Saved {len(cleaned):,} symbols in clean CSV format.")
                    st.rerun()
        else:
            st.warning(f"No symbol file found yet. Add or upload a CSV at `{status['path']}`.")

        uploaded = st.file_uploader(
            "Upload symbol CSV",
            type=["csv"],
            help="Use one `symbol` column, or a one-column CSV where the first column contains symbols.",
            key="scan_universe_upload",
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
            key="scan_bottom_price_range",
        )
    with col2:
        min_volume = st.number_input(
            "Minimum volume",
            min_value=0,
            value=0,
            step=100_000,
            key="scan_bottom_min_volume",
        )
    with col3:
        max_rsi = st.slider(
            "Maximum RSI",
            min_value=0.0,
            max_value=100.0,
            value=100.0,
            step=1.0,
            key="scan_bottom_max_rsi",
        )

    sector_options = sorted(sector for sector in screener["Sector"].dropna().unique() if sector and sector != "Unknown")
    market_options = sorted(market for market in screener["Market"].dropna().unique() if market and market != "Unknown")
    sector_filter = st.multiselect(
        "Sector filter",
        options=sector_options,
        default=sector_options,
        help="Sector is filled when Alpha Vantage company overview is available for the scanned symbol.",
        key="scan_bottom_sector_filter",
    )
    market_filter = st.multiselect(
        "Market filter",
        options=market_options,
        default=market_options,
        key="scan_bottom_market_filter",
    )

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

    if st.button("Score Current Filtered Shortlist", key="scan_bottom_run_stage3"):
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
