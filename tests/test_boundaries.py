from trade_compliance.evaluator import (
    CONCENTRATION_REASON,
    INSUFFICIENT_CASH_REASON,
    INSUFFICIENT_HOLDINGS_REASON,
    evaluate_trade,
)
from trade_compliance.models import Decision, Holding, Portfolio
from tests.conftest import make_trade


def test_sell_exact_holding_equality_passes():
    portfolio = Portfolio("P1", 0, [], 1.0, [Holding("AAA", 50, 10)])
    result = evaluate_trade(make_trade(portfolio_id="P1", action="Sell", security_id="AAA", quantity=50, price=10), portfolio)
    assert result.decision == Decision.APPROVED


def test_sell_one_more_than_holding_fails():
    portfolio = Portfolio("P1", 0, [], 1.0, [Holding("AAA", 50, 10)])
    result = evaluate_trade(make_trade(portfolio_id="P1", action="Sell", security_id="AAA", quantity=51, price=10), portfolio)
    assert result.decision == Decision.REJECTED
    assert result.reason == INSUFFICIENT_HOLDINGS_REASON


def test_buy_exact_cash_equality_passes():
    portfolio = Portfolio("P1", 500, [], 1.0, [])
    result = evaluate_trade(make_trade(portfolio_id="P1", action="Buy", security_id="AAA", quantity=5, price=100), portfolio)
    assert result.decision == Decision.APPROVED


def test_buy_one_cent_over_cash_fails():
    portfolio = Portfolio("P1", 499.99, [], 1.0, [])
    result = evaluate_trade(make_trade(portfolio_id="P1", action="Buy", security_id="AAA", quantity=5, price=100), portfolio)
    assert result.decision == Decision.REJECTED
    assert result.reason == INSUFFICIENT_CASH_REASON


def test_concentration_exact_cap_passes():
    # total = cash + e*price + other = 10000 + 0 + 5000 = 15000
    # qty 33 @150 => 4950/15000 = 0.33 exactly
    portfolio = Portfolio("P1", 10_000, [], 0.33, [Holding("BOND1", 50, 100)])
    result = evaluate_trade(make_trade(portfolio_id="P1", action="Buy", security_id="AAA", quantity=33, price=150), portfolio)
    assert result.decision == Decision.APPROVED


def test_concentration_just_over_cap_needs_signoff():
    portfolio = Portfolio("P1", 10_000, [], 0.33, [Holding("BOND1", 50, 100)])
    result = evaluate_trade(make_trade(portfolio_id="P1", action="Buy", security_id="AAA", quantity=34, price=150), portfolio)
    assert result.decision == Decision.NEEDS_MANUAL_SIGN_OFF
    assert result.reason == CONCENTRATION_REASON


def test_concentration_uses_trade_price_for_security_and_market_price_for_others():
    # Existing AAA holding has market_price 999 (should be ignored for AAA post-trade value)
    # because step 5 uses trade price for this security. Other holding uses its own market_price.
    portfolio = Portfolio(
        "P1",
        cash_balance=1_000,
        restricted_securities=[],
        max_position_pct=0.50,
        current_holdings=[Holding("AAA", 1, 999), Holding("BBB", 10, 10)],
    )
    # Buy 1 AAA @100: post_cash 900, post_qty 2, post_value AAA = 2*100=200, other BBB=100, total 1200, pct 0.166.. approved
    result = evaluate_trade(make_trade(portfolio_id="P1", action="Buy", security_id="AAA", quantity=1, price=100), portfolio)
    assert result.decision == Decision.APPROVED
