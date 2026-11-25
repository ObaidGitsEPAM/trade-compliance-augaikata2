"""CSV loading and reference portfolio data.

Assumptions
-----------
- trades_test.csv is evaluated against a static snapshot by default. The CLI
  reports this assumption explicitly.
- Reference data for POR001-POR005 is sample data authored to exercise all rule
  branches present in trades_test.csv. Values are documented in README.md.
- CSV quantity/price are parsed as floats when possible; unparseable values are
  preserved as raw strings so Step 1 validation rejects them.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .models import Holding, Portfolio, Trade


def _parse_number(raw: str) -> float | str:
    raw = raw.strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return raw
    # Keep integer-looking values as int for cleaner display, but float is fine.
    if value.is_integer():
        return int(value)
    return value


def load_trades(csv_path: str | Path) -> list[Trade]:
    path = Path(csv_path)
    trades: list[Trade] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=2):  # header is line 1
            trades.append(
                Trade(
                    portfolio_id=(row.get("portfolio_id") or "").strip(),
                    security_id=(row.get("security_id") or "").strip(),
                    action=(row.get("action") or "").strip(),
                    quantity=_parse_number(row.get("quantity", "")),
                    price=_parse_number(row.get("price", "")),
                    security_type=(row.get("security_type") or "").strip(),
                    row_number=index,
                )
            )
    return trades


def build_reference_portfolios() -> dict[str, Portfolio]:
    """Sample reference portfolios for POR001-POR005.

    These values are intentionally chosen so the 20 trades in trades_test.csv
    exercise validation, restriction, sell sufficiency/equality, buy
    affordability, concentration sign-off/equality, and approval branches.
    """
    return {
        "POR001": Portfolio(
            portfolio_id="POR001",
            cash_balance=100_000,
            restricted_securities=["XYZCORP"],
            max_position_pct=0.40,
            current_holdings=[
                Holding("AAPL", 100, 150),
                Holding("TCS", 50, 310),
            ],
        ),
        "POR002": Portfolio(
            portfolio_id="POR002",
            cash_balance=20_000,
            restricted_securities=[],
            max_position_pct=0.50,
            current_holdings=[],
        ),
        "POR003": Portfolio(
            portfolio_id="POR003",
            cash_balance=50_000,
            restricted_securities=["BADCO"],
            max_position_pct=0.30,
            current_holdings=[
                Holding("RELIANCE", 30, 2400),
                Holding("TCS", 10, 300),
            ],
        ),
        "POR004": Portfolio(
            portfolio_id="POR004",
            cash_balance=50_000,
            restricted_securities=[],
            max_position_pct=0.50,
            current_holdings=[
                Holding("GOOGL", 5, 2000),
            ],
        ),
        "POR005": Portfolio(
            portfolio_id="POR005",
            cash_balance=10_000,
            restricted_securities=[],
            max_position_pct=0.335,
            current_holdings=[
                Holding("BOND1", 50, 100),
            ],
        ),
    }
