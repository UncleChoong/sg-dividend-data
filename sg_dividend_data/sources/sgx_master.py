"""Fetch the live SGX securities master list from api.sgx.com.

This is an undocumented endpoint — it's what sgx.com itself uses to render
its stock screener — so the shape can change without notice. Wrap it in
graceful failure: if it returns 0 tickers, the caller should fall back to
the curated SGX_DIVIDEND_TICKERS list rather than publishing an empty
universe.

Cached locally for 1 day so we don't hammer the endpoint during development.
"""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set

import requests

log = logging.getLogger(__name__)

# SGX classifies every security into a `type`. Anything not in this set is
# a derivative/structured product we don't want in a dividend app.
EQUITY_TYPES: Set[str] = {
    "stocks",
    "etfs",
    "reits",
    "businesstrusts",
}

# Default endpoint + a basic User-Agent (SGX rejects empty UA).
SGX_ENDPOINT = (
    "https://api.sgx.com/securities/v1.1"
    "?excludetypes=bonds&params=nc,b"
)
USER_AGENT = "Mozilla/5.0 (compatible; APY-bot/1.0)"

# Local cache so dev iteration doesn't hit the network every refresh.
CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_CACHE_PATH = Path.home() / ".cache" / "apy" / "sgx_master.json"


@dataclass
class SgxSecurity:
    ticker: str
    sgx_type: str  # 'stocks' | 'etfs' | 'reits' | 'businesstrusts'


def _read_cache(path: Path) -> Optional[list[dict]]:
    if not path.exists():
        return None
    try:
        age = time.time() - path.stat().st_mtime
        if age > CACHE_TTL_SECONDS:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("sgx_master cache read failed: %s", exc)
        return None


def _write_cache(path: Path, prices: list[dict]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(prices), encoding="utf-8")
    except Exception as exc:
        log.warning("sgx_master cache write failed: %s", exc)


def fetch_sgx_master(
    *,
    cache_path: Optional[Path] = DEFAULT_CACHE_PATH,
    use_cache: bool = True,
    timeout: float = 30.0,
) -> List[SgxSecurity]:
    """Fetch the SGX securities master, filtered to equity types only.

    Returns an empty list (rather than raising) on network failure so the
    caller can fall back to the curated tickers.
    """
    prices: Optional[list[dict]] = None

    if use_cache and cache_path is not None:
        prices = _read_cache(cache_path)
        if prices is not None:
            log.info("sgx_master: using cached response (%d entries)", len(prices))

    if prices is None:
        try:
            log.info("sgx_master: fetching %s", SGX_ENDPOINT)
            resp = requests.get(
                SGX_ENDPOINT,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            prices = payload.get("data", {}).get("prices") or []
            if cache_path is not None:
                _write_cache(cache_path, prices)
        except Exception as exc:
            log.error("sgx_master: fetch failed: %s", exc)
            return []

    out: List[SgxSecurity] = []
    seen: Set[str] = set()
    for row in prices:
        t = row.get("type")
        nc = row.get("nc")
        if not nc or not isinstance(nc, str):
            continue
        if t not in EQUITY_TYPES:
            continue
        if nc in seen:
            continue
        seen.add(nc)
        out.append(SgxSecurity(ticker=nc, sgx_type=t))
    log.info("sgx_master: %d equity securities (from %d total)", len(out), len(prices))
    return out


def discover_candidate_tickers(
    extra: Optional[Iterable[str]] = None,
    *,
    cache_path: Optional[Path] = DEFAULT_CACHE_PATH,
    use_cache: bool = True,
) -> List[str]:
    """Convenience: return a deduplicated list of bare SGX ticker codes,
    unioned with `extra` (typically the curated SGX_DIVIDEND_TICKERS list).
    """
    discovered = [s.ticker for s in fetch_sgx_master(
        cache_path=cache_path, use_cache=use_cache,
    )]
    if extra:
        seen = set(discovered)
        for t in extra:
            if t not in seen:
                seen.add(t)
                discovered.append(t)
    return discovered


def sgx_type_to_sector(sgx_type: str) -> Optional[str]:
    """Map SGX's authoritative security type to our internal sector label."""
    return {
        "reits": "REITs",
        "etfs": "Other",
        "businesstrusts": "Business Trusts",
        # 'stocks' is too generic — let downstream classify_sector decide
        "stocks": None,
    }.get(sgx_type)
