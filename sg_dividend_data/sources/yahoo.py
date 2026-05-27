"""Scrape Yahoo Finance quote page for an SGX ticker."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


@dataclass
class YahooQuote:
    price: float
    market_cap: Optional[float]
    ttm_yield_pct: Optional[float]
    beta: Optional[float]


def fetch_quote(ticker: str, *, session: Optional[requests.Session] = None) -> YahooQuote:
    s = session or requests.Session()
    url = f"https://finance.yahoo.com/quote/{ticker}.SI/"
    r = s.get(url, headers=UA, timeout=15)
    r.raise_for_status()
    return parse_quote_html(r.text)


def parse_quote_html(html: str) -> YahooQuote:
    # Strategy 1: __NEXT_DATA__ JSON (older Yahoo Finance format)
    soup = BeautifulSoup(html, "html.parser")
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            data = json.loads(next_data.string)
            return _from_next_data(data)
        except (ValueError, KeyError):
            pass

    # Strategy 2: regex sniff visible price + yield from page text.
    # Yahoo Finance embeds data in two forms:
    #   a) plain JSON:   "regularMarketPrice":{"raw":62.18,...}
    #   b) escaped JSON: \"regularMarketPrice\":{\"raw\":62.18,...}  (inside a JS string)
    price = _find_price(html)
    yield_pct = _find_yield(html)
    mcap = _find_market_cap(html)
    beta = _find_beta(html, soup)
    if price is None:
        raise ValueError("yahoo: could not parse price")
    return YahooQuote(price=price, market_cap=mcap, ttm_yield_pct=yield_pct, beta=beta)


def _from_next_data(data: dict) -> YahooQuote:
    def find(node, key):
        if isinstance(node, dict):
            if key in node and isinstance(node[key], (int, float)):
                return node[key]
            for v in node.values():
                r = find(v, key)
                if r is not None:
                    return r
        elif isinstance(node, list):
            for v in node:
                r = find(v, key)
                if r is not None:
                    return r
        return None

    price = find(data, "regularMarketPrice")
    mcap = find(data, "marketCap")
    yld = find(data, "trailingAnnualDividendYield")
    beta = find(data, "beta")
    if price is None:
        raise ValueError("yahoo: regularMarketPrice missing from __NEXT_DATA__")
    return YahooQuote(
        price=float(price),
        market_cap=float(mcap) if mcap else None,
        ttm_yield_pct=float(yld) * 100 if yld and yld < 1 else (float(yld) if yld else None),
        beta=float(beta) if beta else None,
    )


# ---------------------------------------------------------------------------
# Regex helpers — handle both plain and JS-escaped JSON forms.
# Current Yahoo Finance (2026) embeds the main-ticker data as a doubly-escaped
# JS string: \\"key\\":{\\"raw\\":VALUE.  Sidebar / watchlist data appears
# earlier in the page as plain JSON: "key":{"raw":VALUE.
# We prefer the escaped form so we always read the page's primary ticker.
# ---------------------------------------------------------------------------

def _raw_pattern_escaped(key: str, value_pat: str = r"[-0-9.E+]+") -> str:
    """Match escaped JSON form: \\"key\\":{\\"raw\\":VALUE (JS string embeds)."""
    escaped_key = re.escape(key)
    return r'\\"' + escaped_key + r'\\":\{\\"raw\\":(' + value_pat + r")"


def _raw_pattern_plain(key: str, value_pat: str = r"[-0-9.E+]+") -> str:
    """Match plain JSON form: \"key\":{\"raw\":VALUE."""
    escaped_key = re.escape(key)
    return r'"' + escaped_key + r'":\{"raw":(' + value_pat + r")"


def _find_raw(html: str, key: str, value_pat: str = r"[0-9.E+]+") -> Optional[str]:
    """Return the first raw value for *key*, preferring the escaped JSON form
    (which is the main-ticker data block in the current Yahoo Finance layout)
    over the plain JSON form (which may appear in sidebar/watchlist blocks first)."""
    m = re.search(_raw_pattern_escaped(key, value_pat), html)
    if m:
        return m.group(1)
    m = re.search(_raw_pattern_plain(key, value_pat), html)
    return m.group(1) if m else None


def _find_price(html: str) -> Optional[float]:
    v = _find_raw(html, "regularMarketPrice", r"[0-9.]+")
    if v is not None:
        return float(v)
    # Fallback: bare scalar (some API responses)
    m = re.search(r'"regularMarketPrice":\s*([0-9.]+)', html)
    return float(m.group(1)) if m else None


def _find_yield(html: str) -> Optional[float]:
    v = _find_raw(html, "trailingAnnualDividendYield", r"[0-9.E+]+")
    if v is not None:
        val = float(v)
        return val * 100 if val < 1 else val
    return None


def _find_market_cap(html: str) -> Optional[float]:
    v = _find_raw(html, "marketCap", r"[0-9.E+]+")
    return float(v) if v is not None else None


def _find_beta(html: str, soup: Optional[BeautifulSoup] = None) -> Optional[float]:
    # Try escaped/plain JSON first
    v = _find_raw(html, "beta", r"-?[0-9.]+")
    if v is not None:
        return float(v)
    # Newer Yahoo Finance renders beta in an HTML table as a visible span
    # <span class="label ...">Beta (5Y Monthly)</span> <span class="value ...">0.27</span>
    if soup is None:
        soup = BeautifulSoup(html, "html.parser")
    for label_span in soup.find_all("span", title=re.compile(r"Beta", re.I)):
        parent = label_span.find_parent()
        if parent:
            value_span = parent.find("span", class_=re.compile(r"value"))
            if value_span:
                try:
                    return float(value_span.get_text(strip=True))
                except ValueError:
                    pass
    return None
