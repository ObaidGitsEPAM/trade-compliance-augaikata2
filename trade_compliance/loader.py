"""CSV loading and reference portfolio data.

Assumptions
-----------
- trades_test.csv is evaluated against a static snapshot by default. The CLI
  reports this assumption explicitly.
- Reference portfolio data is loaded from reference_portfolios.json by default.
  The sample POR001-POR005 data is authored to exercise all rule branches
  present in trades_test.csv. Values are documented in README.md.
- CSV quantity/price are parsed as floats when possible; unparseable values are
  preserved as raw strings so Step 1 validation rejects them.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Holding, Portfolio, Trade

DEFAULT_REFERENCE_PORTFOLIOS_PATH = Path(__file__).resolve().parents[1] / "reference_portfolios.json"


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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _as_number(value: object, field: str) -> float | int:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be a number")
    return value


def _portfolio_from_dict(data: object) -> Portfolio:
    _require(isinstance(data, dict), "Portfolio entry must be an object")
    portfolio_id = data.get("portfolio_id")
    _require(isinstance(portfolio_id, str) and portfolio_id.strip(), "portfolio_id must be a non-empty string")

    cash_balance = _as_number(data.get("cash_balance"), f"{portfolio_id}.cash_balance")
    max_position_pct = _as_number(data.get("max_position_pct"), f"{portfolio_id}.max_position_pct")

    restricted = data.get("restricted_securities", [])
    _require(isinstance(restricted, list), f"{portfolio_id}.restricted_securities must be a list")
    _require(all(isinstance(item, str) for item in restricted), f"{portfolio_id}.restricted_securities must contain strings")

    holdings_raw = data.get("current_holdings", [])
    _require(isinstance(holdings_raw, list), f"{portfolio_id}.current_holdings must be a list")
    holdings: list[Holding] = []
    for idx, h in enumerate(holdings_raw):
        _require(isinstance(h, dict), f"{portfolio_id}.current_holdings[{idx}] must be an object")
        security_id = h.get("security_id")
        _require(isinstance(security_id, str) and security_id.strip(), f"{portfolio_id}.current_holdings[{idx}].security_id must be a non-empty string")
        quantity = _as_number(h.get("quantity"), f"{portfolio_id}.current_holdings[{idx}].quantity")
        market_price = _as_number(h.get("market_price"), f"{portfolio_id}.current_holdings[{idx}].market_price")
        holdings.append(Holding(security_id=security_id, quantity=float(quantity), market_price=float(market_price)))

    return Portfolio(
        portfolio_id=portfolio_id,
        cash_balance=float(cash_balance),
        restricted_securities=list(restricted),
        max_position_pct=float(max_position_pct),
        current_holdings=holdings,
    )


def load_reference_portfolios(path: str | Path | None = None) -> dict[str, Portfolio]:
    """Load portfolio reference data from a JSON file.

    The JSON may be either an object keyed by portfolio_id or a list of
    portfolio objects containing portfolio_id.
    """
    json_path = Path(path) if path is not None else DEFAULT_REFERENCE_PORTFOLIOS_PATH
    with json_path.open(encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    portfolios: dict[str, Portfolio] = {}
    if isinstance(payload, dict):
        entries = []
        for key, value in payload.items():
            _require(isinstance(value, dict), f"Portfolio '{key}' must be an object")
            value = {**value, "portfolio_id": value.get("portfolio_id", key)}
            entries.append(value)
    elif isinstance(payload, list):
        entries = payload
    else:
        raise ValueError("Reference portfolios JSON must be an object or a list")

    for entry in entries:
        portfolio = _portfolio_from_dict(entry)
        _require(portfolio.portfolio_id not in portfolios, f"Duplicate portfolio_id: {portfolio.portfolio_id}")
        portfolios[portfolio.portfolio_id] = portfolio
    return portfolios


def build_reference_portfolios(path: str | Path | None = None) -> dict[str, Portfolio]:
    """Load reference portfolios for POR001-POR005.

    Kept for backward compatibility. By default reads from
    reference_portfolios.json in the project root.
    """
    return load_reference_portfolios(path)
