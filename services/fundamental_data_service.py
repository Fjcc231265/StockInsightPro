"""Fundamental analysis data service facade."""

from __future__ import annotations

import pandas as pd

from data import mock_data
from data.providers import alpha_vantage_provider


def get_financial_statement(statement_type: str, ticker: str, period: str = "Annual") -> pd.DataFrame:
    """Return income, balance sheet, or cash flow statement."""
    if alpha_vantage_provider.is_configured():
        try:
            return alpha_vantage_provider.get_financial_statement(statement_type, ticker, period)
        except alpha_vantage_provider.AlphaVantageError:
            pass

    statement = mock_data.get_financial_statement(statement_type, ticker)
    statement.attrs["source"] = f"Mock fallback ({period})"
    statement.attrs["currency"] = "USD"
    return statement


def get_statement_variation(statement: pd.DataFrame) -> pd.DataFrame:
    """Return period-over-period percentage changes for a financial statement."""
    normalized = _normalize_statement_table(statement)
    period_columns = [column for column in normalized.columns if column != "Metric"]
    rows = []

    for _, statement_row in normalized.iterrows():
        row = {"Metric": statement_row["Metric"]}
        for i in range(len(period_columns) - 1):
            current_period = period_columns[i]
            prior_period = period_columns[i + 1]
            current = _parse_statement_number(statement_row[current_period])
            prior = _parse_statement_number(statement_row[prior_period])
            row[f"{current_period} vs {prior_period}"] = _format_variation(current, prior)
        rows.append(row)

    return pd.DataFrame(rows)


def get_income_statement_margins(statement: pd.DataFrame) -> pd.DataFrame:
    """Return selected P&L margins as a percentage of revenue."""
    normalized = _normalize_statement_table(statement)
    period_columns = [column for column in normalized.columns if column != "Metric"]
    metric_values = {
        row["Metric"]: {period: _parse_statement_number(row[period]) for period in period_columns}
        for _, row in normalized.iterrows()
    }
    revenue = metric_values.get("Revenue", {})
    margin_map = {
        "Gross Margin": "Gross Profit",
        "Operating Margin": "Operating Income",
        "EBITDA Margin": "EBITDA",
        "Pre-Tax Margin": "Income Before Tax",
        "Net Margin": "Net Income",
    }

    rows = []
    for margin_label, metric in margin_map.items():
        if metric not in metric_values:
            continue
        row = {"Metric": margin_label}
        for period in period_columns:
            row[period] = _format_margin(metric_values[metric].get(period), revenue.get(period))
        rows.append(row)

    return pd.DataFrame(rows)


def _normalize_statement_table(statement: pd.DataFrame) -> pd.DataFrame:
    """Ensure statement has a Metric column for calculations."""
    if "Metric" in statement.columns:
        return statement.copy()
    normalized = statement.reset_index()
    first_column = normalized.columns[0]
    return normalized.rename(columns={first_column: "Metric"})


def _parse_statement_number(value: object) -> float | None:
    """Parse display values from statement tables into floats."""
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def _format_variation(current: float | None, prior: float | None) -> str:
    """Format period-over-period percentage change."""
    if current is None or prior in (None, 0):
        return "-"
    return f"{((current - prior) / abs(prior)) * 100:+.2f}%"


def _format_margin(value: float | None, revenue: float | None) -> str:
    """Format margin percentage."""
    if value is None or revenue in (None, 0):
        return "-"
    return f"{(value / revenue) * 100:.2f}%"


def get_valuation_ratios(ticker: str) -> pd.DataFrame:
    """Return valuation ratio table."""
    # TODO: Replace with valuation analytics engine.
    return mock_data.get_valuation_ratios(ticker)


def get_growth_metrics() -> pd.DataFrame:
    """Return growth metrics."""
    return mock_data.get_growth_metrics()


def get_profitability_metrics() -> pd.DataFrame:
    """Return profitability metrics."""
    return mock_data.get_profitability_metrics()


def get_debt_liquidity() -> pd.DataFrame:
    """Return debt and liquidity metrics."""
    return mock_data.get_debt_liquidity()
