"""Tests for sg_dividend_data.sources.yahoo — hermetic (no live network)."""
import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from sg_dividend_data.sources.yahoo import (
    MAX_PLAUSIBLE_YIELD_PCT,
    YahooQuote,
    _fy_based_yield_pct,
    fetch_quote,
)


def _make_fake_ticker(
    last_price=42.10,
    market_cap=1.5e11,
    trailing_yield=0.051,
    dividend_yield=None,
    beta=1.05,
    dividends=None,
    info_extra=None,
):
    fake = MagicMock()
    fake.fast_info.last_price = last_price
    fake.fast_info.__getitem__ = lambda self, key: {
        "marketCap": market_cap,
        "lastPrice": last_price,
    }.get(key)
    info = {
        "trailingAnnualDividendYield": trailing_yield,
        "dividendYield": dividend_yield,
        "beta": beta,
    }
    if info_extra:
        info.update(info_extra)
    fake.info = info
    fake.dividends = (
        pd.Series([], dtype=float) if dividends is None else dividends
    )
    return fake


def _div_series(*dated_amounts: tuple[str, float]) -> pd.Series:
    """Build a dividends Series from (iso-date, amount) pairs."""
    idx = pd.DatetimeIndex([pd.Timestamp(d, tz="UTC") for d, _ in dated_amounts])
    vals = [a for _, a in dated_amounts]
    return pd.Series(vals, index=idx, name="Dividends")


# ─── FY-based yield rule ──────────────────────────────────────────────────
def test_fy_yield_uses_current_year_when_paid_so_far():
    """Sum of CY-2026 dividends ÷ price when there's been a 2026 payment."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-04-15", 0.10),
        ("2025-10-15", 0.10),
        ("2026-04-15", 0.12),  # FY26 partial — only this should count
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=10.0, today=today)
    assert pct == pytest.approx(1.2, abs=0.01)


def test_fy_yield_falls_back_to_prior_year_when_no_current():
    """No FY26 dividends yet → use FY25 sum."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-04-15", 0.10),
        ("2025-10-15", 0.10),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=10.0, today=today)
    assert pct == pytest.approx(2.0, abs=0.01)


def test_fy_yield_returns_none_when_no_payments_in_either_fy():
    """AWK case: last paid 2011, no FY25 or FY26 divs → drop."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2011-08-23", 0.10),
    )
    today = datetime.date(2026, 5, 28)
    assert _fy_based_yield_pct(t, price=10.0, today=today) is None


def test_fy_yield_returns_none_when_no_history_at_all():
    t = MagicMock()
    t.dividends = pd.Series([], dtype=float)
    today = datetime.date(2026, 5, 28)
    assert _fy_based_yield_pct(t, price=10.0, today=today) is None


def test_fy_yield_caps_implausible_values():
    """A 25%+ yield is bad data — return None rather than ship it."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2026-01-15", 5.00),  # 50% on $10 — obvious special / data bug
    )
    today = datetime.date(2026, 5, 28)
    assert _fy_based_yield_pct(t, price=10.0, today=today) is None


def test_fy_yield_handles_zero_price():
    t = MagicMock()
    t.dividends = _div_series(("2026-04-15", 0.10))
    assert _fy_based_yield_pct(t, price=0.0) is None


def test_fy_yield_ignores_yahoo_info_dict():
    """Yahoo's info.dividendYield is bogus for C05-style cases — the new
    rule must NOT consult it at all. Even if Yahoo reports 90%, we compute
    from the series and only the series."""
    fake = _make_fake_ticker(
        last_price=0.55,
        trailing_yield=0.90,  # bogus 90%
        dividends=_div_series(("2026-04-15", 0.005)),  # ~0.9% actual
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("C05")
    assert q.ttm_yield_pct is not None
    # 0.005 / 0.55 ≈ 0.91%
    assert abs(q.ttm_yield_pct - 0.91) < 0.05


# ─── fetch_quote integration ──────────────────────────────────────────────
def test_fetch_quote_basic_shape():
    fake = _make_fake_ticker(
        last_price=42.10,
        market_cap=1.5e11,
        dividends=_div_series(
            ("2025-04-15", 1.0),
            ("2025-10-15", 1.0),
            ("2026-04-15", 1.0),  # only this counts for current FY
        ),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("D05")
    assert isinstance(q, YahooQuote)
    assert q.price == 42.10
    assert q.market_cap == 1.5e11
    assert q.ttm_yield_pct is not None
    # 1.0 / 42.10 ≈ 2.37%
    assert abs(q.ttm_yield_pct - 2.37) < 0.1


def test_fetch_quote_raises_on_zero_price():
    fake = _make_fake_ticker(last_price=0.0)
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        with pytest.raises(ValueError, match="no price"):
            fetch_quote("FAKE")


def test_fetch_quote_drops_zombie_via_yield_none():
    """A stock with last dividend in 2011 returns yield None — refresh
    then filters it via MIN_DIVIDEND_YIELD_PCT."""
    fake = _make_fake_ticker(
        last_price=1.0,
        dividends=_div_series(("2011-08-23", 0.10)),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("AWK")
    assert q.ttm_yield_pct is None


def test_max_plausible_yield_is_sensible():
    assert 10.0 <= MAX_PLAUSIBLE_YIELD_PCT <= 30.0
