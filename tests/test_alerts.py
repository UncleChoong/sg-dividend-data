from unittest.mock import patch, MagicMock
from sg_dividend_data.alerts import telegram_alert

def test_telegram_alert_skips_when_no_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram_alert("hello") is False

def test_telegram_alert_posts_when_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    with patch("sg_dividend_data.alerts.requests.post") as p:
        p.return_value = MagicMock(status_code=200)
        ok = telegram_alert("hello")
    assert ok is True
    p.assert_called_once()
    url = p.call_args[0][0]
    assert "abc" in url
    assert p.call_args[1]["data"]["chat_id"] == "123"
