"""Command-line interface for trade compliance checking."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .evaluator import evaluate_trades
from .loader import build_reference_portfolios, load_trades


def format_result_row(index: int, trade, result) -> str:
    return (
        f"{index:>2}. portfolio={trade.portfolio_id} security={trade.security_id} "
        f"action={trade.action} qty={trade.quantity} price={trade.price} "
        f"type={trade.security_type} => ({result.decision.value}, {result.reason})"
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Evaluate trade compliance decisions.")
    parser.add_argument(
        "--csv",
        default="trades_test.csv",
        help="Path to trades CSV (default: trades_test.csv)",
    )
    parser.add_argument(
        "--stateful",
        action="store_true",
        help="Apply approved trades sequentially instead of static snapshot evaluation.",
    )
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    trades = load_trades(csv_path)
    portfolios = build_reference_portfolios()
    results = evaluate_trades(trades, portfolios, mutate_portfolio=args.stateful)

    mode = "stateful (approved trades mutate portfolio state)" if args.stateful else "static snapshot (each trade evaluated against original portfolio state)"
    print(f"Trade Compliance Results - {csv_path.name}")
    print(f"Mode: {mode}")
    print("-" * 100)
    for i, result in enumerate(results, start=1):
        print(format_result_row(i, result.trade, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
