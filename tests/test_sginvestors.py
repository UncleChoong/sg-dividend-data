"""Tests for sg_dividend_data.sources.dividend_history — hermetic (no live network).

Note: the old sginvestors.py HTML scraper has been replaced by dividend_history.py
which uses yfinance.  These tests remain in test_sginvestors.py so git history stays
linked; the import points to the new module.
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from sg_dividend_data.sources.dividend_history import fetch_div_history


def _make_fake_ticker_with_dividends(annual_amounts: dict) -> MagicMock:
    """Build a MagicMock Ticker whose .dividends returns a synthetic series.

    annual_amounts: {year: total_annual_dividend}, e.g. {2021: 1.2, 2022: 1.4, ...}
    """
    fake = MagicMock()
    if not annual_amounts:
        fake.dividends = pd.Series([], dtype=float)
        return fake

    records = []
    for year, total in annual_amounts.items():
        # Represent each year as a single annual payment on June 1
        ts = pd.Timestamp(year=year, month=6, day=1, tz="UTC")
        records.append((ts, total))

    idx, vals = zip(*records)
    fake.dividends = pd.Series(list(vals), index=list(idx), name="Dividends")
    return fake


def test_fetch_div_history_d05_returns_5y_most_recent_first():
    annual = {2020: 0.87, 2021: 0.93, 2022: 1.31, 2023: 2.09, 2024: 2.11}
    fake = _make_fake_ticker_with_dividends(annual)
    with patch("sg_dividend_data.sources.dividend_history.yf.Ticker", return_value=fake):
        hist = fetch_div_history("D05")

    assert len(hist) == 5
    # Most-recent full year = 2024 (current year 2026, so 2025 is excluded as partial)
    # Actually 2025 would be excluded if test runs in 2026; our mock only has up to 2024
    assert hist[0] == pytest.approx(2.11, rel=1e-3)  # 2024
    assert hist[1] == pytest.approx(2.09, rel=1e-3)  # 2023
    assert hist[4] == pytest.approx(0.87, rel=1e-3)  # 2020


def test_fetch_div_history_returns_none_for_missing_years():
    # Only 3 years of data — older years should be None
    annual = {2022: 1.0, 2023: 1.1, 2024: 1.2}
    fake = _make_fake_ticker_with_dividends(annual)
    with patch("sg_dividend_data.sources.dividend_history.yf.Ticker", return_value=fake):
        hist = fetch_div_history("X99")

    assert len(hist) == 5
    # 2024, 2023, 2022 have data; 2021, 2020 should be None
    assert hist[0] == pytest.approx(1.2, rel=1e-3)
    assert hist[1] == pytest.approx(1.1, rel=1e-3)
    assert hist[2] == pytest.approx(1.0, rel=1e-3)
    assert hist[3] is None
    assert hist[4] is None


def test_fetch_div_history_empty_series_returns_all_none():
    fake = _make_fake_ticker_with_dividends({})
    with patch("sg_dividend_data.sources.dividend_history.yf.Ticker", return_value=fake):
        hist = fetch_div_history("NODIV")

    assert hist == [None, None, None, None, None]


def test_fetch_div_history_exception_returns_all_none():
    fake = MagicMock()
    fake.dividends = MagicMock(side_effect=RuntimeError("network error"))
    with patch("sg_dividend_data.sources.dividend_history.yf.Ticker", return_value=fake):
        hist = fetch_div_history("ERR")

    assert hist == [None, None, None, None, None]


def test_fetch_div_history_elements_are_floats_or_none():
    annual = {2021: 0.5, 2022: 0.6, 2023: 0.7, 2024: 0.8}
    fake = _make_fake_ticker_with_dividends(annual)
    with patch("sg_dividend_data.sources.dividend_history.yf.Ticker", return_value=fake):
        hist = fetch_div_history("A17U")

    for entry in hist:
        assert entry is None or isinstance(entry, float)
    non_null = [e for e in hist if e is not None]
    assert non_null, "expected at least one non-null dividend"
    assert max(non_null) > 0.3
