"""Curated descriptions, market caps, and industry classifications per ticker.

These are hand-authored — not scraped — because they shape the UX of the
consuming app and need to be Singapore-context-aware.

For tickers *not* in the curated map, the writer pulls descriptive metadata
(name, description, industry) from the yfinance info dict instead, so the
consuming app always shows something more meaningful than the bare ticker
code. Curated entries still win when present.
"""
from __future__ import annotations
from typing import Dict, TypedDict, Optional


class Enrichment(TypedDict):
    name: str
    description: str
    market_cap_sgd: Optional[float]
    industry: str


ENRICHMENT: Dict[str, Enrichment] = {
    "D05":  {"name": "DBS Group", "description": "Singapore's largest bank by assets, with operations across Asia. A consistent dividend payer with strong CET-1 capital ratios.", "market_cap_sgd": 175_000_000_000, "industry": "Banks"},
    "O39":  {"name": "OCBC", "description": "Second-largest Singapore bank, with strong presence in Greater China and Southeast Asia. Steady semi-annual dividend record.", "market_cap_sgd": 105_000_000_000, "industry": "Banks"},
    "U11":  {"name": "United Overseas Bank", "description": "Third local bank, with major Southeast Asia regional franchise. Reliable dividend, conservative balance sheet.", "market_cap_sgd": 63_000_000_000, "industry": "Banks"},
    "Z74":  {"name": "Singtel", "description": "Largest Singapore telco, with regional stakes in Optus (Australia), Bharti Airtel (India), and others. Yield-focused after asset rationalisation.", "market_cap_sgd": 74_000_000_000, "industry": "Telco"},
    "CC3":  {"name": "StarHub", "description": "Singapore's second-largest telecom. Smaller scale than Singtel; dividend cut in recent years as fixed-line revenue declined.", "market_cap_sgd": 1_800_000_000, "industry": "Telco"},
    "AJBU": {"name": "Keppel DC REIT", "description": "Singapore's pure-play data centre REIT, with assets across Asia-Pacific and Europe. Beneficiary of AI/cloud capex.", "market_cap_sgd": 4_500_000_000, "industry": "Utilities"},
    "CJLU": {"name": "NetLink NBN Trust", "description": "Owner of Singapore's nationwide fibre broadband network. Regulated returns, defensive yield play.", "market_cap_sgd": 3_800_000_000, "industry": "Utilities"},
    "A17U": {"name": "Ascendas REIT", "description": "Singapore's largest industrial REIT, with logistics, business space, and data centre assets across SG, Australia, US, Europe.", "market_cap_sgd": 11_500_000_000, "industry": "REITs"},
    "C38U": {"name": "CapitaLand Integrated Commercial Trust", "description": "Largest Singapore retail+office REIT. Anchor assets include Plaza Singapura, Funan, Asia Square. Defensive blue-chip REIT.", "market_cap_sgd": 15_000_000_000, "industry": "REITs"},
    "M44U": {"name": "Mapletree Logistics Trust", "description": "Asia-Pacific logistics REIT with 180+ properties across 9 countries. Dividend pressure from rising rates.", "market_cap_sgd": 6_800_000_000, "industry": "REITs"},
    "N2IU": {"name": "Mapletree Pan Asia Commercial Trust", "description": "Office-retail REIT covering SG, HK, China, Japan, Korea. Higher leverage and FX exposure than peers.", "market_cap_sgd": 6_700_000_000, "industry": "REITs"},
    "ME8U": {"name": "Mapletree Industrial Trust", "description": "Industrial + data centre REIT. ~55% US data centres, ~40% Singapore industrial. Active capital recycling.", "market_cap_sgd": 6_400_000_000, "industry": "REITs"},
    "T82U": {"name": "Suntec REIT", "description": "Office + retail REIT centred on Suntec City Mall and One Raffles Quay. Higher debt cost sensitivity.", "market_cap_sgd": 4_200_000_000, "industry": "REITs"},
    "J69U": {"name": "Frasers Centrepoint Trust", "description": "Suburban Singapore retail REIT - Causeway Point, Northpoint City, Tampines 1. Defensive consumer staples mix.", "market_cap_sgd": 4_100_000_000, "industry": "REITs"},
    "BUOU": {"name": "Frasers Logistics & Commercial Trust", "description": "Australia/Europe-focused logistics + commercial REIT. Higher growth profile but FX-exposed.", "market_cap_sgd": 3_600_000_000, "industry": "REITs"},
    "C2PU": {"name": "Parkway Life REIT", "description": "Asia's largest listed healthcare REIT - Singapore + Japan hospitals/nursing homes. CPI-linked rentals.", "market_cap_sgd": 2_700_000_000, "industry": "REITs"},
    "AU8U": {"name": "CapitaLand China Trust", "description": "China retail + business park REIT. Subject to China property/consumer sentiment headwinds.", "market_cap_sgd": 1_300_000_000, "industry": "REITs"},
    "HMN":  {"name": "CapitaLand Ascott Trust", "description": "Asia's largest lodging trust — serviced residences and hotels across 40+ cities. Recovery beneficiary post-pandemic.", "market_cap_sgd": 3_500_000_000, "industry": "REITs"},
    "K71U": {"name": "Keppel REIT", "description": "Prime office REIT with assets in Singapore, Australia, South Korea, Japan. Anchor exposure to Singapore CBD Grade-A.", "market_cap_sgd": 3_500_000_000, "industry": "REITs"},
    "O5RU": {"name": "AIMS APAC REIT", "description": "Industrial + logistics REIT, ~25 properties in Singapore + Australia. Higher yield, smaller scale.", "market_cap_sgd": 1_000_000_000, "industry": "REITs"},
    "J91U": {"name": "ESR-LOGOS REIT", "description": "Industrial REIT, formerly ESR-REIT, merged with ARA LOGOS. Diversified industrial + logistics across Asia-Pacific.", "market_cap_sgd": 2_300_000_000, "industry": "REITs"},
    "P40U": {"name": "Starhill Global REIT", "description": "Retail-focused REIT — Ngee Ann City + Wisma Atria on Orchard Road, plus assets in Australia, China, Japan.", "market_cap_sgd": 1_000_000_000, "industry": "REITs"},
    "CY6U": {"name": "Lendlease Global Commercial REIT", "description": "Retail + office REIT — 313@somerset, Jem in Singapore + Sky Complex in Milan. Smaller-cap REIT.", "market_cap_sgd": 1_200_000_000, "industry": "REITs"},
    "TS0U": {"name": "OUE REIT", "description": "Combined commercial + hospitality REIT — OUE Bayfront, Mandarin Orchard, Crowne Plaza Changi. Tourism-linked.", "market_cap_sgd": 1_800_000_000, "industry": "REITs"},
    "U96":  {"name": "Sembcorp Industries", "description": "Energy + urban infrastructure conglomerate, transitioning to renewables. Improving dividend trajectory.", "market_cap_sgd": 11_000_000_000, "industry": "Industrials"},
    "S58":  {"name": "SATS", "description": "Airline ground handling + in-flight catering. Recovering post-COVID with WFS acquisition.", "market_cap_sgd": 3_900_000_000, "industry": "Industrials"},
    "S63":  {"name": "ST Engineering", "description": "Defence, aerospace, smart-cities conglomerate. Stable order book, reliable dividend grower.", "market_cap_sgd": 13_400_000_000, "industry": "Industrials"},
    "Y92":  {"name": "Thai Beverage", "description": "Thailand's largest beverage producer (Chang Beer). Stable cash flows, listed on SGX.", "market_cap_sgd": 11_500_000_000, "industry": "Consumer"},
    "C07":  {"name": "Jardine Cycle & Carriage", "description": "Astra International (Indonesia) majority owner. Auto, financial services, agribusiness exposure.", "market_cap_sgd": 7_000_000_000, "industry": "Consumer"},
    "BN4":  {"name": "Keppel", "description": "Asset-light infrastructure, real estate, asset management. Spun off offshore marine in 2024.", "market_cap_sgd": 12_500_000_000, "industry": "Industrials"},
    "F34":  {"name": "Wilmar International", "description": "Asia's leading agribusiness — edible oils, sugar, grains. Commodity-cycle exposed.", "market_cap_sgd": 18_000_000_000, "industry": "Consumer"},
    "S68":  {"name": "Singapore Exchange", "description": "Operator of SGX itself. Diversified across cash equities, derivatives, FX. Monopoly profile.", "market_cap_sgd": 13_500_000_000, "industry": "Industrials"},
    "9CI":  {"name": "CapitaLand Investment", "description": "Real estate asset manager — ~S$130bn AUM across REITs, private funds, lodging. STI component.", "market_cap_sgd": 13_500_000_000, "industry": "Industrials"},
    "BS6":  {"name": "Yangzijiang Shipbuilding", "description": "China's largest private shipbuilder. STI component, beneficiary of LNG/container newbuild cycle.", "market_cap_sgd": 11_000_000_000, "industry": "Industrials"},
    "V03":  {"name": "Venture Corp", "description": "Electronics manufacturing services — medical, networking, life sciences customers. Long dividend record.", "market_cap_sgd": 4_000_000_000, "industry": "Industrials"},
    "G13":  {"name": "Genting Singapore", "description": "Operator of Resorts World Sentosa — integrated casino + theme park. Tourism-linked dividend.", "market_cap_sgd": 11_000_000_000, "industry": "Consumer"},
    "C52":  {"name": "ComfortDelGro", "description": "Land transport — taxi, bus, rail across SG/UK/Australia/China. Defensive but low-growth dividend.", "market_cap_sgd": 3_200_000_000, "industry": "Industrials"},
    "C09":  {"name": "City Developments", "description": "Singapore's largest property developer + hospitality (Millennium & Copthorne). Long-cycle dividend.", "market_cap_sgd": 5_000_000_000, "industry": "Industrials"},
    "U14":  {"name": "UOL Group", "description": "Property developer + hospitality (Pan Pacific Hotels). Conservative, family-controlled.", "market_cap_sgd": 5_000_000_000, "industry": "Industrials"},
    "D01":  {"name": "DFI Retail Group", "description": "Pan-Asian retailer — Cold Storage, Giant, Guardian, 7-Eleven HK. Restructuring under Jardine.", "market_cap_sgd": 4_700_000_000, "industry": "Consumer"},
    "S51":  {"name": "Seatrium", "description": "Offshore + marine engineering — formed from Sembcorp Marine + Keppel O&M merger. Energy transition focus.", "market_cap_sgd": 9_000_000_000, "industry": "Industrials"},
    "C6L":  {"name": "Singapore Airlines", "description": "Flag-carrier airline. Variable dividend tied to travel-demand cycle, strong post-COVID recovery.", "market_cap_sgd": 19_000_000_000, "industry": "Industrials"},
    "J36":  {"name": "Jardine Matheson", "description": "Hong Kong-based pan-Asian conglomerate — retail, property, automotive, agribusiness, financial services.", "market_cap_sgd": 17_000_000_000, "industry": "Industrials"},
    "H78":  {"name": "Hongkong Land", "description": "Premium commercial property — Central, Hong Kong + Singapore developments. Steady dividend grower.", "market_cap_sgd": 13_000_000_000, "industry": "Industrials"},
    "OV8":  {"name": "Sheng Siong Group", "description": "Singapore supermarket chain — defensive consumer-staples dividend, no overseas exposure.", "market_cap_sgd": 2_600_000_000, "industry": "Consumer"},
    "F99":  {"name": "Fraser and Neave (F&N)", "description": "Beverages (100Plus, F&N) + dairies + publishing. Stable F&B cash flows.", "market_cap_sgd": 1_500_000_000, "industry": "Consumer"},
    "F86":  {"name": "Frasers Property", "description": "Diversified developer — SG/Australia/EU. Sponsor of Frasers REITs. Higher beta than UOL/City Dev.", "market_cap_sgd": 2_500_000_000, "industry": "Industrials"},
    "ES3":  {"name": "SPDR Straits Times Index ETF", "description": "Tracks the FTSE Straits Times Index — the 30 largest SGX stocks. Most widely held SG ETF.", "market_cap_sgd": 1_700_000_000, "industry": "Other"},
    "QL3":  {"name": "iShares USD Asia HY Bond ETF", "description": "Asian high-yield USD bond exposure. Higher yield, higher credit risk than government bonds.", "market_cap_sgd": 300_000_000, "industry": "Other"},
    "G3B":  {"name": "Nikko AM STI ETF", "description": "Alternative STI tracker — same underlying as ES3 but different fee/structure. Used for SRS investing.", "market_cap_sgd": 800_000_000, "industry": "Other"},
    "A35":  {"name": "ABF Singapore Bond Index Fund", "description": "Tracks an index of Singapore government + quasi-government bonds. Conservative income play.", "market_cap_sgd": 1_300_000_000, "industry": "Other"},
    "CLR":  {"name": "Lion-Phillip S-REIT ETF", "description": "Diversified Singapore REIT ETF — basket exposure to ~20 S-REITs. One-click REIT diversification.", "market_cap_sgd": 250_000_000, "industry": "Other"},
}


