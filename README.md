# Trade Compliance Checker

## Overview

This project implements the Portfolio Trade Order Compliance & Execution Checker described in [trade_compliance_requirements.md](trade_compliance_requirements.md). It evaluates proposed trades in strict Step 1-6 order and returns `(decision, reason)` for each trade.

## Project Layout

- [trade_compliance/models.py](trade_compliance/models.py) - domain models (`Trade`, `Holding`, `Portfolio`, `TradeResult`, `Decision`)
- [trade_compliance/evaluator.py](trade_compliance/evaluator.py) - compliance rules, short-circuit evaluation, optional stateful application
- [trade_compliance/loader.py](trade_compliance/loader.py) - CSV parser and reference portfolio JSON loader
- [reference_portfolios.json](reference_portfolios.json) - sample reference portfolio data for POR001-POR005
- [trade_compliance/cli.py](trade_compliance/cli.py) - CLI formatting/output
- [run_compliance.py](run_compliance.py) - runnable script for [trades_test.csv](trades_test.csv)
- [tests/](tests/) - pytest suite covering ordering, boundaries, invalid inputs, restricted securities, concentration behavior, and state modes

## Requirements

- Python 3.10+ (dataclass/type-hint syntax used)
- pytest for tests

Install test dependency:

```powershell
py -3 -m pip install -r requirements-dev.txt
```

## Run CLI

Static snapshot mode (default, documented assumption):

```powershell
py -3 run_compliance.py --csv trades_test.csv
```

Stateful mode (approved trades mutate portfolio cash/holdings sequentially):

```powershell
py -3 run_compliance.py --csv trades_test.csv --stateful
```

The CLI prints one line per trade with the resulting `(decision, reason)` tuple.

## Run Tests

```powershell
py -3 -m pytest -q
```

## Reference Data (POR001-POR005)

Reference portfolios are stored in [reference_portfolios.json](reference_portfolios.json) and loaded by `build_reference_portfolios()` / `load_reference_portfolios()` in [trade_compliance/loader.py](trade_compliance/loader.py). They are sample data designed so the 20 rows in [trades_test.csv](trades_test.csv) exercise all required branches.

| Portfolio | Cash | Restricted | Max Position % | Holdings (security_id, qty, market_price) |
|---|---:|---|---:|---|
| POR001 | 100000 | XYZCORP | 0.40 | AAPL 100@150; TCS 50@310 |
| POR002 | 20000 | - | 0.50 | none |
| POR003 | 50000 | BADCO | 0.30 | RELIANCE 30@2400; TCS 10@300 |
| POR004 | 50000 | - | 0.50 | GOOGL 5@2000 |
| POR005 | 10000 | - | 0.335 | BOND1 50@100 |

## Assumptions

- **Static snapshot by default**. Each trade is evaluated against the original portfolio reference state. This matches a batch pre-trade compliance check where proposed trades are independently assessed before execution. The evaluator also supports `mutate_portfolio=True` for sequential/stateful evaluation; tests cover both modes.
- **Stateful mutation semantics** (only when `mutate_portfolio=True`): only `Approved` trades mutate state. Buy: `cash_balance -= qty*price`, holding quantity increases, and holding `market_price` is set to trade price. Sell: `cash_balance += qty*price`, holding quantity decreases, and zero-quantity holdings are removed. Rejected/Needs Manual Sign-off trades do not mutate state.
- **Step 1 validation** rejects non-positive/non-numeric/boolean quantity or price and any action outside `{Buy, Sell}` with reason `Invalid trade data.`.
- **Unknown portfolio** is treated as a lookup failure before rule evaluation and rejected with `Unknown portfolio: <id>`. The provided CSV only contains POR001-POR005.
- **Concentration formula** follows the requirement exactly: post-trade value for the traded security uses trade price; other holdings use their stored `market_price`; exact equality to `max_position_pct` passes.
- **Sell orders skip Step 5 completely**, even if they would otherwise be over a concentration cap.

## Expected trades_test.csv Decisions (Static Snapshot)

| Row | Portfolio | Security | Action | Qty | Price | Decision | Reason |
|---:|---|---|---|---:|---:|---|---|
| 1 | POR001 | AAPL | Buy | 20 | 150 | Approved | Approved. |
| 2 | POR001 | AAPL | Buy | 60 | 150 | Approved | Approved. |
| 3 | POR001 | TCS | Sell | 50 | 310 | Approved | Approved. |
| 4 | POR001 | TCS | Sell | 60 | 310 | Rejected | Insufficient holdings to sell. |
| 5 | POR001 | XYZCORP | Buy | 10 | 50 | Rejected | Security is restricted for this portfolio. |
| 6 | POR001 | AAPL | Buy | 400 | 150 | Needs Manual Sign-off | Exceeds maximum position concentration — requires approval. |
| 7 | POR001 | AAPL | Buy | -10 | 150 | Rejected | Invalid trade data. |
| 8 | POR001 | INFY | Buy | 10 | 1500 | Approved | Approved. |
| 9 | POR002 | GOOGL | Buy | 5 | 2000 | Approved | Approved. |
| 10 | POR003 | BADCO | Buy | 10 | 100 | Rejected | Security is restricted for this portfolio. |
| 11 | POR003 | TCS | Buy | 5 | 300 | Approved | Approved. |
| 12 | POR003 | INFY | Buy | 50 | 1500 | Rejected | Insufficient cash for this buy order. |
| 13 | POR003 | RELIANCE | Sell | 30 | 2400 | Approved | Approved. |
| 14 | POR003 | RELIANCE | Sell | 31 | 2400 | Rejected | Insufficient holdings to sell. |
| 15 | POR004 | GOOGL | Buy | 10 | 2000 | Approved | Approved. |
| 16 | POR004 | AAPL | Buy | 300 | 150 | Needs Manual Sign-off | Exceeds maximum position concentration — requires approval. |
| 17 | POR005 | PENNY1 | Buy | 5 | 10 | Approved | Approved. |
| 18 | POR005 | AAPL | Buy | 33 | 150 | Approved | Approved. |
| 19 | POR005 | AAPL | Buy | 34 | 150 | Needs Manual Sign-off | Exceeds maximum position concentration — requires approval. |
| 20 | POR005 | TCS | Buy | 20 | 250 | Approved | Approved. |
