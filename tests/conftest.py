from copy import deepcopy

import pytest

from trade_compliance.models import Holding, Portfolio, Trade


@pytest.fixture
def base_portfolio() -> Portfolio:
    return Portfolio(
        portfolio_id="PORTEST",
        cash_balance=10_000,
        restricted_securities=["RST1"],
        max_position_pct=0.40,
        current_holdings=[
            Holding("AAA", 10, 100),
            Holding("BBB", 20, 50),
        ],
    )


def make_trade(**overrides) -> Trade:
    data = dict(
        portfolio_id="PORTEST",
        security_id="AAA",
        action="Buy",
        quantity=1,
        price=100,
        security_type="Equity",
        row_number=1,
    )
    data.update(overrides)
    return Trade(**data)


def clone_portfolio(portfolio: Portfolio) -> Portfolio:
    return deepcopy(portfolio)
