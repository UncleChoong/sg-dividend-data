"""Risk scoring (0=safe, 100=risky) for SGX dividend tickers."""
from __future__ import annotations
from typing import List, Optional

from sg_dividend_data.models import TickerSnapshot, ScoreBreakdown

_SECTOR_BAND = {
    "Banks": (0, 5),
    "Utilities": (5, 15),
    "Telco": (10, 20),
    "REITs": (20, 35),
    "Business Trusts": (30, 45),
    "Industrials": (10, 25),
    "Consumer": (15, 30),
    "Healthcare": (15, 30),
    "Other": (15, 30),
}


def sector_points(sector: str) -> int:
    lo, hi = _SECTOR_BAND.get(sector, (15, 30))
    return (lo + hi) // 2


def mcap_points(market_cap: Optional[float]) -> int:
    if market_cap is None:
        return 20
    if market_cap <= 5e8:
        return 20
    if market_cap >= 5e9:
        return 0
    pct = (5e9 - market_cap) / (5e9 - 5e8)
    return int(round(20 * pct))


def div_vol_points(history: List[Optional[float]]) -> int:
    non_null = [h for h in history if h is not None]
    if not non_null:
        return 10

    # Check if array is strictly ascending (safe, no penalty for strictly rising)
    is_ascending = True
    for i in range(len(non_null) - 1):
        if non_null[i] >= non_null[i+1]:
            is_ascending = False
            break
    if is_ascending:
        if len(non_null) < len(history):
            return 10  # Missing data despite ascending
        else:
            return 0  # Complete and ascending

    # Not ascending: penalize for cuts and volatility
    pts = 0
    for i in range(len(history) - 1):
        cur = history[i]
        next_val = history[i + 1]
        if cur is not None and next_val is not None and cur < next_val:
            pts += 10
    if len(non_null) < len(history):
        pts += 10
    return min(25, pts)


def payout_points(ratio: Optional[float]) -> int:
    if ratio is None:
        return 10
    if ratio < 0.7:
        return 0
    if ratio < 0.9:
        return int(round(10 * (ratio - 0.7) / 0.2))
    if ratio < 1.0:
        return int(round(10 + 10 * (ratio - 0.9) / 0.1))
    return 25


def price_vol_points(vol: Optional[float]) -> int:
    if vol is None:
        return 5
    if vol <= 0.10:
        return 0
    if vol >= 0.50:
        return 15
    return int(round(15 * (vol - 0.10) / 0.40))


def score(snap: TickerSnapshot) -> ScoreBreakdown:
    return ScoreBreakdown(
        sector=sector_points(snap.sector),
        mcap=mcap_points(snap.market_cap),
        div_vol=div_vol_points(snap.div_history_5y),
        payout=payout_points(snap.payout_ratio),
        price_vol=price_vol_points(snap.price_vol_90d),
    )
