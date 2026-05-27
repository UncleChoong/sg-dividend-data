"""Tests for sg_dividend_data.sources.yahoo — hermetic (no live network)."""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from sg_dividend_data.sources.yahoo import YahooQuote, fetch_quote


def _make_fake_ticker(
    last_price=42.10,
    market_cap=1.5e11,
    trailing_yield=0.051,
    dividend_yield=None,
    beta=1.05,
    dividends=None,
):
    """Build a MagicMock that mimics a yfinance.Ticker for unit tests."""
    fake = MagicMock()

    # fast_info — subscript and attribute access both work on MagicMock,
    # but we need specific values for last_price and marketCap.
    fake.fast_info.last_price = last_price
    fake.fast_info.__getitem__ = lambda self, key: {
        "marketCap": market_cap,
        "lastPrice": last_price,
    }.get(key)

    fake.info = {
        "trailingAnnualDividendYield": trailing_yield,
        "dividendYield": dividend_yield,
        "beta": beta,
    }

    if dividends is None:
        # Empty dividend series by default
        fake.dividends = pd.Series([], dtype=float)
    else:
        fake.dividends = dividends

    return fake


def test_fetch_quote_d05():
    fake = _make_fake_ticker(last_price=42.10, market_cap=1.5e11, trailing_yield=0.051, beta=1.05)
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("D05")
    assert isinstance(q, YahooQuote)
    assert q.price == 42.10
    assert q.market_cap == 1.5e11
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 5.1) < 0.01
    assert q.beta == 1.05


def test_fetch_quote_no_trailing_yield_falls_back_to_dividend_yield():
    """When trailingAnnualDividendYield is absent, dividendYield (percent) is used."""
    fake = _make_fake_ticker(
        last_price=10.0,
        market_cap=5e9,
        trailing_yield=None,
        dividend_yield=6.5,   # already a percent
        beta=None,
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("G3B")
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 6.5) < 0.01


def test_fetch_quote_yield_falls_back_to_dividends_series():
    """When both info yield fields are None, TTM yield is computed from dividends."""
    import datetime
    now = pd.Timestamp.now(tz="UTC")
    dates = pd.date_range(end=now - pd.Timedelta(days=10), periods=4, freq="QE", tz="UTC")
    divs = pd.Series([0.20, 0.20, 0.20, 0.20], index=dates, name="Dividends")

    fake = _make_fake_ticker(
        last_price=20.0,
        market_cap=None,
        trailing_yield=None,
        dividend_yield=None,
        beta=None,
        dividends=divs,
    )
    fake.info = {"trailingAnnualDividendYield": None, "dividendYield": None, "beta": None}
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("QL3")
    # 4 × 0.20 = 0.80 annual div on price 20.0 → yield = 4.0%
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 4.0) < 0.5


def test_fetch_quote_raises_on_zero_price():
    """A ticker that returns price=0 (or None) must raise ValueError."""
    fake = _make_fake_ticker(last_price=0.0)
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        with pytest.raises(ValueError, match="no price"):
            fetch_quote("FAKE")


def test_fetch_quote_missing_beta_returns_none():
    fake = _make_fake_ticker(beta=None)
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("D05")
    assert q.beta is None
