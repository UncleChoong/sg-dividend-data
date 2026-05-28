"""Curated SGX dividend-paying tickers + sector classification.

This file lists the *candidate* universe. The refresh pipeline will:
  1) try yfinance for each ticker,
  2) skip ones that don't resolve (Yahoo no longer covers the symbol), and
  3) drop ones whose TTM dividend yield is below the cut-off (refresh.py).

So this list can be aggressive — the pipeline self-prunes. Add liberally;
junk gets filtered out at refresh time.

Sector classification falls back to yfinance's `sector` field for any
ticker not present in `SECTOR_MAP`, with REITs detected by the SGX
convention that REIT codes end in `U` (e.g. A17U Ascendas REIT).
"""
from __future__ import annotations
from typing import Dict, List

# ─────────────────────────────────────────────────────────────────────
# Candidate SGX dividend-paying tickers
# ─────────────────────────────────────────────────────────────────────
SGX_DIVIDEND_TICKERS: List[str] = [
    # ─── STI 30 Blue Chips ─────────────────────────────────────────
    # The 30 largest SGX-listed companies. Almost all pay regular dividends.
    "D05",   # DBS Group
    "O39",   # OCBC Bank
    "U11",   # United Overseas Bank
    "Z74",   # Singtel
    "Y92",   # Thai Beverage
    "C07",   # Jardine Cycle & Carriage
    "S58",   # SATS
    "S63",   # ST Engineering
    "9CI",   # CapitaLand Investment
    "F34",   # Wilmar International
    "J36",   # Jardine Matheson
    "H78",   # Hongkong Land
    "G13",   # Genting Singapore
    "V03",   # Venture Corp
    "BN4",   # Keppel Ltd
    "BS6",   # Yangzijiang Shipbuilding
    "U96",   # Sembcorp Industries
    "S68",   # Singapore Exchange (SGX)
    "D01",   # DFI Retail Group
    "S51",   # Seatrium
    "C6L",   # Singapore Airlines
    "U14",   # UOL Group
    "C09",   # City Developments
    "C52",   # ComfortDelGro

    # ─── REITs (S-REITs + business trusts) ────────────────────────
    # SGX is Asia's largest REIT hub. ~42 REITs/property trusts, all
    # required to distribute ≥90% of taxable income.
    "A17U",  # Ascendas REIT
    "C38U",  # CapitaLand Integrated Commercial Trust
    "M44U",  # Mapletree Logistics Trust
    "N2IU",  # Mapletree Pan Asia Commercial Trust
    "ME8U",  # Mapletree Industrial Trust
    "BUOU",  # Frasers Logistics & Commercial Trust
    "J69U",  # Frasers Centrepoint Trust
    "T82U",  # Suntec REIT
    "AJBU",  # Keppel DC REIT
    "C2PU",  # Parkway Life REIT
    "AU8U",  # CapitaLand China Trust
    "HMN",   # CapitaLand Ascott Trust
    "O5RU",  # AIMS APAC REIT
    "CRPU",  # Sabana Industrial REIT
    "BTOU",  # Manulife US REIT
    "ODBU",  # United Hampshire US REIT
    "T6U",   # IREIT Global
    "TS0U",  # OUE REIT
    "CY6U",  # Lendlease Global Commercial REIT
    "AW9U",  # First REIT
    "D5IU",  # Lippo Malls Indonesia Retail Trust
    "Q5T",   # Cromwell European REIT
    "J91U",  # ESR-LOGOS REIT
    "Q5T",   # Cromwell European
    "P40U",  # Starhill Global REIT
    "JYEU",  # Lendlease Global REIT (alt)
    "D8DU",  # Daiwa House Logistics Trust
    "OVQ",   # Sasseur REIT
    "A68U",  # Sasseur REIT (alternative listing)
    "RW0U",  # Mapletree Pan Asia (alt code)
    "NS8U",  # HPH Trust USD
    "N51",   # Asian Pay TV Trust
    "K71U",  # Keppel REIT
    "CJLU",  # NetLink NBN Trust
    "5DD",   # Singapore Shipping Corp
    "M1GU",  # Sasseur REIT (alt) / Mapletree Industrial dual
    "BWCU",  # Frasers Hospitality Trust
    "5BB",   # Frasers Property Trust component

    # ─── Banks / Financials ──────────────────────────────────────
    "S41",   # Hong Leong Finance
    "S35",   # PhillipCapital (?)

    # ─── Telco / Media / Tech ────────────────────────────────────
    "CC3",   # StarHub
    "B61U",  # SPH Mgt
    "Z25",   # Hour Glass (?)

    # ─── Engineering / Industrials / Maritime ────────────────────
    "F03",   # Food Empire Holdings
    "BTM",   # Boustead Singapore
    "F99",   # Fraser & Neave
    "5G2",   # Frencken Group
    "S20",   # Sembcorp Marine (now Seatrium)
    "P15",   # Pan-United Corp
    "5OC",   # Olam Group (VC2)
    "VC2",   # Olam Group
    "M01",   # Metro Holdings
    "BBP",   # AEM Holdings (Catalist)
    "5UF",   # SBS Transit
    "S59",   # SIA Engineering Co
    "S08",   # Singapore Post
    "B58",   # Bukit Sembawang Estates
    "5PD",   # Hotel Properties
    "5G3",   # Kim Heng (?)
    "L02",   # Genting Singapore (alt)
    "S56",   # Sin Heng Heavy Machinery
    "AVX",   # AvJennings (AUS via SGX)
    "AVM",   # Aspial Lifestyle

    # ─── Consumer / Retail / Food & Beverage ─────────────────────
    "OV8",   # Sheng Siong
    "F25",   # Far East Orchard
    "F17",   # Guocoland
    "F86",   # Frasers Property
    "D11",   # Riverstone Holdings
    "5ML",   # China Sunsine Chemical
    "5OI",   # Silverlake Axis
    "G92",   # China Yuchai
    "C76",   # China Aviation Oil
    "BAI",   # Mooreast (?)
    "TWO",   # OUE Ltd (LJ3?)
    "U13",   # United Engineers
    "M14",   # AsiaPhos (?)
    "5UX",   # Oxley Holdings
    "5GZ",   # GSS Energy
    "OYY",   # Mooreast (alt)
    "5G1",   # 800 Super (?)
    "A75",   # Asia Power (?)

    # ─── Real estate developers (non-REIT) ───────────────────────
    "Z59",   # Yongnam Holdings
    "BVA",   # Hiap Hoe
    "AWX",   # Hong Fok Corp (?)
    "5RA",   # Ho Bee Land
    "H13",   # Ho Bee Land (alt)
    "RE4",   # Wing Tai Holdings
    "TCU",   # Wee Hur Holdings (?)
    "K3K",   # Kingsmen Creatives
    "M01",   # Metro Holdings (dup but ok)

    # ─── Transport / Logistics ───────────────────────────────────
    "S08",   # Singapore Post
    "5UF",   # SBS Transit
    "S59",   # SIA Engineering
    "C52",   # ComfortDelGro (also STI)

    # ─── Healthcare ──────────────────────────────────────────────
    "Y35",   # Q&M Dental
    "1F0",   # Health Mgmt Intl (?)
    "K6S",   # Singapore Medical Group (?)
    "OMK",   # OUE Healthcare (?)

    # ─── ETFs (high-yield, broad market, bonds) ──────────────────
    "ES3",   # SPDR STI ETF
    "G3B",   # Nikko AM STI ETF
    "QL3",   # iShares USD Asia HY Bond ETF
    "A35",   # ABF Singapore Bond Index Fund
    "CLR",   # Lion-Phillip S-REIT ETF
    "O5T",   # Phillip SGX APAC Dividend Leaders REIT ETF
    "CFA",   # Nikko AM SGD Investment Grade Corp Bond ETF
    "BWCU",  # CSOP iEdge S-REIT Leaders ETF (?)
    "SRT",   # NikkoAM-StraitsTrading Asia ex-Japan REIT ETF
    "P5P",   # iEdge S-REIT Leaders Index ETF (?)
]

