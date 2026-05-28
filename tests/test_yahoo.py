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


# ─── FY-based yield rule (annualised) ─────────────────────────────────────
def test_fy_yield_annualises_partial_via_prior_cadence():
    """Semi-annual payer: FY25 paid Apr+Oct ($0.10 each). FY26 has only
    paid Apr ($0.12) so far. FY25-by-May-28 = $0.10 (just Apr). FY25 total =
    $0.20. Scale = $0.20/$0.10 = 2.0. Annualised = $0.12 * 2 = $0.24.
    Yield = $0.24 / $10 = 2.4%."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-04-15", 0.10),
        ("2025-10-15", 0.10),
        ("2026-04-15", 0.12),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=10.0, today=today)
    assert pct == pytest.approx(2.4, abs=0.05)


def test_fy_yield_quarterly_payer_scales_4x():
    """Quarterly payer like DBS: FY25 paid 4 quarters of $0.50; FY26 has
    paid one Q1 of $0.55 so far. FY25-by-May = Q1 alone = $0.50. Scale =
    $2.00/$0.50 = 4.0. Annualised = $0.55 * 4 = $2.20. Yield = $2.20 / $60
    ≈ 3.67%."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-03-15", 0.50),
        ("2025-06-15", 0.50),
        ("2025-09-15", 0.50),
        ("2025-12-15", 0.50),
        ("2026-03-15", 0.55),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=60.0, today=today)
    assert pct == pytest.approx(3.67, abs=0.1)


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
        dividends=_div_series(
            ("2025-04-15", 0.005),
            ("2026-04-15", 0.005),
        ),
    )
    with patch("sg_dividend_data.sources.yahoo.yf.Ticker", return_value=fake):
        q = fetch_quote("C05")
    assert q.ttm_yield_pct is not None
    # FY25 had 1 payment of $0.005 by 2025-05-28 + 0 after = total $0.005.
    # Scale = 1.0. Annualised FY26 = $0.005. Yield = 0.005/0.55 = 0.91%.
    assert abs(q.ttm_yield_pct - 0.91) < 0.1


def test_fy_yield_caps_runaway_scale_factor():
    """A tiny interim followed by a big special should NOT extrapolate to
    20%+. Cap the scale factor at 5.0 and fall through to FY-1 total."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-04-15", 0.01),   # tiny interim
        ("2025-12-15", 0.49),   # huge special — FY25 total $0.50
        ("2026-04-15", 0.01),
    )
    today = datetime.date(2026, 5, 28)
    # Scale would be 0.50/0.01 = 50 -> capped, falls through to FY25 total $0.50.
    # Yield = $0.50/$10 = 5%.
    pct = _fy_based_yield_pct(t, price=10.0, today=today)
    assert pct == pytest.approx(5.0, abs=0.1)


def test_fy_yield_special_dividend_caught_by_growth_ceiling():
    """TCU-style: regular ~$0.02 dividends, then a $0.09 special in FY26.
    FY25 regular total = $0.08, paid evenly across the year. FY26 has paid
    $0.02 (regular) + $0.09 (special) by today = $0.11. Scale via cadence
    = ~2.0 (semi-annual). Naive annualised = $0.22, vs FY25 $0.08 = 2.75×.
    Growth ceiling (1.5×) clamps to FY25 $0.08. Yield = 0.08/1.14 ≈ 7%."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-05-15", 0.02),  # regular interim
        ("2025-08-15", 0.02),  # regular interim
        ("2025-12-15", 0.04),  # final
        ("2026-05-15", 0.02),  # regular interim
        ("2026-05-28", 0.09),  # special!
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=1.14, today=today)
    # Should be capped at FY25 total = $0.08 / 1.14 ≈ 7.0%
    assert pct == pytest.approx(7.0, abs=0.5)


def test_fy_yield_modest_growth_passes_through():
    """A company growing dividends 10% YoY (DBS-like) should pass through
    the growth ceiling. FY25 4×$0.50=$2.00. FY26 Q1=$0.55, scaled 4x =
    $2.20, which is 1.10× FY25 (under 1.5× cap). Annualised stays at $2.20."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-03-15", 0.50),
        ("2025-06-15", 0.50),
        ("2025-09-15", 0.50),
        ("2025-12-15", 0.50),
        ("2026-03-15", 0.55),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=60.0, today=today)
    # $2.20 / $60 = 3.67%
    assert pct == pytest.approx(3.67, abs=0.1)


def test_fy_yield_no_prior_by_today_falls_back_to_prior_total():
    """Company moved its payment from Sep (FY25) to Mar (FY26). FY26 paid =
    $0.30. FY25-by-May = 0 (payment was later). FY25 total = $0.30.
    Don't extrapolate from zero baseline; use FY25 total = $0.30."""
    t = MagicMock()
    t.dividends = _div_series(
        ("2025-09-15", 0.30),
        ("2026-03-15", 0.30),
    )
    today = datetime.date(2026, 5, 28)
    pct = _fy_based_yield_pct(t, price=10.0, today=today)
    assert pct == pytest.approx(3.0, abs=0.05)


# ─── fetch_quote integration ──────────────────────────────────────────────
def test_fetch_quote_basic_shape():
    """Semi-annual payer: FY25 Apr+Oct = $2.00 total, $1.00 paid by 2025-05-28.
    FY26 Apr = $1.00 paid. Scale = $2.00/$1.00 = 2.0. Annualised = $2.00.
    Yield = 2.00 / 42.10 ≈ 4.75%."""
    fake = _make_fake_ticker(
        last_price=42.10,
        market_cap=1.5e11,
        dividends=_div_series(
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
    assert q.ttm_yield_pct is not None
    assert abs(q.ttm_yield_pct - 4.75) < 0.15


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
