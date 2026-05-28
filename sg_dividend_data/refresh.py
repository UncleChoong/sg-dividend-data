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
from sg_dividend_data.universe import (
    SGX_DIVIDEND_TICKERS,
    classify_sector,
    lot_size_for,
)
from sg_dividend_data.uploader import upload_to_r2
from sg_dividend_data.writer import write_universe

log = logging.getLogger("refresh")

# Refuse to publish to R2 if fewer than this many tickers scraped successfully.
MIN_TICKERS_FOR_PUBLISH = 5

# Minimum TTM yield (in %) for a ticker to count as "dividend-paying" and stay
# in the published universe. Anything lower is either a junk feed or a stock
# that has effectively stopped paying — out of scope for a dividend app.
MIN_DIVIDEND_YIELD_PCT = 0.5


def _compute_payout_ratio(history: list, snapshot=None) -> Optional[float]:
    return None


def _compute_price_vol_90d(ticker: str) -> Optional[float]:
    return None


def build_snapshot(ticker: str) -> TickerSnapshot:
    yq = fetch_quote(ticker)
    hist: list = []
    try:
        hist = fetch_div_history(ticker)
    except Exception as e:
        log.warning("div history fetch failed for %s: %s (using empty history)", ticker, e)
    # Prefer yfinance's longName when present, otherwise fall back to the ticker
    # code (the writer/enrichment layer will override with curated names where
    # available).
    name = yq.long_name or ticker
    sector = classify_sector(ticker, yq.yf_sector)
    return TickerSnapshot(
        ticker=ticker,
        name=name,
        sector=sector,
        price=yq.price,
        market_cap=yq.market_cap or 0.0,
        ttm_yield_pct=yq.ttm_yield_pct or 0.0,
        lot_size=lot_size_for(ticker),
        div_history_5y=hist,
        payout_ratio=_compute_payout_ratio(hist),
        price_vol_90d=_compute_price_vol_90d(ticker),
        yf_long_name=yq.long_name,
        yf_sector=yq.yf_sector,
        yf_industry=yq.yf_industry,
        yf_summary=yq.long_business_summary,
    )


def refresh_all(*, dry_run: bool, output: Path) -> List[TickerSnapshot]:
    snapshots: list[TickerSnapshot] = []
    failures: list[str] = []
    skipped_low_yield: list[str] = []
    for t in SGX_DIVIDEND_TICKERS:
        try:
            snap = build_snapshot(t)
            if snap.ttm_yield_pct < MIN_DIVIDEND_YIELD_PCT:
                skipped_low_yield.append(f"{t} ({snap.ttm_yield_pct:.2f}%)")
                log.info(
                    "skip %s — yield %.2f%% below %.2f%% cutoff",
                    t, snap.ttm_yield_pct, MIN_DIVIDEND_YIELD_PCT,
                )
                continue
            snapshots.append(snap)
            log.info("ok %s price=%.2f yield=%.2f%%", t, snap.price, snap.ttm_yield_pct)
        except Exception as exc:
            log.warning("fail %s: %s", t, exc)
            failures.append(f"{t}: {exc}")
    log.info(
        "kept=%d failed=%d skipped_low_yield=%d",
        len(snapshots), len(failures), len(skipped_low_yield),
    )
    write_universe(snapshots, output)
    if failures and not dry_run:
        telegram_alert(
            f"SG dividend refresh: {len(failures)} failures\n"
            + "\n".join(failures[:20])
        )
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
