"""Trade compliance evaluation logic.

Assumptions
-----------
- Default evaluation mode is a static snapshot: each trade is evaluated against
  the portfolio state as provided, and trades do not mutate portfolio state.
- An optional stateful mode is supported for tests/callers that need it. In
  stateful mode, only Approved trades mutate portfolio cash and holdings.
  Approved Buy: cash_balance -= quantity * price; holding quantity += quantity
  (or a new holding is added with market_price=trade.price).
  Approved Sell: cash_balance += quantity * price; holding quantity -= quantity
  (holding removed when quantity reaches zero).
- Validation is applied before business-rule checks. A trade with non-numeric,
  non-positive, or missing quantity/price, or an action not in {Buy, Sell}, is
  rejected as "Invalid trade data."
- Portfolio lookup is outside the six compliance steps; an unknown portfolio is
  rejected with a clear reason before step evaluation.
"""

from __future__ import annotations

import math
from copy import deepcopy

from .models import Decision, Holding, Portfolio, Trade, TradeResult

VALID_ACTIONS = {"Buy", "Sell"}
INVALID_TRADE_REASON = "Invalid trade data."
RESTRICTED_REASON = "Security is restricted for this portfolio."
INSUFFICIENT_HOLDINGS_REASON = "Insufficient holdings to sell."
INSUFFICIENT_CASH_REASON = "Insufficient cash for this buy order."
CONCENTRATION_REASON = "Exceeds maximum position concentration — requires approval."


def is_valid_trade(trade: Trade) -> bool:
    """Step 1 validation."""
    if not isinstance(trade.action, str) or trade.action not in VALID_ACTIONS:
        return False
    quantity = trade.quantity
    price = trade.price
    if not isinstance(quantity, (int, float)) or isinstance(quantity, bool):
        return False
    if not isinstance(price, (int, float)) or isinstance(price, bool):
        return False
    if not math.isfinite(float(quantity)) or not math.isfinite(float(price)):
        return False
    if quantity <= 0 or price <= 0:
        return False
    return True


def evaluate_trade(trade: Trade, portfolio: Portfolio) -> TradeResult:
    """Evaluate a single trade against a portfolio in strict step order."""
    # Step 1 — Validate
    if not is_valid_trade(trade):
        return TradeResult(trade, Decision.REJECTED, INVALID_TRADE_REASON)

    # Step 2 — Restricted security check
    if trade.security_id in portfolio.restricted_securities:
        return TradeResult(trade, Decision.REJECTED, RESTRICTED_REASON)

    # Step 3 — Sell check
    if trade.action == "Sell":
        held_quantity = portfolio.holding_quantity(trade.security_id)
        if held_quantity < trade.quantity:
            return TradeResult(trade, Decision.REJECTED, INSUFFICIENT_HOLDINGS_REASON)

    # Step 4 — Buy affordability check
    if trade.action == "Buy":
        cost = trade.quantity * trade.price
        if cost > portfolio.cash_balance:
            return TradeResult(trade, Decision.REJECTED, INSUFFICIENT_CASH_REASON)

    # Step 5 — Position concentration check (Buy only)
    if trade.action == "Buy":
        post_trade_cash = portfolio.cash_balance - (trade.quantity * trade.price)
        existing_quantity = portfolio.holding_quantity(trade.security_id)
        post_trade_quantity = existing_quantity + trade.quantity
        post_trade_value_of_this_security = post_trade_quantity * trade.price
        value_of_other_holdings = sum(
            h.quantity * h.market_price
            for h in portfolio.current_holdings
            if h.security_id != trade.security_id
        )
        total_portfolio_value_after = (
            post_trade_cash + post_trade_value_of_this_security + value_of_other_holdings
        )
        # Defensive guard: pathological zero/negative total should not approve.
        if total_portfolio_value_after <= 0:
            return TradeResult(trade, Decision.NEEDS_MANUAL_SIGN_OFF, CONCENTRATION_REASON)
        position_pct = post_trade_value_of_this_security / total_portfolio_value_after
        if position_pct > portfolio.max_position_pct:
            return TradeResult(trade, Decision.NEEDS_MANUAL_SIGN_OFF, CONCENTRATION_REASON)

    # Step 6 — Otherwise
    return TradeResult(trade, Decision.APPROVED, "Approved.")


def apply_approved_trade(trade: Trade, portfolio: Portfolio) -> None:
    """Mutate portfolio state for an approved trade (stateful mode only)."""
    if trade.action == "Buy":
        portfolio.cash_balance -= trade.quantity * trade.price
        holding = portfolio.holding_for(trade.security_id)
        if holding is None:
            portfolio.current_holdings.append(
                Holding(
                    security_id=trade.security_id,
                    quantity=trade.quantity,
                    market_price=trade.price,
                )
            )
        else:
            holding.quantity += trade.quantity
            # Assumption: trade price is used as the latest market price for this holding.
            holding.market_price = trade.price
    elif trade.action == "Sell":
        portfolio.cash_balance += trade.quantity * trade.price
        holding = portfolio.holding_for(trade.security_id)
        if holding is None:
            return
        holding.quantity -= trade.quantity
        if holding.quantity == 0:
            portfolio.current_holdings = [
                h for h in portfolio.current_holdings if h.security_id != trade.security_id
            ]


def evaluate_trades(
    trades: list[Trade],
    portfolios: dict[str, Portfolio],
    *,
    mutate_portfolio: bool = False,
) -> list[TradeResult]:
    """Evaluate trades against portfolio reference data.

    By default, portfolios are evaluated as a static snapshot: every trade sees
    the original portfolio state. Set mutate_portfolio=True for sequential
    stateful evaluation where approved trades update the portfolio.
    """
    state = portfolios if mutate_portfolio else {k: deepcopy(v) for k, v in portfolios.items()}
    results: list[TradeResult] = []
    for trade in trades:
        portfolio = state.get(trade.portfolio_id)
        if portfolio is None:
            results.append(
                TradeResult(
                    trade,
                    Decision.REJECTED,
                    f"Unknown portfolio: {trade.portfolio_id}",
                )
            )
            continue
        result = evaluate_trade(trade, portfolio)
        if mutate_portfolio and result.decision == Decision.APPROVED:
            apply_approved_trade(trade, portfolio)
        results.append(result)
    return results
