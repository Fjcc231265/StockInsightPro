"""Local stock universe loading and CSV import for screeners."""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

STOCK_UNIVERSE_FILE = Path(__file__).resolve().parents[1] / "data" / "rsi_screener_symbols.csv"
UNIVERSE_COLUMNS = ["symbol"]
_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9./-]{0,9}$")
_SYMBOL_COLUMN_ALIASES = ("symbol", "ticker", "sym", "symbols", "tickers", "código", "codigo")
_NAME_HEADERS = {"name", "company", "company name", "security name"}
_EXCLUDED_TOKENS = {
    "SYMBOL",
    "TICKER",
    "NAME",
    "LAST",
    "SALE",
    "CHANGE",
    "MARKET",
    "CAP",
    "COUNTRY",
    "IPO",
    "YEAR",
    "VOLUME",
    "SECTOR",
    "INDUSTRY",
    "AND",
    "OR",
    "THE",
    "COMMON",
    "STOCK",
    "CLASS",
    "HOLDINGS",
    "INC",
    "CORP",
    "LTD",
    "PLC",
}


def load_stock_universe() -> pd.DataFrame:
    """Load the saved stock universe from disk."""
    if not STOCK_UNIVERSE_FILE.exists():
        return pd.DataFrame(columns=UNIVERSE_COLUMNS)

    try:
        raw_text = STOCK_UNIVERSE_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return pd.DataFrame(columns=UNIVERSE_COLUMNS)

    # Prefer an already-cleaned one-column symbol file when present.
    try:
        frame = pd.read_csv(io.StringIO(raw_text))
        columns_lower = {str(column).strip().lower() for column in frame.columns}
        if list(frame.columns) == ["symbol"] or "symbol" in columns_lower:
            normalized = _normalize_universe_frame(frame)
            if not normalized.empty:
                normalized.attrs["parse_method"] = "clean_symbol_csv"
                return normalized
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError):
        pass

    symbols, parse_method = _extract_symbols(raw_text)
    universe = pd.DataFrame({"symbol": symbols})
    universe.attrs["parse_method"] = parse_method
    return universe


def save_stock_universe(universe: pd.DataFrame) -> pd.DataFrame:
    """Persist the stock universe to disk."""
    normalized = _normalize_universe_frame(universe)
    STOCK_UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(STOCK_UNIVERSE_FILE, index=False)
    return normalized


def import_stock_universe_csv(uploaded: pd.DataFrame | str | bytes) -> pd.DataFrame:
    """Import a user-provided CSV or text universe containing symbols and save to disk."""
    if isinstance(uploaded, pd.DataFrame):
        universe = _normalize_universe_frame(uploaded)
        if universe.empty:
            raise ValueError("No valid symbols were found in the Symbol/Ticker column.")
        universe.attrs["source"] = "User CSV import"
        universe.attrs["parse_method"] = "pandas_frame"
        return save_stock_universe(universe)

    if isinstance(uploaded, bytes):
        raw_text = uploaded.decode("utf-8", errors="replace")
    else:
        raw_text = str(uploaded)

    # Strip UTF-8 BOM from Excel/Nasdaq exports.
    raw_text = raw_text.lstrip("\ufeff")

    symbols, parse_method = _extract_symbols(raw_text)
    if not symbols:
        raise ValueError(
            "No valid symbols were found. Use a CSV with a Symbol or Ticker column "
            "(Name/company columns are ignored)."
        )

    universe = pd.DataFrame({"symbol": symbols})
    universe.attrs["source"] = "User CSV import"
    universe.attrs["parse_method"] = parse_method
    return save_stock_universe(universe)


def get_stock_universe_symbols() -> list[str]:
    """Return symbols from the saved universe file."""
    universe = load_stock_universe()
    if universe.empty:
        return []

    return list(dict.fromkeys(universe["symbol"].dropna().astype(str).str.upper().tolist()))


def universe_file_status() -> dict:
    """Return metadata about the on-disk universe file."""
    if not STOCK_UNIVERSE_FILE.exists():
        return {"exists": False, "count": 0, "path": str(STOCK_UNIVERSE_FILE)}
    universe = load_stock_universe()
    modified = STOCK_UNIVERSE_FILE.stat().st_mtime
    return {
        "exists": True,
        "count": len(universe),
        "path": str(STOCK_UNIVERSE_FILE),
        "modified": modified,
        "parse_method": universe.attrs.get("parse_method", "unknown"),
    }


