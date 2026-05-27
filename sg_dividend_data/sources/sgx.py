"""SGX corporate-actions JSON scraper for upcoming declared dividends."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from datetime import date

import requests
from dateutil.parser import parse as dt_parse

UA = {"User-Agent": "Mozilla/5.0"}


@dataclass
class DividendEvent:
    ticker: str
    name: str
    ex_date: Optional[date]
    payment_date: Optional[date]
    amount: Optional[float]


def fetch_corp_actions(*, session: Optional[requests.Session] = None) -> List[DividendEvent]:
    url = "https://api.sgx.com/securities/v1.1/corporate-actions?category=DIVIDEND"
    s = session or requests.Session()
    r = s.get(url, headers=UA, timeout=15)
    r.raise_for_status()
    return parse_corp_actions(r.json())


def parse_corp_actions(data: dict) -> List[DividendEvent]:
    raw = data.get("data") or data.get("items") or []
    out: list[DividendEvent] = []
    for row in raw:
        ticker = (row.get("stock-code") or row.get("ticker") or "").strip()
        name = (row.get("name") or row.get("stock-name") or "").strip()
        ex = _maybe_date(row.get("ex-date") or row.get("corporate-action-ex-date"))
        pay = _maybe_date(row.get("payment-date") or row.get("corporate-action-payment-date"))
        amt = _maybe_float(row.get("rate") or row.get("corporate-action-rate"))
        if ticker:
            out.append(DividendEvent(ticker=ticker, name=name, ex_date=ex, payment_date=pay, amount=amt))
    return out


def upcoming_for(ticker: str, events: List[DividendEvent]) -> List[DividendEvent]:
    today = date.today()
    return [e for e in events if e.ticker == ticker and (e.ex_date is None or e.ex_date >= today)]


def _maybe_date(s) -> Optional[date]:
    if not s:
        return None
    try:
        return dt_parse(str(s)).date()
    except (ValueError, TypeError):
        return None


def _maybe_float(s) -> Optional[float]:
    if s in (None, "", "-"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None
