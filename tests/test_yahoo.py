"""Tests for sg_dividend_data.sources.yahoo — hermetic (no live network)."""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from sg_dividend_data.sources.yahoo import (
    MAX_PLAUSIBLE_YIELD_PCT,
    YahooQuote,
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
    """Build a MagicMock that mimics a yfinance.Ticker for unit tests."""
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

    if dividends is None:
        fake.dividends = pd.Series([], dtype=float)
    else:
        fake.dividends = dividends

    return fake


def _dividends_for_ttm(annual_total: float) -> pd.Series:
    """Return a 4-quarter dividend series summing to `annual_total`, all
    within the trailing 12 months."""
    now = pd.Timestamp.now(tz="UTC")
    dates = pd.date_range(
        end=now - pd.Timedelta(days=10), periods=4, freq="QE", tz="UTC"
    )
    per_q = annual_total / 4
    return pd.Series([per_q] * 4, index=dates, name="Dividends")


def test_fetch_quote_prefers_dividend_history_over_info_dict():
    """The dividend series is authoritative — Yahoo's info-dict yield is a
    fallback only. Even when both are present, history wins."""
    # info says 90% (bogus), but dividend history says 5% — history must win.
    fake = _make_fake_ticker(
        last_price=10.0,
        market_cap=1e9,
        trailing_yield=0.90,  # bogus 90%
        dividends=_dividends_for_ttm(annual_total=0.50),  # 5% on $10
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("C05")
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 5.0) < 0.5


def test_fetch_quote_rejects_implausible_yields():
    """Yields above the cap are discarded as bad data, returning None."""
    # No dividend history; info dict says 80% (over cap).
    fake = _make_fake_ticker(
        last_price=1.0,
        market_cap=1e8,
        trailing_yield=0.80,   # 80%, above cap
        dividend_yield=None,
        dividends=pd.Series([], dtype=float),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("BAD")
    assert q.ttm_yield_pct is None


def test_fetch_quote_falls_back_to_info_yield_when_no_history():
    """With no dividend history, the info dict's trailing yield is used."""
    fake = _make_fake_ticker(
        last_price=20.0,
        market_cap=5e9,
        trailing_yield=0.045,  # 4.5%
        dividends=pd.Series([], dtype=float),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("D05")
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 4.5) < 0.01


def test_fetch_quote_falls_back_to_dividend_yield_field():
    """dividendYield as a raw percent (>1) is interpreted correctly."""
    fake = _make_fake_ticker(
        last_price=10.0,
        market_cap=5e9,
        trailing_yield=None,
        dividend_yield=6.5,
        dividends=pd.Series([], dtype=float),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("G3B")
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 6.5) < 0.01


def test_fetch_quote_returns_none_when_no_yield_data():
    fake = _make_fake_ticker(
        last_price=10.0,
        market_cap=5e9,
        trailing_yield=None,
        dividend_yield=None,
        dividends=pd.Series([], dtype=float),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("NODIV")
    assert q.ttm_yield_pct is None


def test_fetch_quote_raises_on_zero_price():
    fake = _make_fake_ticker(last_price=0.0)
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        with pytest.raises(ValueError, match="no price"):
            fetch_quote("FAKE")


def test_fetch_quote_missing_beta_returns_none():
    fake = _make_fake_ticker(beta=None)
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("D05")
    assert q.beta is None


def test_fetch_quote_basic_d05_shape():
    """Smoke test that the populated YahooQuote shape is correct."""
    fake = _make_fake_ticker(
        last_price=42.10,
        market_cap=1.5e11,
        trailing_yield=0.051,
        dividends=_dividends_for_ttm(annual_total=2.0),  # 4.75% history → wins
        beta=1.05,
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("D05")
    assert isinstance(q, YahooQuote)
    assert q.price == 42.10
    assert q.market_cap == 1.5e11
    assert q.beta == 1.05
    # 2.0 / 42.10 ≈ 4.75%
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 4.75) < 0.2


def test_max_plausible_yield_is_sensible():
    """Document the cap so a future change requires updating the test too."""
    assert 10.0 <= MAX_PLAUSIBLE_YIELD_PCT <= 30.0
