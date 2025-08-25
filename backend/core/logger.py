import datetime as dt
import logging
import os
import sys

import orjson
from concurrent_log_handler import ConcurrentRotatingFileHandler
from typing_extensions import override

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


class StandardTextFormatter(logging.Formatter):
    """A formatter that outputs human-readable text instead of JSON."""

    def __init__(self, *, include_timestamp: bool = True, include_logger: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_logger = include_logger

    @override
    def format(self, record: logging.LogRecord) -> str:
        # Build the log message parts
        parts = []

        # Add timestamp if requested
        if self.include_timestamp:
            timestamp = dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc)
            parts.append(timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"))

        # Add level name with color/formatting
        level_str = f"[{record.levelname}]"
        parts.append(level_str)

        # Add logger name if requested
        if self.include_logger and record.name != "root":
            parts.append(f"{record.name}")

        # Add the actual message
        message = record.getMessage()

        # Combine parts with the message
        prefix = " ".join(parts)
        log_line = f"{prefix}: {message}"

        # Add exception info if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_line += "\n" + self.formatStack(record.stack_info)

        # Add custom attributes if present
        custom_attrs = getattr(record, "custom_attrs", {})
        if custom_attrs:
            attrs_str = " ".join(f"{k}={v}" for k, v in custom_attrs.items())
            log_line += f" [{attrs_str}]"

        return log_line


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
    """Build console handler with standard text formatting."""
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    # Use standard text formatter for console output
    handler.setFormatter(StandardTextFormatter(
        include_timestamp=True, include_logger=True))
    return handler


def _build_file_handler(path: str, level: int, max_bytes: int, backup_count: int) -> logging.Handler:
    """Build file handler with JSON formatting (good for log processing)."""
    _ensure_logs_dir(path)
    # Use ConcurrentRotatingFileHandler for thread-safe async writes
    # backupCount = number of old log files to keep (e.g., app.log.1, app.log.2, etc.)
    # maxBytes = maximum size of log file in bytes
    fh = ConcurrentRotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count)
    fh.setLevel(level)
    # Keep JSON format for file logging (useful for log analysis tools)
    fh.setFormatter(MyJSONFormatter(
        fmt_keys={"level": "levelname", "logger": "name"}))
    return fh


def setup_logging(
    *,
    level: int | None = None,
    log_path: str = "logs/app.log",
    max_log_files: int = 5,
        max_log_size: int = 10_000_000) -> None:

    if level is None:
        debug_env = os.getenv("DEBUG", "false").lower() in {
            "1", "true", "yes", "on"}
        level = logging.DEBUG if debug_env else logging.INFO

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(level)
    root.addHandler(_build_console_handler(level))

    if log_path:
        try:
            root.addHandler(_build_file_handler(
                log_path, level, max_log_size, max_log_files))
        except OSError as e:
            logging.getLogger().warning(f"Failed to setup file handler: {e}")

    for name in ("backend", "uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        lg.setLevel(level)
