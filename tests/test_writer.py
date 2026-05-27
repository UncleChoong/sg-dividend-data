import json
from pathlib import Path
from sg_dividend_data.writer import assemble, write_universe
from sg_dividend_data.models import TickerSnapshot

def make_snap(ticker="D05", sector="Banks", **kw):
    base = dict(ticker=ticker, name=f"{ticker} Inc", sector=sector,
                price=10.0, market_cap=5e9, ttm_yield_pct=4.0, lot_size=100,
                div_history_5y=[0.4]*5, payout_ratio=0.5, price_vol_90d=0.15)
    base.update(kw)
    return TickerSnapshot(**base)


def test_assemble_produces_universe():
    snaps = [make_snap("D05"), make_snap("A17U", sector="REITs")]
    out = assemble(snaps)
    assert "generated_at" in out
    assert out["schema_version"] == 1
    assert len(out["universe"]) == 2
    tickers = {e["ticker"] for e in out["universe"]}
    assert tickers == {"D05", "A17U"}


def test_write_universe_round_trips(tmp_path: Path):
    snaps = [make_snap("D05")]
    path = tmp_path / "out.json"
    write_universe(snaps, path)
    data = json.loads(path.read_text())
    assert data["universe"][0]["ticker"] == "D05"
    assert "score" in data["universe"][0]
    assert "score_breakdown" in data["universe"][0]
