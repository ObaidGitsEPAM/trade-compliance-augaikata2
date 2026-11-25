from copy import deepcopy

from trade_compliance.evaluator import evaluate_trades
from trade_compliance.models import Decision, Holding, Portfolio
from tests.conftest import make_trade


def test_static_snapshot_does_not_mutate_input_portfolios():
    portfolios = {
        "P1": Portfolio("P1", 1000, [], 1.0, [Holding("AAA", 1, 100)]),
    }
    original = deepcopy(portfolios)
    trades = [
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=2, price=100),
        make_trade(portfolio_id="P1", security_id="AAA", action="Sell", quantity=1, price=100),
    ]
    results = evaluate_trades(trades, portfolios, mutate_portfolio=False)
    assert [r.decision for r in results] == [Decision.APPROVED, Decision.APPROVED]
    assert portfolios == original


def test_static_snapshot_evaluates_each_trade_against_original_state():
    portfolios = {
        "P1": Portfolio("P1", 1000, [], 1.0, []),
    }
    trades = [
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=10, price=100),  # uses full cash
        make_trade(portfolio_id="P1", security_id="BBB", action="Buy", quantity=1, price=100),   # would fail in stateful
    ]
    results = evaluate_trades(trades, portfolios, mutate_portfolio=False)
    assert [r.decision for r in results] == [Decision.APPROVED, Decision.APPROVED]


def test_stateful_mode_applies_approved_trades_sequentially():
    portfolios = {
        "P1": Portfolio("P1", 1000, [], 1.0, []),
    }
    trades = [
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=10, price=100),  # approved, cash becomes 0
        make_trade(portfolio_id="P1", security_id="BBB", action="Buy", quantity=1, price=100),   # insufficient cash after first
    ]
    results = evaluate_trades(trades, portfolios, mutate_portfolio=True)
    assert results[0].decision == Decision.APPROVED
    assert results[1].decision == Decision.REJECTED
    assert results[1].reason == "Insufficient cash for this buy order."
    assert portfolios["P1"].cash_balance == 0
    assert portfolios["P1"].holding_quantity("AAA") == 10


def test_stateful_sell_updates_holdings_and_cash():
    portfolios = {
        "P1": Portfolio("P1", 0, [], 1.0, [Holding("AAA", 5, 100)]),
    }
    trades = [
        make_trade(portfolio_id="P1", security_id="AAA", action="Sell", quantity=3, price=100),
        make_trade(portfolio_id="P1", security_id="AAA", action="Sell", quantity=3, price=100),  # now only 2 left
    ]
    results = evaluate_trades(trades, portfolios, mutate_portfolio=True)
    assert results[0].decision == Decision.APPROVED
    assert results[1].decision == Decision.REJECTED
    assert results[1].reason == "Insufficient holdings to sell."
    assert portfolios["P1"].holding_quantity("AAA") == 2
    assert portfolios["P1"].cash_balance == 300


def test_stateful_does_not_mutate_on_rejected_or_signoff():
    portfolios = {
        "P1": Portfolio("P1", 200, [], 0.10, [Holding("OTHER", 10, 100)]),
    }
    original = deepcopy(portfolios["P1"])
    trades = [
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=2, price=100),  # concentration sign-off
        make_trade(portfolio_id="P1", security_id="MISSING", action="Sell", quantity=1, price=100),  # rejected
    ]
    results = evaluate_trades(trades, portfolios, mutate_portfolio=True)
    assert results[0].decision == Decision.NEEDS_MANUAL_SIGN_OFF
    assert results[1].decision == Decision.REJECTED
    assert portfolios["P1"] == original
