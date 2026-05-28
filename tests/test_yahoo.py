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


# ─── 3-year average yield rule ────────────────────────────────────────────
def test_three_year_average_basic():
    """Aztech-style: 3 completed years with growing dividends.
    Avg of $0.045 + $0.10 + $0.11 = $0.085, on $0.945 → 9.0%.

    This is the canonical user-driven case: a high-payout-ratio stock
    whose TTM yield (12.8%) overstates the run rate. The smoothed average
    shows the trend without the peak."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2023-05-05", 0.015),
        ("2023-07-31", 0.030),
        ("2024-04-22", 0.050),
        ("2024-08-06", 0.050),
        ("2025-04-17", 0.100),
        ("2025-07-28", 0.010),
        ("2026-04-22", 0.110),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=0.945, today=today)
    # (0.045 + 0.10 + 0.11) / 3 = 0.085; 0.085 / 0.945 ≈ 9.0%
    assert pct == pytest.approx(9.0, abs=0.1)


def test_three_year_average_smooths_special_dividends():
    """TCU-style: a recent year's special dividend gets smoothed out.
    Per-year totals: 2023 $0.034, 2024 $0.04, 2025 $0.04. Avg ~$0.038."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2023-05-04", 0.017),
        ("2023-08-17", 0.017),
        ("2024-05-02", 0.020),
        ("2024-08-15", 0.020),
        ("2025-05-08", 0.020),
        ("2025-08-14", 0.020),
        ("2026-05-05", 0.022),
        ("2026-05-28", 0.090),  # special — would NOT inflate average
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=1.14, today=today)
    # (0.034 + 0.04 + 0.04) / 3 = 0.038; 0.038 / 1.14 ≈ 3.3%
    assert pct == pytest.approx(3.3, abs=0.2)


def test_three_year_average_handles_dbs_growth():
    """DBS-style: steadily growing dividends. Average reflects the trend,
    slightly lower than the most recent year."""
    t = MagicMock()
    t.dividends = _div_series(
        # 2023: 4 x ~$0.52 = $2.09 total
        ("2023-04-15", 0.52),
        ("2023-07-15", 0.52),
        ("2023-10-15", 0.52),
        ("2024-01-15", 0.53),
        # 2024: 4 x ~$0.53
        ("2024-04-15", 0.53),
        ("2024-07-15", 0.53),
        ("2024-10-15", 0.53),
        ("2025-01-15", 0.52),
        # 2025: 4 x with bumps
        ("2025-04-15", 0.75),
        ("2025-07-15", 0.75),
        ("2025-10-15", 0.75),
        ("2026-01-15", 0.60),
        # 2026 so far: Q1
        ("2026-04-15", 0.60),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=62.0, today=today)
    # Calendar-year totals (per the dates above):
    #   2023: 0.52 + 0.52 + 0.52 = 1.56
    #   2024: 0.53 + 0.53 + 0.53 + 0.53 = 2.12
    #   2025: 0.52 + 0.75 + 0.75 + 0.75 = 2.77
    # 3-yr avg = (1.56 + 2.12 + 2.77) / 3 ≈ 2.15. Yield = 2.15 / 62 ≈ 3.47%.
    assert pct == pytest.approx(3.47, abs=0.15)


def test_eligibility_drops_zombies():
    """AWK case: last paid 2011. No FY25 OR FY26 payment → dropped."""
    t = MagicMock()
    t.dividends = _div_series(("2011-08-23", 0.10))
    today = datetime.date(2026, 5, 28)
    assert _fy_based_yield_pct(t, price=10.0, today=today) is None


def test_eligibility_keeps_fy25_only():
    """Annual payer that paid only in 2025, not yet in 2026 → kept."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2023-09-15", 0.30),
        ("2024-09-15", 0.30),
        ("2025-09-15", 0.30),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=10.0, today=today)
    # 3-year avg = 0.30; yield = 3.0%
    assert pct == pytest.approx(3.0, abs=0.01)


def test_new_listing_uses_available_years():
    """Brand-new payer: only 1 completed year has dividends. Average uses
    just that year rather than dividing by 3."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-05-15", 0.05),  # only completed-year payment
        ("2026-05-15", 0.05),  # current FY (irrelevant — drives eligibility)
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=1.00, today=today)
    # 1-year avg = 0.05; yield = 5.0%
    assert pct == pytest.approx(5.0, abs=0.01)


def test_new_ipo_only_paid_in_current_fy():
    """IPO during the current calendar year, no completed-year payments
    yet. Falls back to FY-current paid-so-far as a best-effort estimate."""
    t = MagicMock()
    t.dividends = _div_series(("2026-04-15", 0.03))
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=1.00, today=today)
    # $0.03 / $1 = 3%
    assert pct == pytest.approx(3.0, abs=0.01)


def test_caps_implausible_yields():
    """A 25%+ averaged yield is bad data → return None."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2023-04-15", 5.00),
        ("2024-04-15", 5.00),
        ("2025-04-15", 5.00),
        ("2026-04-15", 5.00),
    )
    today = datetime.date(2026, 5, 28)
    # 5.0 average on $10 → 50%, well above 20% cap.
    assert _fy_based_yield_pct(t, price=10.0, today=today) is None


def test_handles_zero_price():
    t = MagicMock()
    t.dividends = _div_series(("2026-04-15", 0.10))
    assert _fy_based_yield_pct(t, price=0.0) is None


def test_ignores_yahoo_info_dict():
    """Yahoo's info.dividendYield is bogus for C05-style cases — the new
    rule must NOT consult it at all."""
    fake = _make_fake_ticker(
        last_price=0.55,
        trailing_yield=0.90,  # bogus 90%
        dividends=_div_series(
            ("2024-04-15", 0.015),
            ("2025-04-15", 0.005),
            ("2026-04-15", 0.005),
        ),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("C05")
    # 3-year avg: only 2024 ($0.015) and 2025 ($0.005) have non-zero in
    # completed years (2023 = 0). Avg of non-zero years = (0.015 + 0.005)/2 = 0.01.
    # 0.01 / 0.55 ≈ 1.8%
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 1.8) < 0.5


# ─── fetch_quote integration ──────────────────────────────────────────────
def test_fetch_quote_shape():
    fake = _make_fake_ticker(
        last_price=42.10,
        market_cap=1.5e11,
        dividends=_div_series(
            ("2023-04-15", 1.0),
            ("2023-10-15", 1.0),
            ("2024-04-15", 1.0),
            ("2024-10-15", 1.0),
            ("2025-04-15", 1.0),
            ("2025-10-15", 1.0),
            ("2026-04-15", 1.0),
        ),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("D05")
    assert isinstance(q, YahooQuote)
    assert q.price == 42.10
    assert q.market_cap == 1.5e11
    # 3-year avg = (2.0 + 2.0 + 2.0) / 3 = 2.0 ; yield = 4.75%
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 4.75) < 0.1


def test_fetch_quote_raises_on_zero_price():
    fake = _make_fake_ticker(last_price=0.0)
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        with pytest.raises(ValueError, match="no price"):
            fetch_quote("FAKE")


def test_max_plausible_yield_is_sensible():
    assert 10.0 <= MAX_PLAUSIBLE_YIELD_PCT <= 30.0
