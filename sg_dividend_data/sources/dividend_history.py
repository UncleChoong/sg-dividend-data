"""Fetch 5-year dividend history for an SGX ticker via yfinance."""
from __future__ import annotations
import logging
from typing import List, Optional

import yfinance as yf

log = logging.getLogger(__name__)


def fetch_div_history(ticker: str) -> List[Optional[float]]:
    """Return the last 5 full calendar years of annual dividend totals.

    The returned list is **most-recent-first**: index 0 = latest full year,
    index 4 = five years ago.  Elements are None when data is unavailable.

    Args:
        ticker: bare SGX code, e.g. "D05".  The ".SI" suffix is added internally.

    Returns:
        List of length 5.  Values are in the ticker's native currency (SGD for
        most SGX-listed securities).
    """
    symbol = f"{ticker}.SI"
    try:
        t = yf.Ticker(symbol)
        divs = t.dividends
        if divs is None or len(divs) == 0:
            log.debug("yfinance: no dividend history for %s", symbol)
            return [None] * 5

        # Group by calendar year and sum all payments within each year.
        annual = divs.groupby(divs.index.year).sum()

        # The current (possibly incomplete) year could skew analysis — include
        # only full years.  We use the last 5 complete years (up to last year).
        import datetime
        current_year = datetime.date.today().year
        # Drop the current year if it appears (partial data)
        annual = annual[annual.index < current_year]

        latest = int(annual.index.max()) if len(annual) > 0 else None
        if latest is None:
            return [None] * 5

        # Build most-recent-first list of length 5.
        result: List[Optional[float]] = []
        for offset in range(5):
            yr = latest - offset
            val = annual.get(yr)
            result.append(float(val) if val is not None and float(val) > 0 else None)
        return result

    except Exception as exc:
        log.warning("yfinance: dividend history failed for %s: %s", ticker, exc)
        return [None] * 5
