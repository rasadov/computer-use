import unittest
import logging
import os
import sys
import orjson
import datetime as dt
import tempfile
import shutil
from unittest.mock import patch
from io import StringIO
import time

from backend.core.logger import (
    MyJSONFormatter,
    NonErrorFilter,
    _ensure_logs_dir,
    _build_console_handler,
    _build_file_handler,
    setup_logging,
)

class TestLogger(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for log files
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        # Capture console output
        self.stdout = StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout
        # Reset logging configuration
        logging.getLogger().handlers = []
        logging.getLogger().setLevel(logging.NOTSET)

    def tearDown(self):
        # Restore stdout
        sys.stdout = self.original_stdout
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Reset logging configuration
        logging.getLogger().handlers = []
        logging.getLogger().setLevel(logging.NOTSET)

    def test_my_json_formatter_basic(self):
        """Test MyJSONFormatter with a basic log record."""
        formatter = MyJSONFormatter(fmt_keys={"level": "levelname", "logger": "name"})
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = orjson.loads(output)
        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["logger"], "test")
        self.assertEqual(parsed["message"], "Test message")
        self.assertTrue("timestamp" in parsed)
        # Verify timestamp is ISO format
        dt.datetime.fromisoformat(parsed["timestamp"])

    def test_my_json_formatter_with_custom_attrs(self):
        """Test MyJSONFormatter with custom attributes."""
        formatter = MyJSONFormatter(fmt_keys={"level": "levelname", "logger": "name"})
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.custom_attrs = {"custom_attr": "custom_value"}
        output = formatter.format(record)
        parsed = orjson.loads(output)
        self.assertEqual(parsed["custom_attr"], "custom_value")
        
    def test_my_json_formatter_with_exception(self):
        """Test MyJSONFormatter with exception info."""
        formatter = MyJSONFormatter(fmt_keys={"level": "levelname", "logger": "name"})
        logger = logging.getLogger("test")
        logger.setLevel(logging.ERROR)
        try:
            raise ValueError("Test error")
        except ValueError as e:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
        output = formatter.format(record)
        parsed = orjson.loads(output)
        self.assertIn("exc_info", parsed)
        self.assertIn("ValueError: Test error", parsed["exc_info"])

    def test_non_error_filter(self):
        """Test NonErrorFilter behavior."""
        filter_ = NonErrorFilter()
        record_info = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="", args=(), exc_info=None
        )
        record_error = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0, msg="", args=(), exc_info=None
        )
        self.assertTrue(filter_.filter(record_info))
        self.assertFalse(filter_.filter(record_error))

    def test_ensure_logs_dir(self):
        """Test _ensure_logs_dir creates directories."""
        log_file = os.path.join(self.temp_dir, "logs/subdir/test.log")
        _ensure_logs_dir(log_file)
        self.assertTrue(os.path.exists(os.path.dirname(log_file)))

    @patch("os.makedirs")
    def test_ensure_logs_dir_handles_error(self, mock_makedirs):
        """Test _ensure_logs_dir handles errors gracefully."""
        mock_makedirs.side_effect = OSError("Permission denied")
        log_file = os.path.join(self.temp_dir, "logs/test.log")
        _ensure_logs_dir(log_file)  # Should not raise
        mock_makedirs.assert_called_once()

    def test_build_console_handler(self):
        """Test _build_console_handler configuration."""
        handler: logging.StreamHandler = _build_console_handler(logging.INFO)
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertEqual(handler.level, logging.INFO)
        self.assertIsInstance(handler.formatter, MyJSONFormatter)
        self.assertEqual(handler.stream, sys.stdout)

    def test_build_file_handler(self):
        """Test _build_file_handler configuration."""
        handler = _build_file_handler(self.log_file, logging.INFO)
        self.assertIsInstance(handler, logging.FileHandler)
        self.assertEqual(handler.level, logging.INFO)
        self.assertIsInstance(handler.formatter, MyJSONFormatter)
        self.assertTrue(os.path.exists(self.temp_dir))

    @patch("os.getenv")
    def test_setup_logging_console_only(self, mock_getenv):
        """Test setup_logging with console output only."""
        mock_getenv.return_value = "true"
        setup_logging(level=logging.DEBUG)
        logger = logging.getLogger()
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_with_file(self):
        """Test setup_logging with file output."""
        setup_logging(level=logging.INFO, log_file=self.log_file)
        logger = logging.getLogger()
        self.assertEqual(logger.level, logging.INFO)
        self.assertEqual(len(logger.handlers), 2)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
        self.assertIsInstance(logger.handlers[1], logging.FileHandler)
        # Verify file handler writes logs
        logger.info("Test log")
        with open(self.log_file, "r") as f:
            log_entry = orjson.loads(f.read())
            self.assertEqual(log_entry["message"], "Test log")

    def test_setup_logging_uvicorn(self):
        """Test setup_logging configures Uvicorn loggers."""
        setup_logging(level=logging.DEBUG)
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            logger = logging.getLogger(name)
            self.assertEqual(logger.level, logging.DEBUG)
            self.assertTrue(logger.propagate)
            self.assertEqual(len(logger.handlers), 0)

    def test_logging_performance(self):
        """Test logging performance with many log messages."""
        setup_logging(level=logging.INFO, log_file=self.log_file)
        logger = logging.getLogger("test")
        n_logs = 1000
        start_time = time.time()
        for i in range(n_logs):
            logger.info(f"Test message {i}")
        duration = time.time() - start_time
        logs_per_second = n_logs / duration
        print(f"Logged {n_logs} messages in {duration:.2f} seconds ({logs_per_second:.2f} logs/sec)")
        # Assert performance is reasonable (threshold depends on system)
        self.assertLess(duration, 2.0, f"Logging {n_logs} messages took too long: {duration:.2f} seconds")

if __name__ == "__main__":
    unittest.main()