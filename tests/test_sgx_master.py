"""Tests for sg_dividend_data.sources.sgx_master — no live network."""
from __future__ import annotations
import json
from unittest.mock import MagicMock, patch

import pytest

from sg_dividend_data.sources.sgx_master import (
    discover_candidate_tickers,
    fetch_sgx_master,
    sgx_type_to_sector,
)


def _fake_response(prices: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "meta": {"code": "200", "totalPages": 1, "totalItems": 1},
        "data": {"prices": prices},
    }
    return resp


def test_fetch_sgx_master_filters_to_equity_types(tmp_path):
    prices = [
        {"nc": "D05", "type": "stocks"},
        {"nc": "ES3", "type": "etfs"},
        {"nc": "A17U", "type": "reits"},
        {"nc": "S58", "type": "businesstrusts"},
        {"nc": "ABCD1", "type": "companywarrants"},  # filtered out
        {"nc": "EFGH2", "type": "dlcertificates"},   # filtered out
        {"nc": None, "type": "stocks"},              # filtered out
        {"nc": "IJKL3", "type": "adrs"},             # filtered out
    ]
    with patch(
        "sg_dividend_data.sources.sgx_master.requests.get",
        return_value=_fake_response(prices),
    ):
        secs = fetch_sgx_master(
            cache_path=tmp_path / "cache.json",
            use_cache=False,
        )
    assert {s.ticker for s in secs} == {"D05", "ES3", "A17U", "S58"}


def test_fetch_sgx_master_deduplicates(tmp_path):
    prices = [
        {"nc": "D05", "type": "stocks"},
        {"nc": "D05", "type": "stocks"},  # duplicate
    ]
    with patch(
        "sg_dividend_data.sources.sgx_master.requests.get",
        return_value=_fake_response(prices),
    ):
        secs = fetch_sgx_master(
            cache_path=tmp_path / "cache.json",
            use_cache=False,
        )
    assert len(secs) == 1
    assert secs[0].ticker == "D05"


def test_fetch_sgx_master_returns_empty_on_network_failure(tmp_path):
    with patch(
        "sg_dividend_data.sources.sgx_master.requests.get",
        side_effect=Exception("connection refused"),
    ):
        secs = fetch_sgx_master(
            cache_path=tmp_path / "cache.json",
            use_cache=False,
        )
    # Returns empty rather than raising — caller falls back to curated list.
    assert secs == []


def test_fetch_sgx_master_uses_cache(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps([{"nc": "CACHED", "type": "stocks"}]))
    with patch(
        "sg_dividend_data.sources.sgx_master.requests.get",
        side_effect=AssertionError("should not have been called"),
    ):
        secs = fetch_sgx_master(cache_path=cache, use_cache=True)
    assert [s.ticker for s in secs] == ["CACHED"]


def test_discover_candidate_tickers_unions_extras(tmp_path):
    prices = [{"nc": "DISC1", "type": "stocks"}, {"nc": "DISC2", "type": "reits"}]
    with patch(
        "sg_dividend_data.sources.sgx_master.requests.get",
        return_value=_fake_response(prices),
    ):
        tickers = discover_candidate_tickers(
            extra=["CURATED1", "DISC1", "CURATED2"],
            cache_path=tmp_path / "cache.json",
            use_cache=False,
        )
    # Discovered come first, curated appended in order, dedupe applied.
    assert tickers == ["DISC1", "DISC2", "CURATED1", "CURATED2"]


def test_sgx_type_to_sector():
    assert sgx_type_to_sector("reits") == "REITs"
    assert sgx_type_to_sector("etfs") == "Other"
    assert sgx_type_to_sector("businesstrusts") == "Business Trusts"
    assert sgx_type_to_sector("stocks") is None  # let downstream decide
    assert sgx_type_to_sector("unknown") is None
