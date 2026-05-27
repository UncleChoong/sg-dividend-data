from unittest.mock import patch, MagicMock
from sg_dividend_data.refresh import build_snapshot
from sg_dividend_data.sources.yahoo import YahooQuote
from pathlib import Path


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


def test_refresh_skips_upload_when_no_snapshots(monkeypatch, tmp_path):
    from sg_dividend_data import refresh as r

    # Force every ticker fetch to fail.
    monkeypatch.setattr(r, "build_snapshot",
        lambda t, session=None: (_ for _ in ()).throw(RuntimeError("boom")))

    # Spy on uploader — it must NOT be called.
    called = {"n": 0}
    monkeypatch.setattr(r, "upload_to_r2",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    monkeypatch.setattr(r, "telegram_alert", lambda *a, **k: True)

    output = tmp_path / "x.json"
    snaps = r.refresh_all(dry_run=False, output=output)

    assert snaps == []
    assert called["n"] == 0, "should NOT have uploaded an empty universe"
