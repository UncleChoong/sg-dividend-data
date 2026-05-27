from sg_dividend_data.models import TickerSnapshot, ScoreBreakdown, UniverseEntry

def test_ticker_snapshot_roundtrip():
    snap = TickerSnapshot(
        ticker="D05",
        name="DBS Group",
        sector="Banks",
        price=42.10,
        market_cap=1.2e11,
        ttm_yield_pct=5.1,
        lot_size=100,
        div_history_5y=[1.92, 1.62, 1.44, 1.20, 1.20],
        payout_ratio=0.55,
        price_vol_90d=0.18,
    )
    d = snap.model_dump()
    assert d["ticker"] == "D05"
    assert TickerSnapshot.model_validate(d) == snap

def test_score_breakdown_total():
    sb = ScoreBreakdown(sector=10, mcap=0, div_vol=0, payout=5, price_vol=3)
    assert sb.total() == 18

def test_universe_entry_serializes_to_spec_shape():
    snap = TickerSnapshot(
        ticker="D05", name="DBS Group", sector="Banks",
        price=42.10, market_cap=1.2e11, ttm_yield_pct=5.1,
        lot_size=100, div_history_5y=[1.92, 1.62, 1.44, 1.20, 1.20],
        payout_ratio=0.55, price_vol_90d=0.18,
    )
    sb = ScoreBreakdown(sector=10, mcap=0, div_vol=0, payout=5, price_vol=3)
    entry = UniverseEntry.from_snapshot(snap, sb)
    out = entry.model_dump()
    assert out["ticker"] == "D05"
    assert out["score"] == 18
    assert out["score_breakdown"]["sector"] == 10
    assert out["div_history_5y"] == [1.92, 1.62, 1.44, 1.20, 1.20]
