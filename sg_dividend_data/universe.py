"""Curated SGX dividend-paying tickers + sector classification."""
from __future__ import annotations
from typing import Dict, List

# Hand-curated. Add/remove tickers here. Each must also appear in SECTOR_MAP.
SGX_DIVIDEND_TICKERS: List[str] = [
    # Banks
    "D05", "O39", "U11",
    # Utilities / Telco / Infra
    "Z74", "CC3", "AJBU", "CJLU",
    # Core S-REITs
    "A17U", "C38U", "M44U", "N2IU", "ME8U", "T82U", "J69U", "BUOU", "C2PU",
    "AU8U", "M1GU", "ACV", "T39",
    # Business Trusts / Yield plays
    "U96", "S58",
    # Industrials / Defensives
    "S63", "Y92", "C07", "BN4",
    # Consumer / F&B
    "F34", "S68",  # S68 is SGX itself
    # ETFs (high-yield)
    "ES3", "QL3", "G3B",
]
# Deduplicate while preserving order
SGX_DIVIDEND_TICKERS = list(dict.fromkeys(SGX_DIVIDEND_TICKERS))

SECTOR_MAP: Dict[str, str] = {
    "D05": "Banks", "O39": "Banks", "U11": "Banks",
    "Z74": "Telco", "CC3": "Telco",
    "AJBU": "Utilities", "CJLU": "Utilities",
    "A17U": "REITs", "C38U": "REITs", "M44U": "REITs", "N2IU": "REITs", "ME8U": "REITs",
    "T82U": "REITs", "J69U": "REITs", "BUOU": "REITs", "C2PU": "REITs",
    "AU8U": "REITs", "M1GU": "REITs", "ACV": "REITs", "T39": "REITs",
    "U96": "Business Trusts", "S58": "Business Trusts",
    "S63": "Industrials", "Y92": "Consumer", "C07": "Consumer", "BN4": "Industrials",
    "F34": "Consumer", "S68": "Industrials",
    "ES3": "Other", "QL3": "Other", "G3B": "Other",
}

# Default SGX lot size is 100 shares. Exceptions can be added here.
_LOT_OVERRIDES: Dict[str, int] = {}

def lot_size_for(ticker: str) -> int:
    return _LOT_OVERRIDES.get(ticker, 100)
