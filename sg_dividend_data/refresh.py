"""Refresh the SG dividend universe and upload to R2."""
from __future__ import annotations
import argparse
import logging
import sys
import traceback
from pathlib import Path
from typing import List, Optional

from sg_dividend_data.alerts import telegram_alert
from sg_dividend_data.models import TickerSnapshot
from sg_dividend_data.sources.dividend_history import fetch_div_history
from sg_dividend_data.sources.yahoo import fetch_quote
from sg_dividend_data.universe import SECTOR_MAP, SGX_DIVIDEND_TICKERS, lot_size_for
from sg_dividend_data.uploader import upload_to_r2
from sg_dividend_data.writer import write_universe

log = logging.getLogger("refresh")

# Refuse to publish to R2 if fewer than this many tickers scraped successfully.
# Protects against overwriting a good R2 file with a near-empty one when most
# scrapers fail (e.g. during a network outage or anti-bot block wave).
MIN_TICKERS_FOR_PUBLISH = 5


def _compute_payout_ratio(history: list, snapshot=None) -> Optional[float]:
    # MVP: we don't have EPS scraping yet; return None → scoring uses fallback.
    # TODO(v2): pull EPS from Yahoo and compute payout = last_div / eps
    return None


def _compute_price_vol_90d(ticker: str) -> Optional[float]:
    # MVP: stub. TODO(v2): implement via Yahoo chart endpoint.
    return None


def build_snapshot(ticker: str) -> TickerSnapshot:
    yq = fetch_quote(ticker)
    hist: list = []
    try:
        hist = fetch_div_history(ticker)
    except Exception as e:
        log.warning("div history fetch failed for %s: %s (using empty history)", ticker, e)
    name = ticker
    return TickerSnapshot(
        ticker=ticker,
        name=name,
        sector=SECTOR_MAP.get(ticker, "Other"),
        price=yq.price,
        market_cap=yq.market_cap or 0.0,
        ttm_yield_pct=yq.ttm_yield_pct or 0.0,
        lot_size=lot_size_for(ticker),
        div_history_5y=hist,
        payout_ratio=_compute_payout_ratio(hist),
        price_vol_90d=_compute_price_vol_90d(ticker),
    )


def refresh_all(*, dry_run: bool, output: Path) -> List[TickerSnapshot]:
    snapshots: list[TickerSnapshot] = []
    failures: list[str] = []
    for t in SGX_DIVIDEND_TICKERS:
        try:
            snap = build_snapshot(t)
            snapshots.append(snap)
            log.info("ok %s price=%.2f yield=%.2f%%", t, snap.price, snap.ttm_yield_pct)
        except Exception as exc:
            log.exception("fail %s: %s", t, exc)
            failures.append(f"{t}: {exc}")
    write_universe(snapshots, output)
    if failures:
        telegram_alert(f"SG dividend refresh: {len(failures)} failures\n" + "\n".join(failures[:20]))
    if not dry_run:
        if len(snapshots) < MIN_TICKERS_FOR_PUBLISH:
            msg = (
                f"SG dividend refresh: only {len(snapshots)} tickers succeeded "
                f"(minimum {MIN_TICKERS_FOR_PUBLISH}), NOT uploading to R2. "
                f"{len(failures)} failures."
            )
            telegram_alert(msg + "\n" + "\n".join(failures[:20]))
            log.error(msg)
            return snapshots
        upload_to_r2(output)
    return snapshots


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="write JSON locally, do not upload")
    p.add_argument("--output", default="sg_dividend_universe.json")
    args = p.parse_args(argv)
    try:
        snaps = refresh_all(dry_run=args.dry_run, output=Path(args.output))
        log.info("refresh complete: %d tickers", len(snaps))
        return 0
    except Exception:
        tb = traceback.format_exc()
        telegram_alert(f"SG dividend refresh CRASH:\n{tb[-3000:]}")
        log.error("crash:\n%s", tb)
        return 1


if __name__ == "__main__":
    sys.exit(main())
