from sg_dividend_data.enrichment import ENRICHMENT, _trim_summary, enrich_entry


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
    assert entry["name"] == "DBS Group"


def test_enrich_entry_for_unknown_ticker_with_yf_fallback():
    entry = {
        "ticker": "XXX",
        "sector": "Industrials",
        "name": "Some Industrial Co",
        "_yf_summary": "Some Industrial Co manufactures widgets across Asia. "
                       "It pays a dividend twice a year.",
        "_yf_industry": "Specialty Industrial Machinery",
    }
    enrich_entry(entry)
    assert "Some Industrial Co manufactures widgets" in entry["description"]
    # `industry` stays on our coarse sector bucket so filter chips still work
    assert entry["industry"] == "Industrials"
    # Fine-grained yfinance industry is stashed for display only
    assert entry["industry_detail"] == "Specialty Industrial Machinery"
    # name is left untouched (set upstream from yfinance longName)
    assert entry["name"] == "Some Industrial Co"
    # temporary keys consumed
    assert "_yf_summary" not in entry
    assert "_yf_industry" not in entry


def test_enrich_entry_for_unknown_ticker_no_yf_data():
    entry = {"ticker": "XXX", "sector": "Other", "name": "XXX"}
    enrich_entry(entry)
    assert entry["description"] == ""
    assert entry["industry"] == "Other"
    assert entry["market_cap_sgd"] is None
    assert entry["name"] == "XXX"


def test_enrich_entry_preserves_upstream_market_cap_for_unknown():
    entry = {
        "ticker": "XXX", "sector": "Other", "name": "XXX",
        "market_cap_sgd": 9.9e8,
    }
    enrich_entry(entry)
    assert entry["market_cap_sgd"] == 9.9e8


def test_trim_summary_truncates_at_sentence_boundary():
    long = "Sentence one. Sentence two. " + ("filler word " * 100)
    trimmed = _trim_summary(long, max_chars=200)
    assert len(trimmed) <= 201
    # Should end on a sentence boundary if found in the back half.
    assert trimmed.endswith(".") or trimmed.endswith("…")


def test_trim_summary_passes_short_strings_through():
    short = "Short description."
    assert _trim_summary(short) == "Short description."