# Deduplicate while preserving order
SGX_DIVIDEND_TICKERS = list(dict.fromkeys(SGX_DIVIDEND_TICKERS))

# ─────────────────────────────────────────────────────────────────────
# Sector classification (overrides yfinance's classification)
# ─────────────────────────────────────────────────────────────────────
SECTOR_MAP: Dict[str, str] = {
    # Banks
    "D05": "Banks", "O39": "Banks", "U11": "Banks", "S41": "Banks",
    # Telco
    "Z74": "Telco", "CC3": "Telco",
    # Utilities / Infra
    "AJBU": "Utilities", "CJLU": "Utilities",
    # REITs — all SGX REIT codes end in U
    "A17U": "REITs", "C38U": "REITs", "M44U": "REITs", "N2IU": "REITs",
    "ME8U": "REITs", "BUOU": "REITs", "J69U": "REITs", "T82U": "REITs",
    "C2PU": "REITs", "AU8U": "REITs", "HMN": "REITs", "O5RU": "REITs",
    "CRPU": "REITs", "BTOU": "REITs", "ODBU": "REITs", "T6U": "REITs",
    "TS0U": "REITs", "CY6U": "REITs", "AW9U": "REITs", "D5IU": "REITs",
    "Q5T": "REITs", "J91U": "REITs", "P40U": "REITs", "JYEU": "REITs",
    "D8DU": "REITs", "OVQ": "REITs", "A68U": "REITs", "RW0U": "REITs",
    "NS8U": "Business Trusts", "N51": "Business Trusts", "K71U": "REITs",
    "M1GU": "REITs", "BWCU": "REITs", "5BB": "REITs",
    # Business Trusts
    "U96": "Business Trusts", "S58": "Business Trusts",
    # Industrials
    "S63": "Industrials", "BN4": "Industrials", "BS6": "Industrials",
    "S51": "Industrials", "BTM": "Industrials", "5G2": "Industrials",
    "S20": "Industrials", "P15": "Industrials", "V03": "Industrials",
    "BBP": "Industrials", "S59": "Industrials", "S56": "Industrials",
    # Consumer
    "Y92": "Consumer", "C07": "Consumer", "F34": "Consumer",
    "D01": "Consumer", "OV8": "Consumer", "F99": "Consumer",
    "5ML": "Consumer", "5OI": "Consumer", "G92": "Consumer",
    "C76": "Consumer", "VC2": "Consumer", "5OC": "Consumer",
    # Real Estate (non-REIT developers)
    "9CI": "Industrials", "C09": "Industrials", "U14": "Industrials",
    "F86": "Industrials", "B58": "Industrials", "5PD": "Industrials",
    "F17": "Industrials", "F25": "Industrials", "5UX": "Industrials",
    "5RA": "Industrials", "H13": "Industrials", "RE4": "Industrials",
    # Transport / Logistics
    "C52": "Industrials", "C6L": "Industrials", "S08": "Industrials",
    "5UF": "Industrials",
    # Holding / Conglomerates / Hospitality / Gaming
    "J36": "Industrials", "H78": "Industrials", "G13": "Consumer",
    # Healthcare
    "Y35": "Consumer",
    # Financial markets
    "S68": "Industrials",
    # ETFs
    "ES3": "Other", "G3B": "Other", "QL3": "Other", "A35": "Other",
    "CLR": "Other", "O5T": "Other", "CFA": "Other", "SRT": "Other",
    "P5P": "Other",
}


