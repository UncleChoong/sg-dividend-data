from unittest.mock import patch, MagicMock
from sg_dividend_data.refresh import build_snapshot
from sg_dividend_data.sources.yahoo import YahooQuote


def test_build_snapshot_assembles_fields(monkeypatch):
    yq = YahooQuote(price=42.0, market_cap=1e11, ttm_yield_pct=5.0, beta=1.0)
    monkeypatch.setattr("sg_dividend_data.refresh.fetch_quote", lambda t, session=None: yq)
    monkeypatch.setattr("sg_dividend_data.refresh.fetch_div_history",
                        lambda t, session=None: [1.9, 1.6, 1.4, 1.2, 1.2])
    monkeypatch.setattr("sg_dividend_data.refresh._compute_payout_ratio", lambda *a, **k: 0.5)
    monkeypatch.setattr("sg_dividend_data.refresh._compute_price_vol_90d", lambda *a, **k: 0.18)

    snap = build_snapshot("D05")
    assert snap.ticker == "D05"
    assert snap.sector == "Banks"
    assert snap.price == 42.0
    assert snap.ttm_yield_pct == 5.0
    assert snap.div_history_5y == [1.9, 1.6, 1.4, 1.2, 1.2]
