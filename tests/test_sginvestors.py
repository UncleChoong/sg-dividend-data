from pathlib import Path
from sg_dividend_data.sources.sginvestors import parse_div_history, fetch_div_history

FIXTURE = Path(__file__).parent / "fixtures" / "sginvestors_d05.html"


def test_parse_d05_returns_5y_floats():
    html = FIXTURE.read_text(encoding="utf-8")
    hist = parse_div_history(html)
    assert len(hist) == 5
    for entry in hist:
        assert entry is None or isinstance(entry, float)
    non_null = [e for e in hist if e is not None]
    assert non_null, "expected at least one non-null dividend"
    assert max(non_null) > 0.5


def test_parse_handles_empty_table():
    hist = parse_div_history("<html><body><table></table></body></html>")
    assert hist == [None, None, None, None, None]