def classify_sector(ticker: str, yf_sector: str | None = None) -> str:
    """Return our internal sector label for a ticker.

    Order of preference:
      1) Explicit SECTOR_MAP entry.
      2) SGX REIT code convention (ends with 'U' and has 3-5 chars).
      3) yfinance sector mapping.
      4) "Other".
    """
    if ticker in SECTOR_MAP:
        return SECTOR_MAP[ticker]
    # SGX convention: REIT codes typically end with 'U' (one or two characters)
    if 3 <= len(ticker) <= 5 and ticker.endswith("U") and not ticker.endswith("MU"):
        return "REITs"
    if yf_sector:
        return _yf_sector_to_label(yf_sector)
    return "Other"


def _yf_sector_to_label(yf_sector: str) -> str:
    """Map yfinance's GICS-flavoured sector strings to our internal labels."""
    s = yf_sector.strip().lower()
    if "real estate" in s:
        # Most SGX-listed real-estate names are developers (Industrials family),
        # not REITs. REITs are detected separately by the ticker-ends-in-U rule
        # in classify_sector(), which runs first.
        return "Industrials"
    if "financial" in s:
        return "Banks"
    if "communication" in s or "telecom" in s:
        return "Telco"
    if "util" in s:
        return "Utilities"
    if "industrial" in s:
        return "Industrials"
    if "consumer" in s or "staple" in s:
        return "Consumer"
    if "energy" in s:
        return "Industrials"
    if "material" in s:
        return "Industrials"
    if "health" in s:
        return "Consumer"
    if "tech" in s:
        return "Industrials"
    return "Other"


# Default SGX lot size is 100 shares. Exceptions can be added here.
_LOT_OVERRIDES: Dict[str, int] = {}


def lot_size_for(ticker: str) -> int:
    return _LOT_OVERRIDES.get(ticker, 100)
