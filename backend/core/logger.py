import datetime as dt
import logging
import os
import sys
from typing_extensions import override

import orjson
from concurrent_log_handler import ConcurrentRotatingFileHandler


LOG_RECORD_BUILTIN_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info", "thread",
    "threadName", "taskName",
}


class MyJSONFormatter(logging.Formatter):
    def __init__(self, *, fmt_keys: dict[str, str] | None = None):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    @override
    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return orjson.dumps(message, default=str).decode()

    def _prepare_log_dict(self, record: logging.LogRecord):
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(record.created, tz=dt.timezone.utc).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: always_fields.pop(val, getattr(record, val))
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)
        # Only include specific custom attributes
        custom_attrs = getattr(record, "custom_attrs", {})
        message.update(custom_attrs)
        return message


class NonErrorFilter(logging.Filter):
    @override
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= logging.INFO


def _ensure_logs_dir(path: str) -> None:
    try:
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    except OSError as e:
        logging.getLogger().warning(f"Failed to create log directory: {e}")


def _build_console_handler(level: int) -> logging.StreamHandler:
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(MyJSONFormatter(fmt_keys={"level": "levelname", "logger": "name"}))
    return handler


def _build_file_handler(path: str, level: int) -> logging.Handler:
    _ensure_logs_dir(path)
    # Use ConcurrentRotatingFileHandler for thread-safe async writes
    fh = ConcurrentRotatingFileHandler(path, maxBytes=10_000_000, backupCount=5)
    fh.setLevel(level)
    fh.setFormatter(MyJSONFormatter(fmt_keys={"level": "levelname", "logger": "name"}))
    return fh


def setup_logging(*, level: int | None = None, log_file: str | None = None) -> None:
    if level is None:
        debug_env = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "on"}
        level = logging.DEBUG if debug_env else logging.INFO

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(level)
    root.addHandler(_build_console_handler(level))
    if log_file:
        try:
            root.addHandler(_build_file_handler(log_file, level))
        except OSError as e:
            logging.getLogger().warning(f"Failed to setup file handler: {e}")

    for name in ("backend", "uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        lg.setLevel(level)
