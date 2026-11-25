"""Domain models for the trade compliance checker."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Action(str, Enum):
    BUY = "Buy"
    SELL = "Sell"


class Decision(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    NEEDS_MANUAL_SIGN_OFF = "Needs Manual Sign-off"


@dataclass
class Holding:
    security_id: str
    quantity: float
    market_price: float


@dataclass
class Portfolio:
    portfolio_id: str
    cash_balance: float
    restricted_securities: List[str] = field(default_factory=list)
    max_position_pct: float = 0.0
    current_holdings: List[Holding] = field(default_factory=list)

    def holding_for(self, security_id: str) -> Holding | None:
        for holding in self.current_holdings:
            if holding.security_id == security_id:
                return holding
        return None

    def holding_quantity(self, security_id: str) -> float:
        holding = self.holding_for(security_id)
        return holding.quantity if holding else 0.0


@dataclass
class Trade:
    portfolio_id: str
    security_id: str
    action: str
    quantity: float
    price: float
    security_type: str
    row_number: int | None = None


@dataclass
class TradeResult:
    trade: Trade
    decision: Decision
    reason: str

    def as_tuple(self) -> tuple[str, str]:
        return (self.decision.value, self.reason)
