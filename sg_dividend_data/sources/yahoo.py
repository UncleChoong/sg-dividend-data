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


def fetch_quote(ticker: str) -> YahooQuote:
    """Fetch price, market-cap, TTM yield and beta for an SGX ticker.

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

        # TTM yield — try trailingAnnualDividendYield (fraction) then dividendYield (may be %)
        # then fall back to computing from dividends series / price.
        ttm_yield_pct: Optional[float] = _resolve_yield(t, price)

        # beta — optional
        beta: Optional[float] = None
        try:
            raw_beta = t.info.get("beta")
            if raw_beta is not None:
                beta = float(raw_beta)
        except Exception:
            pass

        return YahooQuote(
            price=float(price),
            market_cap=mcap,
            ttm_yield_pct=ttm_yield_pct,
            beta=beta,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"yfinance: failed to fetch {symbol}: {exc}") from exc


def _resolve_yield(t: yf.Ticker, price: float) -> Optional[float]:
    """Return TTM yield as a percentage (e.g. 5.0 for 5%), or None."""
    # 1. trailingAnnualDividendYield — Yahoo stores this as a fraction (0.05 = 5%)
    try:
        info = t.info
        tay = info.get("trailingAnnualDividendYield")
        if tay and float(tay) > 0:
            pct = float(tay) * 100
            # Sanity check: yfinance occasionally stores it already as a percent
            if pct > 50:
                pct = float(tay)  # it was already a percent
            return round(pct, 4)
    except Exception:
        pass

    # 2. dividendYield — Yahoo sometimes stores this already as a percent (e.g. 3.6 means 3.6%)
    try:
        dy = info.get("dividendYield")
        if dy and float(dy) > 0:
            # If value > 1 it's already a percent; if <= 1 it's a fraction
            dy_f = float(dy)
            return round(dy_f if dy_f > 1 else dy_f * 100, 4)
    except Exception:
        pass

    # 3. Compute TTM yield from dividend history
    try:
        divs = t.dividends
        if divs is not None and len(divs) > 0:
            cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=1)
            ttm_total = divs[divs.index >= cutoff].sum()
            if ttm_total > 0 and price > 0:
                return round(ttm_total / price * 100, 4)
    except Exception:
        pass

    return None
