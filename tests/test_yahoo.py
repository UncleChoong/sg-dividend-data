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
    3-yr avg = $0.085, FY-1 = $0.11, TTM = $0.12 — min is the avg.
    On $0.945 → 9.0%."""
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
    # min(3-yr avg=0.085, FY-1=0.11, TTM=0.12) = 0.085 → 9.0%.
    assert pct == pytest.approx(9.0, abs=0.1)


def test_fy_prior_floor_catches_one_off_specials():
    """BEI/LHT Holdings: 2024 had a one-off $0.18 special, 2023 + 2025
    both back to $0.05 normal. 3-yr avg = $0.093 (skewed by special) but
    FY-1 ($0.05) is the actual current rate. Floor brings us down to FY-1."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2023-04-15", 0.05),
        ("2024-04-15", 0.18),  # one-off
        ("2025-04-15", 0.05),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=0.815, today=today)
    # 3-yr avg = (0.05 + 0.18 + 0.05)/3 = $0.093
    # FY-1 = $0.05; FY-1 floor applies → avg_div = $0.05
    # TTM (last 365d from 2026-05-28): includes 2025-04-15 ($0.05) → $0.05
    # min = $0.05 → 0.05/0.815 ≈ 6.13%.
    assert pct == pytest.approx(6.13, abs=0.2)


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
    """Anything above 12% — distressed-payer territory — is excluded."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2023-04-15", 5.00),
        ("2024-04-15", 5.00),
        ("2025-04-15", 5.00),
        ("2026-04-15", 5.00),
    )
    today = datetime.date(2026, 5, 28)
    # 5.0 average on $10 → 50%, well above 12% cap.
    assert _fy_based_yield_pct(t, price=10.0, today=today) is None


def test_caps_excludes_distressed_small_caps():
    """HLS-style distressed payer: depressed price + recent cuts → 19%+
    historical-average yield. Above the 12% cap → dropped."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2024-09-11", 0.028),
        ("2025-05-16", 0.020),
        ("2025-09-16", 0.019),
        ("2026-05-18", 0.010),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=0.17, today=today)
    # Without the cap: 3-yr avg = (0.028 + 0.039) / 2 = $0.0335 → 19.7%.
    # With TTM floor: TTM = $0.0291 → 17.1%. Still > 12% cap → None.
    assert pct is None


def test_ttm_floor_catches_recent_cuts_below_cap():
    """A dividend-cutter whose TTM is below the 3-year average but still
    under the cap should display the TTM-based number, not the average."""
    t = MagicMock()
    t.dividends = _div_series(
        # 2023: $0.50 paid, $0.50 yield on $100 = nope, on $10:
        ("2023-06-15", 0.50),
        ("2024-06-15", 0.40),  # 20% cut
        ("2025-06-15", 0.30),  # another 25% cut
        ("2026-06-15", 0.10),  # major cut — but in this test the date
                               # is past today so won't count for TTM
    )
    today = datetime.date(2026, 7, 1)  # after the 2026 payment
    pct = _fy_based_yield_pct(t, price=10.0, today=today)
    # 3-year avg (CY23+24+25): (0.50 + 0.40 + 0.30) / 3 = $0.40 → 4.0%
    # TTM (last 12 months from 2026-07-01): only the 2026-06-15 $0.10 → 1.0%
    # TTM is lower → display TTM. Yield = 1.0%.
    assert pct == pytest.approx(1.0, abs=0.05)


def test_handles_zero_price():
    t = MagicMock()
    t.dividends = _div_series(("2026-04-15", 0.10))
    assert _fy_based_yield_pct(t, price=0.0) is None


def test_ignores_yahoo_info_dict():
    """Yahoo's info.dividendYield is bogus for C05-style cases — the new
    rule must NOT consult it at all. The TTM floor also kicks in here
    because 2025's $0.005 was paid before the TTM window, leaving only
    the 2026-04-15 $0.005 in TTM → that's the lower-of-two and wins."""
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
    # 3-yr avg of non-zero = (0.015 + 0.005)/2 = 0.01.
    # TTM (from 2025-05-28 cutoff) = just 2026-04-15 $0.005.
    # min = 0.005 → 0.005/0.55 ≈ 0.91%.
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 0.91) < 0.1


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
