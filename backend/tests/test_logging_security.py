import json
import logging

from app.core.logging import JsonFormatter, redact_secrets


def test_redacts_telegram_tokens_and_url_passwords():
    raw = "POST https://api.telegram.org/bot123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_123/getMe rtsp://user:password@host/live"
    redacted = redact_secrets(raw)
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in redacted
    assert "password" not in redacted
    assert redacted == "POST https://api.telegram.org/bot***/getMe rtsp://user:***@host/live"


def test_formatter_redacts_message_and_extra():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "bot123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_123", (), None)
    record.url = "rtsp://u:secret@camera/live"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "bot***"
    assert payload["extra"]["url"] == "rtsp://u:***@camera/live"


def test_redacts_bearer_and_jwt_tokens():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"
    assert redact_secrets(f"Authorization: Bearer {jwt}") == "Authorization: Bearer ***"
