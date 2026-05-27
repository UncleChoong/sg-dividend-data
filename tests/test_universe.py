from sg_dividend_data.universe import SGX_DIVIDEND_TICKERS, SECTOR_MAP, lot_size_for

def test_universe_includes_local_banks():
    for t in ("D05", "O39", "U11"):
        assert t in SGX_DIVIDEND_TICKERS

def test_universe_includes_core_reits():
    for t in ("A17U", "C38U", "M44U", "N2IU", "ME8U"):
        assert t in SGX_DIVIDEND_TICKERS

def test_sector_map_covers_every_ticker():
    missing = [t for t in SGX_DIVIDEND_TICKERS if t not in SECTOR_MAP]
    assert missing == [], f"sector missing for: {missing}"

def test_sectors_are_known():
    allowed = {"Banks", "Utilities", "Telco", "REITs", "Business Trusts", "Industrials",
               "Consumer", "Healthcare", "Other"}
    for t, sec in SECTOR_MAP.items():
        assert sec in allowed, f"{t} has unknown sector {sec}"

def test_lot_size_default_100():
    assert lot_size_for("D05") == 100

def test_lot_size_etfs_can_differ():
    # ES3 (STI ETF) is 100; QL3 also 100 in SGX retail. Just check function returns int.
    assert isinstance(lot_size_for("ES3"), int)
