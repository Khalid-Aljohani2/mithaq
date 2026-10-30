"""Structured logging with a request id (NFR-12).

Emits one JSON object per line. The AI call records carry stage, model,
latency, token counts and the validation result; they never carry the API key,
a prompt, or a request body.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar

#: Correlates every log line emitted while handling one request.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

#: Attributes the standard LogRecord always carries - everything else on a
#: record was put there by us via `extra` and belongs in the output.
_STANDARD = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "taskName",
}

#: Never emitted, whatever a caller passes.
_REDACT = frozenset({"api_key", "llm_api_key", "authorization", "x_api_key", "key", "token"})


class JsonFormatter(logging.Formatter):
    """One JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD or key.startswith("_"):
                continue
            payload[key] = "[redacted]" if key.lower() in _REDACT else value
        if record.exc_info:
            payload["exc_type"] = getattr(record.exc_info[0], "__name__", "Exception")
        return json.dumps(payload, ensure_ascii=False, default=str)


def new_request_id() -> str:
    """Allocate and install a request id for the current context."""
    rid = uuid.uuid4().hex[:16]
    request_id_var.set(rid)
    return rid


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the mithaq loggers. Idempotent."""
    logger = logging.getLogger("mithaq")
    if any(getattr(h, "_mithaq", False) for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._mithaq = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
