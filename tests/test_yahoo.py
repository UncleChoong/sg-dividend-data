from pathlib import Path
import pytest
from sg_dividend_data.sources.yahoo import parse_quote_html, YahooQuote

FIXTURE = Path(__file__).parent / "fixtures" / "yahoo_d05.html"


def test_parse_d05():
    html = FIXTURE.read_text(encoding="utf-8")
    q = parse_quote_html(html)
    assert isinstance(q, YahooQuote)
    assert q.price > 0
    assert q.market_cap is None or q.market_cap > 1e9
    assert q.ttm_yield_pct is None or 0 < q.ttm_yield_pct < 25


def test_parse_handles_missing_yield():
    html = "<html><body>no data here</body></html>"
    with pytest.raises(ValueError):
        parse_quote_html(html)
