import contextvars
import json
import logging
import re
import sys
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_BOT_TOKEN = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")
_URL_PASSWORD = re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:/\s]+:)([^@\s/]+)(@)")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~-]+")
_JWT = re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def redact_secrets(value: str) -> str:
    value = _BOT_TOKEN.sub("***", value)
    value = _BEARER.sub(r"\1***", value)
    value = _JWT.sub("***", value)
    return _URL_PASSWORD.sub(r"\1***\3", value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        extra = {k: v for k, v in record.__dict__.items() if k not in _RESERVED and not k.startswith("_")}
        if extra:
            payload["extra"] = {k: _safe(v) for k, v in extra.items()}
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return redact_secrets(json.dumps(payload, ensure_ascii=False, default=str))


def _safe(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    # These clients otherwise log full Telegram URLs, which contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
