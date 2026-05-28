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
from sg_dividend_data.sources.sgx_master import (
    fetch_sgx_master,
    sgx_type_to_sector,
)
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

# Currencies accepted in the published universe. SGX-listed names that trade
# in USD/EUR/GBP (Jardine Matheson J36, Hongkong Land H78, Cromwell European
# Q5T, Elite UK MENU, etc.) get filtered out — displaying their USD prices
# with an "S$" prefix would mislead users running dividend simulations.
ACCEPTED_CURRENCIES = {"SGD", None}

# Tickers with no dividend payment in the last N days are filtered out.
# Catches zombie payers — companies that yfinance still reports a
# dividendYield for despite having actually stopped paying years ago
# (e.g. AWK Fuxing China Group last paid in 2011).
MAX_DAYS_SINCE_LAST_DIVIDEND = 730  # 2 years


def _compute_payout_ratio(history: list, snapshot=None) -> Optional[float]:
    return None


def _compute_price_vol_90d(ticker: str) -> Optional[float]:
    return None


def build_snapshot(ticker: str, *, sgx_sector_hint: Optional[str] = None) -> TickerSnapshot:
    """Build a TickerSnapshot from yfinance + optional SGX-type hint.

    `sgx_sector_hint`, when provided, takes precedence over yfinance's GICS
    sector — used by the auto-discover path so SGX's authoritative REIT /
    Business Trust classification is honoured.
    """
    yq = fetch_quote(ticker)
    hist: list = []
    try:
        hist = fetch_div_history(ticker)
    except Exception as e:
        log.warning("div history fetch failed for %s: %s (using empty history)", ticker, e)
    name = yq.long_name or ticker
    # Sector precedence: hardcoded SECTOR_MAP > SGX type hint > yfinance sector heuristic.
    sector = classify_sector(ticker, yq.yf_sector)
    if sgx_sector_hint and ticker not in _explicit_sector_overrides():
        sector = sgx_sector_hint
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
        currency=yq.currency,
        last_dividend_date=yq.last_dividend_date,
    )


def _is_zombie_payer(snap: TickerSnapshot) -> bool:
    """True if the most-recent dividend payment is older than the cutoff.

    Catches AWK-style entries where Yahoo still reports a dividendYield
    but the underlying company stopped paying years ago.
    """
    import datetime
    if not snap.last_dividend_date:
        # No dividend history at all — yield can only come from Yahoo's
        # info fields which we've already learned are unreliable for
        # zombie payers. Treat as zombie unless yfinance gave us a
        # current yield AND the ticker has zero recorded payments
        # (likely a new listing — let it through, the bundled history
        # will simply be empty and the user sees that).
        return False
    try:
        last = datetime.date.fromisoformat(snap.last_dividend_date)
        age_days = (datetime.date.today() - last).days
        return age_days > MAX_DAYS_SINCE_LAST_DIVIDEND
    except Exception:
        return False


def _explicit_sector_overrides() -> set[str]:
    """Tickers where our hand-curated SECTOR_MAP wins over the SGX type hint.
    Returns the set of tickers explicitly mapped in universe.SECTOR_MAP.
    """
    from sg_dividend_data.universe import SECTOR_MAP
    return set(SECTOR_MAP.keys())


def _build_candidate_universe(*, auto_discover: bool) -> list[tuple[str, Optional[str]]]:
    """Return [(ticker, sgx_sector_hint), ...] to feed the refresh loop.

    With auto_discover=True, unions curated + SGX-master tickers and tags
    each with the SGX-type-derived sector hint (REITs / ETFs / Business
    Trusts) where applicable.
    """
    if not auto_discover:
        return [(t, None) for t in SGX_DIVIDEND_TICKERS]

    sgx_secs = fetch_sgx_master()
    if not sgx_secs:
        log.warning(
            "sgx_master returned 0 securities — falling back to curated list only"
        )
        return [(t, None) for t in SGX_DIVIDEND_TICKERS]

    sgx_hints: dict[str, Optional[str]] = {
        s.ticker: sgx_type_to_sector(s.sgx_type) for s in sgx_secs
    }
    out: list[tuple[str, Optional[str]]] = []
    seen: set[str] = set()
    # Curated tickers first so they're preferred for ordering.
    for t in SGX_DIVIDEND_TICKERS:
        if t in seen:
            continue
        seen.add(t)
        out.append((t, sgx_hints.get(t)))
    for t, hint in sgx_hints.items():
        if t in seen:
            continue
        seen.add(t)
        out.append((t, hint))
    log.info(
        "candidate universe: curated=%d discovered=%d total=%d",
        len(SGX_DIVIDEND_TICKERS),
        len(sgx_hints),
        len(out),
    )
    return out


def refresh_all(
    *,
    dry_run: bool,
    output: Path,
    auto_discover: bool = False,
) -> List[TickerSnapshot]:
    snapshots: list[TickerSnapshot] = []
    failures: list[str] = []
    skipped_low_yield: list[str] = []
    skipped_currency: list[str] = []
    skipped_zombie: list[str] = []
    candidates = _build_candidate_universe(auto_discover=auto_discover)
    for t, hint in candidates:
        try:
            snap = build_snapshot(t, sgx_sector_hint=hint)
            if snap.currency not in ACCEPTED_CURRENCIES:
                skipped_currency.append(f"{t} ({snap.currency})")
                continue
            if snap.ttm_yield_pct < MIN_DIVIDEND_YIELD_PCT:
                skipped_low_yield.append(f"{t} ({snap.ttm_yield_pct:.2f}%)")
                continue
            if _is_zombie_payer(snap):
                skipped_zombie.append(f"{t} (last_div={snap.last_dividend_date})")
                continue
            snapshots.append(snap)
            log.info(
                "ok %s ccy=%s price=%.2f yield=%.2f%%",
                t, snap.currency or "?", snap.price, snap.ttm_yield_pct,
            )
        except Exception as exc:
            log.warning("fail %s: %s", t, exc)
            failures.append(f"{t}: {exc}")
    log.info(
        "kept=%d failed=%d skipped_low_yield=%d skipped_currency=%d skipped_zombie=%d",
        len(snapshots), len(failures), len(skipped_low_yield),
        len(skipped_currency), len(skipped_zombie),
    )
    if skipped_currency:
        log.info("non-SGD tickers filtered: %s", ", ".join(skipped_currency[:20]))
    if skipped_zombie:
        log.info("zombie payers filtered: %s", ", ".join(skipped_zombie[:20]))
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
    p.add_argument(
        "--auto-discover",
        action="store_true",
        help="Union curated list with the live SGX master from api.sgx.com",
    )
    args = p.parse_args(argv)
    try:
        snaps = refresh_all(
            dry_run=args.dry_run,
            output=Path(args.output),
            auto_discover=args.auto_discover,
        )
        log.info("refresh complete: %d tickers", len(snaps))
        return 0
    except Exception:
        tb = traceback.format_exc()
        telegram_alert(f"SG dividend refresh CRASH:\n{tb[-3000:]}")
        log.error("crash:\n%s", tb)
        return 1


if __name__ == "__main__":
    sys.exit(main())
