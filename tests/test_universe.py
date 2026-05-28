from sg_dividend_data.universe import (
    SECTOR_MAP,
    SGX_DIVIDEND_TICKERS,
    classify_sector,
    lot_size_for,
)


ALLOWED_SECTORS = {
    "Banks", "Utilities", "Telco", "REITs", "Business Trusts",
    "Industrials", "Consumer", "Healthcare", "Other",
}


def test_universe_includes_local_banks():
    for t in ("D05", "O39", "U11"):
        assert t in SGX_DIVIDEND_TICKERS


def test_universe_includes_core_reits():
    for t in ("A17U", "C38U", "M44U", "N2IU", "ME8U"):
        assert t in SGX_DIVIDEND_TICKERS


def test_universe_is_expanded():
    # The list should be a comprehensive set of SGX dividend payers, not just
    # the original 30-ish curated entries. We keep this loose so adding new
    # tickers doesn't break the test.
    assert len(SGX_DIVIDEND_TICKERS) >= 80


def test_sector_map_values_are_known():
    for t, sec in SECTOR_MAP.items():
        assert sec in ALLOWED_SECTORS, f"{t} has unknown sector {sec}"


def test_classify_sector_uses_map_first():
    assert classify_sector("D05") == "Banks"
    assert classify_sector("A17U") == "REITs"


def test_classify_sector_reit_suffix_heuristic():
    # SGX REIT codes end in U — should be detected even without an explicit map entry.
    assert classify_sector("XYZU") == "REITs"


def test_classify_sector_falls_back_to_yfinance_sector():
    assert classify_sector("NEW1", yf_sector="Financial Services") == "Banks"
    assert classify_sector("NEW2", yf_sector="Consumer Defensive") == "Consumer"
    assert classify_sector("NEW3", yf_sector="Communication Services") == "Telco"
    # SGX real-estate names default to Industrials (developers); REITs are
    # caught earlier by the ticker-ends-in-U convention.
    assert classify_sector("NEW4", yf_sector="Real Estate") == "Industrials"


def test_classify_sector_unknown_is_other():
    assert classify_sector("ZZ1") == "Other"


def test_lot_size_default_100():
    assert lot_size_for("D05") == 100


def test_lot_size_etfs_can_differ():
    assert isinstance(lot_size_for("ES3"), int)
