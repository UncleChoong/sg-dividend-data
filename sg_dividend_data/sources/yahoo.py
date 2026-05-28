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

        return YahooQuote(
            price=float(price),
            market_cap=mcap,
            ttm_yield_pct=ttm_yield_pct,
            beta=beta,
            long_name=long_name,
            yf_sector=yf_sector,
            yf_industry=yf_industry,
            long_business_summary=summary,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"yfinance: failed to fetch {symbol}: {exc}") from exc


# Anything above this is almost certainly bad data — Yahoo's
# trailingAnnualDividendYield / dividendYield fields occasionally return
# values inflated by special / liquidation dividends, broken split
# adjustments, or stale numerator-over-fresh-denominator bugs. SGX dividend
# yields realistically top out around 12-15% even for the highest-yielders.
MAX_PLAUSIBLE_YIELD_PCT = 20.0


def _resolve_yield(t: yf.Ticker, price: float, info: dict) -> Optional[float]:
    """Return TTM yield as a percentage (e.g. 5.0 for 5%), or None.

    Order of preference, from most-reliable to least:
      1. Sum of the last 12 months of dividends from `t.dividends` ÷ price.
      2. trailingAnnualDividendYield from the info dict.
      3. dividendYield from the info dict.

    Any candidate exceeding MAX_PLAUSIBLE_YIELD_PCT is discarded as bad
    data — for example, C05 Chemical Industries shows 90% from Yahoo's
    info dict despite the actual dividend history giving ~3%.
    """
    # 1. Compute TTM yield from the actual dividend series — authoritative.
    try:
        divs = t.dividends
        if divs is not None and len(divs) > 0 and price > 0:
            cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=1)
            ttm_total = float(divs[divs.index >= cutoff].sum())
            if ttm_total > 0:
                pct = ttm_total / price * 100
                if 0 < pct <= MAX_PLAUSIBLE_YIELD_PCT:
                    return round(pct, 4)
    except Exception:
        pass

    # 2. trailingAnnualDividendYield — Yahoo stores this as a fraction (0.05 = 5%),
    #    but occasionally as a raw percent. Treat anything > 1 as already-percent.
    try:
        tay = info.get("trailingAnnualDividendYield")
        if tay and float(tay) > 0:
            tay_f = float(tay)
            pct = tay_f if tay_f > 1 else tay_f * 100
            if 0 < pct <= MAX_PLAUSIBLE_YIELD_PCT:
                return round(pct, 4)
    except Exception:
        pass

    # 3. dividendYield — same fraction-vs-percent ambiguity as above.
    try:
        dy = info.get("dividendYield")
        if dy and float(dy) > 0:
            dy_f = float(dy)
            pct = dy_f if dy_f > 1 else dy_f * 100
            if 0 < pct <= MAX_PLAUSIBLE_YIELD_PCT:
                return round(pct, 4)
    except Exception:
        pass

    return None
