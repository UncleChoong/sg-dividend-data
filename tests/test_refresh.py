import datetime
from sg_dividend_data.refresh import _is_zombie_payer, build_snapshot
from sg_dividend_data.models import TickerSnapshot
from sg_dividend_data.sources.yahoo import YahooQuote


def _make_yq(**kw) -> YahooQuote:
    base = dict(price=42.0, market_cap=1e11, ttm_yield_pct=5.0, beta=1.0)
    base.update(kw)
    return YahooQuote(**base)


def test_build_snapshot_assembles_fields(monkeypatch):
    yq = _make_yq(currency="SGD", last_dividend_date="2026-04-01")
    monkeypatch.setattr("sg_dividend_data.refresh.fetch_quote", lambda t: yq)
    monkeypatch.setattr("sg_dividend_data.refresh.fetch_div_history",
                        lambda t: [1.9, 1.6, 1.4, 1.2, 1.2])
    monkeypatch.setattr("sg_dividend_data.refresh._compute_payout_ratio", lambda *a, **k: 0.5)
    monkeypatch.setattr("sg_dividend_data.refresh._compute_price_vol_90d", lambda *a, **k: 0.18)

    snap = build_snapshot("D05")
    assert snap.ticker == "D05"
    assert snap.sector == "Banks"
    assert snap.price == 42.0
    assert snap.ttm_yield_pct == 5.0
    assert snap.currency == "SGD"
    assert snap.last_dividend_date == "2026-04-01"
    assert snap.div_history_5y == [1.9, 1.6, 1.4, 1.2, 1.2]


def test_refresh_skips_upload_when_no_snapshots(monkeypatch, tmp_path):
    from sg_dividend_data import refresh as r

    monkeypatch.setattr(
        r, "build_snapshot",
        lambda t, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    called = {"n": 0}
    monkeypatch.setattr(r, "upload_to_r2",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    monkeypatch.setattr(r, "telegram_alert", lambda *a, **k: True)

    output = tmp_path / "x.json"
    snaps = r.refresh_all(dry_run=False, output=output)

    assert snaps == []
    assert called["n"] == 0


# ─── Currency filter ──────────────────────────────────────────────────────
def _make_snapshot(**kw) -> TickerSnapshot:
    base = dict(
        ticker="X", name="X", sector="Industrials",
        price=10.0, market_cap=0, ttm_yield_pct=4.0, lot_size=100,
        div_history_5y=[0.4] * 5,
        currency="SGD",
        last_dividend_date=datetime.date.today().isoformat(),
    )
    base.update(kw)
    return TickerSnapshot(**base)


def test_refresh_drops_non_sgd_currency(monkeypatch, tmp_path):
    from sg_dividend_data import refresh as r

    snapshots = {
        "D05": _make_snapshot(ticker="D05", currency="SGD"),
        "J36": _make_snapshot(ticker="J36", currency="USD"),
        "MENU": _make_snapshot(ticker="MENU", currency="GBP"),
    }
    monkeypatch.setattr(
        r, "build_snapshot",
        lambda t, **kw: snapshots[t],
    )
    monkeypatch.setattr(
        r, "_build_candidate_universe",
        lambda **kw: [(t, None) for t in snapshots],
    )
    monkeypatch.setattr(r, "upload_to_r2", lambda *a, **k: None)
    monkeypatch.setattr(r, "telegram_alert", lambda *a, **k: True)

    out = r.refresh_all(dry_run=True, output=tmp_path / "u.json")
    kept = {s.ticker for s in out}
    assert kept == {"D05"}, f"non-SGD tickers leaked through: {kept}"


# ─── Zombie filter ────────────────────────────────────────────────────────
def test_is_zombie_payer_drops_old_payments():
    snap = _make_snapshot(last_dividend_date="2011-08-23")
    assert _is_zombie_payer(snap) is True


def test_is_zombie_payer_keeps_recent():
    today = datetime.date.today().isoformat()
    assert _is_zombie_payer(_make_snapshot(last_dividend_date=today)) is False


def test_is_zombie_payer_keeps_unknown():
    """No dividend date at all — treat as a brand-new listing, let it through.
    The bundled history will be empty and the UI shows that gap."""
    assert _is_zombie_payer(_make_snapshot(last_dividend_date=None)) is False


def test_refresh_drops_zombie_payers(monkeypatch, tmp_path):
    from sg_dividend_data import refresh as r

    snapshots = {
        "D05": _make_snapshot(
            ticker="D05",
            last_dividend_date=datetime.date.today().isoformat(),
        ),
        "AWK": _make_snapshot(
            ticker="AWK",
            ttm_yield_pct=15.0,  # Yahoo says it's high-yield...
            last_dividend_date="2011-08-23",  # ...but last paid 2011
        ),
    }
    monkeypatch.setattr(
        r, "build_snapshot",
        lambda t, **kw: snapshots[t],
    )
    monkeypatch.setattr(
        r, "_build_candidate_universe",
        lambda **kw: [(t, None) for t in snapshots],
    )
    monkeypatch.setattr(r, "upload_to_r2", lambda *a, **k: None)
    monkeypatch.setattr(r, "telegram_alert", lambda *a, **k: True)

    out = r.refresh_all(dry_run=True, output=tmp_path / "u.json")
    kept = {s.ticker for s in out}
    assert "AWK" not in kept, "zombie payer leaked through"
    assert "D05" in kept
