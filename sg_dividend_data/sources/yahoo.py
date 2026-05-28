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

# Yields above this cap are discarded as bad data — Singapore-listed
# stocks realistically top out around 12-15%, so anything beyond is
# either a broken yfinance feed or a one-off special dividend that will
# mislead simulation users.
MAX_PLAUSIBLE_YIELD_PCT = 20.0


def _fy_based_yield_pct(
    t: yf.Ticker,
    price: float,
    *,
    today: Optional[datetime.date] = None,
) -> Optional[float]:
    """Annualised current-FY yield with prior-year cadence scaling.

    Rule:
      A. If dividends paid in the current calendar year > 0:
         Scale that partial-year sum to a full-year estimate using FY-1's
         payment cadence:

             annualised = FY_current_paid * (FY_prior_full / FY_prior_paid_by_same_date)

         If FY-1 had a payment by the same calendar date this year does,
         the scale factor reflects the actual cadence (1.0 for full payers,
         4.0 for quarterly with one payment in, 2.0 for semi-annual, etc.).
         If FY-1 had no payment by the same date but had a full-year sum,
         we fall through to case B rather than try to extrapolate blindly.

      B. Else if FY-1 total > 0:
         annualised = FY_prior_total (last full year is the benchmark).

      C. Else return None — the caller drops the ticker.

    Any candidate exceeding MAX_PLAUSIBLE_YIELD_PCT is discarded.

    This eliminates two systemic problems:
      - TTM yield inflated by recent special dividends (e.g. TCU's
        partial-year special is no longer projected as a full-year rate).
      - Stocks like DBS appearing to have cut their yield in half just
        because we're mid-year and only one quarter has paid out.
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
        # yfinance's dividend index is tz-aware Timestamps; .year / .month / .day work.
        idx = divs.index
        years = idx.year
        cur_paid = float(divs[years == cy_current].sum())
        prior_total = float(divs[years == cy_prior].sum())

        if cur_paid > 0:
            # FY-1 dividends paid by the same month/day as today, last year.
            prior_by_today = float(divs[
                (years == cy_prior)
                & (
                    (idx.month < today.month)
                    | ((idx.month == today.month) & (idx.day <= today.day))
                )
            ].sum())
            if prior_by_today > 0 and prior_total > 0:
                # Run-rate scale: how much MORE did FY-1 pay after this date?
                scale = prior_total / prior_by_today
                # Sanity-cap the multiplier. A scale > 5 would imply the
                # current FY's only payment is a tiny interim and the bulk
                # comes much later — better to fall through to FY-1 total
                # than over-project.
                if scale > 5.0:
                    annualised = prior_total
                else:
                    annualised = cur_paid * scale
            else:
                # No FY-1 payment by the same date → don't extrapolate from a
                # zero baseline. Use FY-1 total if available, else FY-current paid as-is.
                annualised = prior_total if prior_total > 0 else cur_paid

            # Growth-rate ceiling: dividends rarely grow >50% YoY. If our
            # extrapolation implies that, the FY-current "paid so far" almost
            # certainly contains a one-off / special dividend (TCU's $0.09
            # extraordinary payout in May 2026 is the canonical case) and
            # annualising it would mislead simulation users. Fall back to
            # FY-1 total as a more sustainable estimate.
            if prior_total > 0 and annualised > 1.5 * prior_total:
                annualised = prior_total

            pct = annualised / price * 100
            return round(pct, 4) if 0 < pct <= MAX_PLAUSIBLE_YIELD_PCT else None

        if prior_total > 0:
            pct = prior_total / price * 100
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
