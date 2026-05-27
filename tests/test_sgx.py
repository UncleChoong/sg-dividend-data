from pathlib import Path
import json
from sg_dividend_data.sources.sgx import parse_corp_actions, upcoming_for

FIXTURE = Path(__file__).parent / "fixtures" / "sgx_corp_actions.json"

def test_parse_returns_list_of_events():
    data = json.loads(FIXTURE.read_text())
    events = parse_corp_actions(data)
    assert isinstance(events, list)
    if events:
        e = events[0]
        assert hasattr(e, "ticker")
        assert hasattr(e, "ex_date")
        assert hasattr(e, "amount")

def test_upcoming_filters_by_ticker():
    data = json.loads(FIXTURE.read_text())
    events = parse_corp_actions(data)
    if events:
        sample = events[0].ticker
        filtered = upcoming_for(sample, events)
        assert all(e.ticker == sample for e in filtered)