def _extract_symbols(raw_text: str) -> tuple[list[str], str]:
    """Extract ticker symbols, preferring a Symbol/Ticker column over free-text tokens."""
    tabular_symbols = _extract_symbols_from_tabular_csv(raw_text)
    if tabular_symbols:
        return tabular_symbols, "symbol_column"

    strict_symbols = _extract_symbols_strict_csv(raw_text)
    if strict_symbols:
        return strict_symbols, "strict_csv"

    # Lenient parsing is only for plain symbol lists, never for Name-heavy screener dumps.
    if _looks_like_named_screener_csv(raw_text):
        return [], "missing_symbol_column"

    lenient_symbols = _extract_symbols_lenient(raw_text)
    if lenient_symbols:
        return lenient_symbols, "lenient_text"
    return [], "empty"


def _extract_symbols_from_tabular_csv(raw_text: str) -> list[str]:
    """Read multi-column CSVs and keep only the Symbol/Ticker column."""
    for sep in (",", ";", "\t", "|"):
        try:
            frame = pd.read_csv(io.StringIO(raw_text), sep=sep, engine="python")
        except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError):
            continue
        if frame.empty or frame.shape[1] < 1:
            continue

        symbol_column = _resolve_symbol_column(frame)
        if symbol_column is None:
            # Multi-column file without Symbol/Ticker — do not invent tickers from Name.
            if frame.shape[1] > 1:
                continue
            symbol_column = frame.columns[0]

        renamed = frame[[symbol_column]].rename(columns={symbol_column: "symbol"})
        normalized = _normalize_universe_frame(renamed)
        if not normalized.empty:
            return normalized["symbol"].tolist()
    return []


def _resolve_symbol_column(frame: pd.DataFrame) -> str | None:
    """Return the Symbol/Ticker column name, never Name."""
    column_map = {str(column).strip().lower(): column for column in frame.columns}
    for alias in _SYMBOL_COLUMN_ALIASES:
        if alias in column_map:
            return column_map[alias]
    return None


def _looks_like_named_screener_csv(raw_text: str) -> bool:
    """Detect Nasdaq-style exports that include a Name column."""
    header = raw_text.splitlines()[0].upper() if raw_text.splitlines() else ""
    has_name = "NAME" in header
    has_symbol = any(token in header for token in ("SYMBOL", "TICKER"))
    return has_name and not has_symbol


def _extract_symbols_strict_csv(raw_text: str) -> list[str]:
    """Try pandas CSV parsing when the file is a valid one-column CSV."""
    try:
        frame = pd.read_csv(io.StringIO(raw_text), usecols=[0], header=0)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError, KeyError):
        try:
            frame = pd.read_csv(io.StringIO(raw_text), header=None, usecols=[0])
        except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError, KeyError):
            return []

    if frame.empty:
        return []

    first_header = str(frame.columns[0]).strip().lower()
    if first_header in _NAME_HEADERS:
        return []

    normalized = _normalize_universe_frame(frame.rename(columns={frame.columns[0]: "symbol"}))
    return normalized["symbol"].tolist()


def _extract_symbols_lenient(raw_text: str) -> list[str]:
    """Parse comma-separated or quoted symbol lists line by line."""
    symbols: list[str] = []
    for line in raw_text.splitlines():
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
        cleaned_line = cleaned_line.replace("'", " ").replace('"', " ")
        for token in re.split(r"[,;\s]+", cleaned_line):
            symbol = token.strip().upper()
            if _is_valid_symbol(symbol):
                symbols.append(symbol)
    return list(dict.fromkeys(symbols))


def _is_valid_symbol(symbol: str) -> bool:
    """Return True for simple US-style ticker tokens."""
    if not symbol or symbol in _EXCLUDED_TOKENS:
        return False
    if not _SYMBOL_PATTERN.fullmatch(symbol):
        return False
    if symbol.endswith(".") or symbol.startswith(".") or symbol.endswith("/") or symbol.startswith("/"):
        return False
    return True


def _normalize_universe_frame(universe: pd.DataFrame) -> pd.DataFrame:
    """Normalize universe columns for storage and filtering."""
    if universe.empty:
        return pd.DataFrame(columns=UNIVERSE_COLUMNS)

    symbol_column = _resolve_symbol_column(universe)
    if symbol_column is None:
        first_header = str(universe.columns[0]).strip().lower()
        if first_header in _NAME_HEADERS:
            return pd.DataFrame(columns=UNIVERSE_COLUMNS)
        symbol_column = universe.columns[0]

    normalized = pd.DataFrame({"symbol": universe[symbol_column].astype(str).str.strip().str.upper()})
    normalized = normalized[normalized["symbol"].apply(_is_valid_symbol)]
    normalized = normalized.drop_duplicates(subset=["symbol"], keep="first")
    return normalized[UNIVERSE_COLUMNS]
