from pathlib import Path

from trade_compliance.evaluator import evaluate_trades
from trade_compliance.loader import build_reference_portfolios, load_trades
from trade_compliance.models import Decision


WORKSPACE = Path(__file__).resolve().parents[1]
CSV_PATH = WORKSPACE / "trades_test.csv"


EXPECTED = [
    (Decision.APPROVED, "Approved."),
    (Decision.APPROVED, "Approved."),
    (Decision.APPROVED, "Approved."),
    (Decision.REJECTED, "Insufficient holdings to sell."),
    (Decision.REJECTED, "Security is restricted for this portfolio."),
    (Decision.NEEDS_MANUAL_SIGN_OFF, "Exceeds maximum position concentration — requires approval."),
    (Decision.REJECTED, "Invalid trade data."),
    (Decision.APPROVED, "Approved."),
    (Decision.APPROVED, "Approved."),
    (Decision.REJECTED, "Security is restricted for this portfolio."),
    (Decision.APPROVED, "Approved."),
    (Decision.REJECTED, "Insufficient cash for this buy order."),
    (Decision.APPROVED, "Approved."),
    (Decision.REJECTED, "Insufficient holdings to sell."),
    (Decision.APPROVED, "Approved."),
    (Decision.NEEDS_MANUAL_SIGN_OFF, "Exceeds maximum position concentration — requires approval."),
    (Decision.APPROVED, "Approved."),
    (Decision.APPROVED, "Approved."),
    (Decision.NEEDS_MANUAL_SIGN_OFF, "Exceeds maximum position concentration — requires approval."),
    (Decision.APPROVED, "Approved."),
]


def test_trades_test_csv_static_snapshot_decisions():
    trades = load_trades(CSV_PATH)
    portfolios = build_reference_portfolios()
    results = evaluate_trades(trades, portfolios, mutate_portfolio=False)
    actual = [(r.decision, r.reason) for r in results]
    assert len(actual) == 20
    assert actual == EXPECTED


def test_trades_test_csv_row_alignment():
    trades = load_trades(CSV_PATH)
    assert len(trades) == 20
    assert trades[0].portfolio_id == "POR001"
    assert trades[0].security_id == "AAPL"
    assert trades[-1].portfolio_id == "POR005"
    assert trades[-1].security_id == "TCS"
