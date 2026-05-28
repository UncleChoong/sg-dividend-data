"""Fetch SGX quote data via yfinance (Yahoo Finance JSON API)."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)


@dataclass
class YahooQuote:
    price: float
    market_cap: Optional[float]
    ttm_yield_pct: Optional[float]
    beta: Optional[float]
    # Identity + descriptive metadata pulled from yfinance.info — used as a
    # fallback when the ticker isn't in our hand-curated enrichment dict.
    long_name: Optional[str] = None
    yf_sector: Optional[str] = None
    yf_industry: Optional[str] = None
    long_business_summary: Optional[str] = None
    # Trading currency reported by yfinance (e.g. "SGD", "USD"). Critical
    # for sg-dividend-data because a number of SGX-listed names (Jardine
    # Matheson J36, Hongkong Land H78, etc.) trade in USD — treating their
    # SGD-prefixed prices/market-caps as such is a real bug, not a label
    # nit. The refresh pipeline filters non-SGD names out of the universe.
    currency: Optional[str] = None
    # Date (ISO YYYY-MM-DD) of the most recent dividend payment, if any.
    # Used to filter out "zombie payers" — companies that yfinance still
    # reports a historical dividendYield for, but which actually stopped
    # paying years ago (e.g. AWK Fuxing China, last paid 2011).
    last_dividend_date: Optional[str] = None


def fetch_quote(ticker: str) -> YahooQuote:
    """Fetch price, market-cap, TTM yield, beta and descriptive metadata for
    an SGX ticker.

    Args:
        ticker: bare SGX code, e.g. "D05".  The ".SI" suffix is added internally.

    Returns:
        YahooQuote dataclass.

    Raises:
        ValueError: if price cannot be determined (ticker not found / delisted).
    """
    symbol = f"{ticker}.SI"
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info

        # price — required
        price = fi.last_price
        if price is None or price <= 0:
            raise ValueError(f"yfinance: no price for {symbol}")

        # market cap — optional
        try:
            mcap: Optional[float] = float(fi["marketCap"]) if fi["marketCap"] else None
        except Exception:
            mcap = None

        # All other metadata comes from the (slower) info dict. Pull it once.
        info: dict = {}
        try:
            info = t.info or {}
        except Exception:
            info = {}

        ttm_yield_pct: Optional[float] = _resolve_yield(t, price, info)

        beta: Optional[float] = None
        try:
            raw_beta = info.get("beta")
            if raw_beta is not None:
                beta = float(raw_beta)
        except Exception:
            pass

        long_name = info.get("longName") or info.get("shortName")
        if isinstance(long_name, str):
            long_name = long_name.strip() or None

        yf_sector = info.get("sector")
        if isinstance(yf_sector, str):
            yf_sector = yf_sector.strip() or None

        yf_industry = info.get("industry")
        if isinstance(yf_industry, str):
            yf_industry = yf_industry.strip() or None

        summary = info.get("longBusinessSummary")
        if isinstance(summary, str):
            summary = summary.strip() or None

        currency = info.get("currency")
        if isinstance(currency, str):
            currency = currency.strip().upper() or None
        else:
            currency = None

        last_dividend_date: Optional[str] = None
        try:
            divs = t.dividends
            if divs is not None and len(divs) > 0:
                last = divs.index.max()
                last_dividend_date = last.date().isoformat()
        except Exception:
            pass

        return YahooQuote(
            price=float(price),
            market_cap=mcap,
            ttm_yield_pct=ttm_yield_pct,
            beta=beta,
            long_name=long_name,
            yf_sector=yf_sector,
            yf_industry=yf_industry,
            long_business_summary=summary,
            currency=currency,
            last_dividend_date=last_dividend_date,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"yfinance: failed to fetch {symbol}: {exc}") from exc


import datetime

# Yields above this cap are discarded as bad data, or as
# distressed-payer signals that don't belong in a dividend simulator
# targeted at retail income investors. SGX REITs realistically max out
# around 10-12% even for the highest-yielders; anything above is
# almost always a small-cap with a depressed share price where the
# dividend is being priced in for a cut.
MAX_PLAUSIBLE_YIELD_PCT = 12.0


def _fy_based_yield_pct(
    t: yf.Ticker,
    price: float,
    *,
    today: Optional[datetime.date] = None,
) -> Optional[float]:
    """Headline yield = average of the last 3 completed calendar years'
    dividends ÷ current price.

    Why a 3-year average rather than TTM or partial-FY annualisation:
      - TTM yield over-weights special / one-off dividends (TCU's $0.09
        May 2026 special projected forward to ~20%).
      - High-payout small-caps whose price has declined (Aztech 76.9%
        payout ratio, stock down from S$1.28 IPO to S$0.945) display
        "yield" numbers that are mathematically real but unsustainable
        — the smoothing surfaces the trend, not the peak.
      - A multi-year average naturally signals dividend stability: a
        cut a few years ago drags the average down for a while.

    Eligibility rule (user-specified): the ticker must have paid at
    least one dividend in either the current calendar year or the
    immediately prior calendar year. Anything older is treated as a
    zombie payer and dropped (returns None).

    Falls back gracefully:
      - 3 completed years had payments  → average of all 3.
      - Fewer completed years have payments (newer listings) → average
        over only those years.
      - Zero completed years had payments but current FY has → use the
        current-FY partial as-is (brand-new IPO best-effort).
      - Nothing → return None, caller drops the ticker.

    A hard cap of MAX_PLAUSIBLE_YIELD_PCT discards bad-data outliers.
    """
    if price <= 0:
        return None
    today = today or datetime.date.today()
    cy_current = today.year
    cy_prior = cy_current - 1
    try:
        divs = t.dividends
        if divs is None or len(divs) == 0:
            return None
        years = divs.index.year
        cur_paid = float(divs[years == cy_current].sum())
        prior_paid = float(divs[years == cy_prior].sum())

        # Eligibility — must have paid this year or last.
        if cur_paid <= 0 and prior_paid <= 0:
            return None

        # Sum of dividends per completed year for the last 3 years.
        completed_totals: list[float] = []
        for offset in range(1, 4):
            cy = cy_current - offset
            total = float(divs[years == cy].sum())
            completed_totals.append(total)
        non_zero = [v for v in completed_totals if v > 0]

        if non_zero:
            avg_div = sum(non_zero) / len(non_zero)
        else:
            # Zero completed years had dividends but FY-current has → use
            # what they've paid so far as the best available estimate.
            avg_div = cur_paid

        # Three conservative floors that together prevent the average from
        # showing rosier numbers than what the company is actually paying
        # right now. We take the minimum of:
        #
        #   1. 3-year average (default)
        #   2. FY-1 total — catches 2024-style one-off specials where a
        #      single big year pulls the average up despite a return to
        #      normal payment levels (BEI/LHT Holdings: 2024 $0.18 surge,
        #      2023 + 2025 both $0.05).
        #   3. TTM total — catches gradual per-payment cuts where the
        #      calendar-year totals look stable but each individual
        #      payment is shrinking (HLS Helens: $0.028 → $0.020 → $0.019
        #      → $0.010 over four payments).
        #
        # The minimum is the most conservative defensible estimate for a
        # dividend simulator targeting realistic income projections.
        if prior_paid > 0 and prior_paid < avg_div:
            avg_div = prior_paid

        idx = divs.index
        today_ts = pd.Timestamp(today, tz="UTC")
        cutoff = today_ts - pd.DateOffset(years=1)
        ttm_total = float(divs[(idx >= cutoff) & (idx <= today_ts)].sum())
        if ttm_total > 0 and ttm_total < avg_div:
            avg_div = ttm_total

        pct = avg_div / price * 100
        return round(pct, 4) if 0 < pct <= MAX_PLAUSIBLE_YIELD_PCT else None
    except Exception:
        pass
    return None


def _resolve_yield(t: yf.Ticker, price: float, info: dict) -> Optional[float]:
    """Compute the FY-based yield. The info-dict yield fields are no longer
    consulted — they're the source of every C05-class bug we've fixed
    (90% for a stock that pays ~3%, 15% for a stock that hasn't paid in
    15 years). The dividend series is the authoritative record."""
    return _fy_based_yield_pct(t, price)
