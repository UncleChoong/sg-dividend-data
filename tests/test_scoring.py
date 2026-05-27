from sg_dividend_data.scoring import score, sector_points, mcap_points, div_vol_points, payout_points, price_vol_points
from sg_dividend_data.models import TickerSnapshot, ScoreBreakdown


def make_snap(**overrides):
    base = dict(
        ticker="X", name="X", sector="Banks", price=10.0, market_cap=5e9,
        ttm_yield_pct=4.0, lot_size=100, div_history_5y=[0.5]*5,
        payout_ratio=0.6, price_vol_90d=0.15,
    )
    base.update(overrides)
    return TickerSnapshot(**base)

def test_sector_points_banks_low():
    assert sector_points("Banks") <= 5

def test_sector_points_business_trusts_high():
    assert sector_points("Business Trusts") >= 30

def test_mcap_small_cap_penalty():
    assert mcap_points(2e8) == 20
    assert mcap_points(1e10) == 0
    assert 0 < mcap_points(1e9) < 20

def test_div_vol_no_cuts():
    assert div_vol_points([1.0, 1.0, 1.0, 1.0, 1.0]) == 0

def test_div_vol_rising_no_cut():
    # Most-recent-first: [1.4, 1.3, 1.2, 1.1, 1.0] means dividends rose every year — 0 cuts.
    assert div_vol_points([1.4, 1.3, 1.2, 1.1, 1.0]) == 0

def test_div_vol_four_cuts():
    # Most-recent-first: [1.0, 1.1, 1.2, 1.3, 1.4] — dividends fell every year, 4 cuts → 40pts capped at 25.
    assert div_vol_points([1.0, 1.1, 1.2, 1.3, 1.4]) == 25

def test_div_vol_one_cut():
    assert div_vol_points([0.5, 1.0, 1.0, 1.0, 1.0]) == 10  # most-recent < next-most-recent: 1 cut

def test_div_vol_missing_history():
    assert div_vol_points([None, None, None, None, None]) == 10

def test_payout_band():
    assert payout_points(0.5) == 0
    assert 0 < payout_points(0.8) < 15
    assert payout_points(1.1) == 25

def test_price_vol_scaling():
    assert price_vol_points(0.10) == 0
    assert price_vol_points(0.50) == 15
    assert 0 < price_vol_points(0.30) < 15

def test_dbs_like_low_score():
    snap = make_snap(sector="Banks", market_cap=1e11, div_history_5y=[1.92,1.62,1.44,1.20,1.20],
                     payout_ratio=0.55, price_vol_90d=0.18)
    sb = score(snap)
    assert sb.total() < 25

def test_distressed_high_yield_high_score():
    snap = make_snap(sector="Business Trusts", market_cap=3e8,
                     div_history_5y=[0.05, 0.02, 0.01, None, None],
                     payout_ratio=1.2, price_vol_90d=0.55)
    sb = score(snap)
    assert sb.total() >= 70
