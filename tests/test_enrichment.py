from sg_dividend_data.enrichment import ENRICHMENT, enrich_entry


def test_enrichment_covers_curated_tickers():
    for t in ("D05", "O39", "U11", "A17U", "ES3", "QL3"):
        assert t in ENRICHMENT
        e = ENRICHMENT[t]
        assert e["description"]
        assert e["industry"]
        assert e["market_cap_sgd"] is None or e["market_cap_sgd"] > 0


def test_enrich_entry_for_curated_ticker():
    entry = {"ticker": "D05", "sector": "Banks", "name": "D05"}
    enrich_entry(entry)
    assert entry["description"]
    assert entry["industry"] == "Banks"
    assert entry["market_cap_sgd"] > 1e10
    # name was overridden to curated full name
    assert entry["name"] == "DBS Group"


def test_enrich_entry_for_unknown_ticker_falls_back():
    entry = {"ticker": "XXX", "sector": "Other", "name": "XXX"}
    enrich_entry(entry)
    assert entry["description"] == ""
    assert entry["industry"] == "Other"
    assert entry["market_cap_sgd"] is None
    # name unchanged
    assert entry["name"] == "XXX"


def test_enrich_entry_preserves_upstream_market_cap_for_unknown():
    entry = {
        "ticker": "XXX", "sector": "Other", "name": "XXX",
        "market_cap_sgd": 9.9e8,
    }
    enrich_entry(entry)
    assert entry["market_cap_sgd"] == 9.9e8
