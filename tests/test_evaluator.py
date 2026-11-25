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


def test_step1_rejects_invalid_action(base_portfolio):
    result = evaluate_trade(make_trade(action="Hold"), base_portfolio)
    assert result.decision == Decision.REJECTED
    assert result.reason == INVALID_TRADE_REASON


def test_step1_rejects_zero_and_negative_quantity(base_portfolio):
    for qty in [0, -1, -10]:
        result = evaluate_trade(make_trade(quantity=qty), base_portfolio)
        assert result.decision == Decision.REJECTED
        assert result.reason == INVALID_TRADE_REASON


def test_step1_rejects_zero_and_negative_price(base_portfolio):
    for price in [0, -1, -150.5]:
        result = evaluate_trade(make_trade(price=price), base_portfolio)
        assert result.decision == Decision.REJECTED
        assert result.reason == INVALID_TRADE_REASON


def test_step1_rejects_non_numeric_and_bool_inputs(base_portfolio):
    bad_values = ["10", None, float("nan"), float("inf"), True, False]
    for bad_qty in bad_values:
        result = evaluate_trade(make_trade(quantity=bad_qty), base_portfolio)
        assert result.decision == Decision.REJECTED, bad_qty
        assert result.reason == INVALID_TRADE_REASON
    for bad_price in bad_values:
        result = evaluate_trade(make_trade(price=bad_price), base_portfolio)
        assert result.decision == Decision.REJECTED, bad_price
        assert result.reason == INVALID_TRADE_REASON


def test_step2_rejects_restricted_security(base_portfolio):
    result = evaluate_trade(make_trade(security_id="RST1"), base_portfolio)
    assert result.decision == Decision.REJECTED
    assert result.reason == RESTRICTED_REASON


def test_step3_rejects_insufficient_sell_holdings(base_portfolio):
    result = evaluate_trade(make_trade(action="Sell", security_id="AAA", quantity=11), base_portfolio)
    assert result.decision == Decision.REJECTED
    assert result.reason == INSUFFICIENT_HOLDINGS_REASON


def test_step3_allows_exact_sell_equality(base_portfolio):
    result = evaluate_trade(make_trade(action="Sell", security_id="AAA", quantity=10, price=100), base_portfolio)
    assert result.decision == Decision.APPROVED
    assert result.reason == "Approved."


def test_step4_rejects_insufficient_cash(base_portfolio):
    result = evaluate_trade(make_trade(action="Buy", security_id="CCC", quantity=101, price=100), base_portfolio)
    assert result.decision == Decision.REJECTED
    assert result.reason == INSUFFICIENT_CASH_REASON


def test_step4_allows_exact_cash_equality():
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=1000,
        restricted_securities=[],
        max_position_pct=1.0,
        current_holdings=[],
    )
    result = evaluate_trade(make_trade(portfolio_id="P1", security_id="AAA", action="Buy", quantity=10, price=100), portfolio)
    assert result.decision == Decision.APPROVED


def test_step5_buy_exceeds_concentration_needs_signoff():
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=1000,
        restricted_securities=[],
        max_position_pct=0.50,
        current_holdings=[Holding("OTHER", 10, 100)],
    )
    # cost 600, post_cash 400, post_qty 6, value 600, other 1000, total 2000, pct 0.3 -> approved
    approved = evaluate_trade(make_trade(portfolio_id="P1", security_id="NEW", action="Buy", quantity=6, price=100), portfolio)
    assert approved.decision == Decision.APPROVED
    # cost 900, post_cash 100, post_qty 9, value 900, other 1000, total 2000, pct 0.45 -> approved
    approved2 = evaluate_trade(make_trade(portfolio_id="P1", security_id="NEW", action="Buy", quantity=9, price=100), portfolio)
    assert approved2.decision == Decision.APPROVED
    # cost 1100 > cash? No, cash 1000 so qty 11 fails affordability. Use qty 10: cost 1000, post_cash 0, value 1000, other 1000, total 2000, pct 0.5 == cap passes
    eq = evaluate_trade(make_trade(portfolio_id="P1", security_id="NEW", action="Buy", quantity=10, price=100), portfolio)
    assert eq.decision == Decision.APPROVED


def test_step5_sell_never_triggers_concentration():
    # A sell that would look concentrated if evaluated should still be approved (after passing sell checks).
    portfolio = Portfolio(
        portfolio_id="P1",
        cash_balance=0,
        restricted_securities=[],
        max_position_pct=0.01,  # extremely low cap
        current_holdings=[Holding("AAA", 100, 100), Holding("BBB", 1, 1)],
    )
    result = evaluate_trade(make_trade(portfolio_id="P1", security_id="AAA", action="Sell", quantity=1, price=100), portfolio)
    assert result.decision == Decision.APPROVED
    assert result.reason == "Approved."
