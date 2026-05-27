from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class TickerSnapshot(BaseModel):
    ticker: str
    name: str
    sector: str
    price: float
    market_cap: float
    ttm_yield_pct: float
    lot_size: int
    div_history_5y: List[Optional[float]] = Field(default_factory=list)
    payout_ratio: Optional[float] = None
    price_vol_90d: Optional[float] = None


class ScoreBreakdown(BaseModel):
    sector: int = 0
    mcap: int = 0
    div_vol: int = 0
    payout: int = 0
    price_vol: int = 0

    def total(self) -> int:
        return min(100, self.sector + self.mcap + self.div_vol + self.payout + self.price_vol)


class UniverseEntry(BaseModel):
    ticker: str
    name: str
    sector: str
    price: float
    yield_pct: float
    score: int
    score_breakdown: ScoreBreakdown
    lot_size: int
    div_history_5y: List[Optional[float]]

    @classmethod
    def from_snapshot(cls, snap: TickerSnapshot, sb: ScoreBreakdown) -> "UniverseEntry":
        return cls(
            ticker=snap.ticker,
            name=snap.name,
            sector=snap.sector,
            price=snap.price,
            yield_pct=snap.ttm_yield_pct,
            score=sb.total(),
            score_breakdown=sb,
            lot_size=snap.lot_size,
            div_history_5y=snap.div_history_5y,
        )
