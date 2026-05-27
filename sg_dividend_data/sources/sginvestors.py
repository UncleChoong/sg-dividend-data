"""Scrape SGinvestors.io for 5y dividend history."""
from __future__ import annotations
import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0"}
SLUG_OVERRIDES = {
    "D05": "d05-dbs-group",
    "O39": "o39-ocbc-bank",
    "U11": "u11-uob",
    "Z74": "z74-singtel",
}


def fetch_div_history(ticker: str, *, session: Optional[requests.Session] = None) -> List[Optional[float]]:
    slug = SLUG_OVERRIDES.get(ticker)
    if not slug:
        slug = ticker.lower()
    s = session or requests.Session()
    url = f"https://sginvestors.io/sgx/stock/{slug}/share-dividend-history"
    r = s.get(url, headers=UA, timeout=15)
    r.raise_for_status()
    return parse_div_history(r.text)


def parse_div_history(html: str) -> List[Optional[float]]:
    soup = BeautifulSoup(html, "html.parser")
    by_year: dict[int, float] = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            year = _extract_year(cells)
            amt = _extract_dividend(cells)
            if year and amt is not None:
                by_year[year] = by_year.get(year, 0.0) + amt
    if not by_year:
        return [None] * 5
    latest = max(by_year)
    return [by_year.get(latest - i) for i in range(5)]


_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _extract_year(cells: list[str]) -> Optional[int]:
    for c in cells:
        m = _YEAR_RE.search(c)
        if m:
            return int(m.group(1))
    return None


def _extract_dividend(cells: list[str]) -> Optional[float]:
    for c in cells:
        c2 = c.replace("S$", "").replace("$", "").replace("SGD", "").replace(",", "").strip()
        m = re.fullmatch(r"(\d+\.\d{1,4})", c2)
        if m:
            return float(m.group(1))
    return None
