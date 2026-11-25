from trade_compliance.evaluator import (
    CONCENTRATION_REASON,
    INSUFFICIENT_CASH_REASON,
    INSUFFICIENT_HOLDINGS_REASON,
    INVALID_TRADE_REASON,
    RESTRICTED_REASON,
    evaluate_trade,
)
from trade_compliance.models import Decision, Holding, Portfolio
from tests.conftest import make_trade


def test_step1_short_circuits_before_restriction_and_concentration():
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=0,
        restricted_securities=["AAA"],
        max_position_pct=0.01,
        current_holdings=[],
    )
    # Invalid qty, also restricted, also unaffordable/concentrated if it got there.
    result = evaluate_trade(
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=-1, price=100),
        portfolio,
    )
    assert result.decision == Decision.REJECTED
    assert result.reason == INVALID_TRADE_REASON


def test_step2_short_circuits_before_sell_or_buy_checks():
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=0,
        restricted_securities=["AAA"],
        max_position_pct=1.0,
        current_holdings=[Holding("AAA", 1, 100)],
    )
    # Restricted sell with insufficient holdings - restriction should win (Step 2 before Step 3).
    sell_result = evaluate_trade(
        make_trade(portfolio_id="P1", security_id="AAA", action="Sell", quantity=999, price=100),
        portfolio,
    )
    assert sell_result.decision == Decision.REJECTED
    assert sell_result.reason == RESTRICTED_REASON

    # Restricted buy with insufficient cash - restriction should win (Step 2 before Step 4).
    buy_result = evaluate_trade(
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=999, price=100),
        portfolio,
    )
    assert buy_result.decision == Decision.REJECTED
    assert buy_result.reason == RESTRICTED_REASON


def test_step3_short_circuits_before_concentration_not_applicable_but_before_later_logic():
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=999999,
        restricted_securities=[],
        max_position_pct=0.0001,
        current_holdings=[Holding("AAA", 1, 100)],
    )
    # Sell with insufficient holdings - Step 3 rejects; Step 5 would never apply to sells anyway,
    # but ordering still matters: we must get Step 3 reason.
    result = evaluate_trade(
        make_trade(portfolio_id="P1", security_id="AAA", action="Sell", quantity=2, price=100),
        portfolio,
    )
    assert result.decision == Decision.REJECTED
    assert result.reason == INSUFFICIENT_HOLDINGS_REASON


def test_step4_short_circuits_before_concentration():
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=100,
        restricted_securities=[],
        max_position_pct=0.0001,  # would fail concentration if reached
        current_holdings=[],
    )
    result = evaluate_trade(
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=2, price=100),
        portfolio,
    )
    assert result.decision == Decision.REJECTED
    assert result.reason == INSUFFICIENT_CASH_REASON


def test_step5_evaluated_only_when_previous_steps_pass():
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=1000,
        restricted_securities=[],
        max_position_pct=0.10,
        current_holdings=[Holding("OTHER", 1, 100)],
    )
    # Passes steps 1-4 but fails concentration.
    result = evaluate_trade(
        make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=10, price=100),
        portfolio,
    )
    assert result.decision == Decision.NEEDS_MANUAL_SIGN_OFF
    assert result.reason == CONCENTRATION_REASON