def _trim_summary(text: str, max_chars: int = 400) -> str:
    """Trim a yfinance longBusinessSummary to fit a card-sized description."""
    s = text.strip().replace("\n", " ").replace("  ", " ")
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars]
    # Trim back to the last sentence-ending punctuation if possible.
    for punct in (". ", "; "):
        idx = cut.rfind(punct)
        if idx > max_chars * 0.5:
            return cut[: idx + 1].strip()
    return cut.strip() + "…"


def enrich_entry(entry: dict) -> dict:
    """Mutate-in-place: add description, industry, market_cap_sgd to a UniverseEntry dict.

    Curated entries (ENRICHMENT dict) take precedence; otherwise we use the
    yfinance metadata that the snapshot carried through. Falls back to empty
    description + sector-as-industry if neither is available.
    """
    ticker = entry.get("ticker", "")
    # Always pop the temporary keys so they don't leak into output JSON.
    yf_summary = entry.pop("_yf_summary", None)
    yf_industry = entry.pop("_yf_industry", None)

    e = ENRICHMENT.get(ticker)
    if e is not None:
        entry["description"] = e["description"]
        entry["industry"] = e["industry"]
        entry["market_cap_sgd"] = e["market_cap_sgd"]
        entry["name"] = e["name"]
        return entry

    if isinstance(yf_summary, str) and yf_summary:
        entry["description"] = _trim_summary(yf_summary)
    else:
        entry["description"] = ""

    # `industry` is what the consuming app uses for filter chips & badges —
    # keep it on our coarse bucket (Banks / REITs / Industrials / …) by
    # mirroring `sector`. The fine-grained yfinance industry ("REIT — Retail"
    # etc.) is stashed in `industry_detail` for display in the stock detail UI.
    entry["industry"] = entry.get("sector", "Other")
    if isinstance(yf_industry, str) and yf_industry:
        entry["industry_detail"] = yf_industry

    # market_cap_sgd: already injected upstream by the writer, or null
    entry.setdefault("market_cap_sgd", None)
    return entry
