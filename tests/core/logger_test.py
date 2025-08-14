import unittest
import json
import logging
import datetime as dt
from unittest.mock import Mock, patch
from io import StringIO

from backend.core.logger import MyJSONFormatter, NonErrorFilter


class TestMyJSONFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = MyJSONFormatter()
        self.logger = logging.getLogger('test')
        
    def create_log_record(self, msg="test message", level=logging.INFO, **kwargs):
        """Helper to create log records"""
        record = logging.LogRecord(
            name='test_logger',
            level=level,
            pathname='/test/path.py',
            lineno=42,
            msg=msg,
            args=(),
            exc_info=None
        )
        for k, v in kwargs.items():
            setattr(record, k, v)
        return record
    
    def test_format_basic_message(self):
        """Test basic message formatting"""
        record = self.create_log_record("Hello world")
        result = self.formatter.format(record)
        data = json.loads(result)
        
        self.assertEqual(data["message"], "Hello world")
        self.assertIn("timestamp", data)
        # Check timestamp format
        dt.datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
    
    def test_format_with_custom_fmt_keys(self):
        """Test formatting with custom fmt_keys mapping"""
        formatter = MyJSONFormatter(fmt_keys={"level": "levelname", "file": "filename"})
        record = self.create_log_record("Test message")
        result = formatter.format(record)
        data = json.loads(result)
        
        self.assertEqual(data["level"], "INFO")
        self.assertIn("file", data)
        self.assertIn("message", data)
        self.assertIn("timestamp", data)
    
    def test_format_with_exception_info(self):
        """Test formatting with exception information"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
        record = self.create_log_record("Error occurred", exc_info=exc_info)
        result = self.formatter.format(record)
        data = json.loads(result)
        
        self.assertIn("exc_info", data)
        self.assertIn("ValueError", data["exc_info"])
        self.assertIn("Test exception", data["exc_info"])
    
    def test_format_with_stack_info(self):
        """Test formatting with stack information"""
        import traceback
        stack_info = ''.join(traceback.format_stack())
        record = self.create_log_record("Stack test", stack_info=stack_info)
        result = self.formatter.format(record)
        data = json.loads(result)
        
        self.assertIn("stack_info", data)
        self.assertTrue(len(data["stack_info"]) > 0)
    
    def test_format_with_extra_fields(self):
        """Test formatting with extra fields not in builtin attrs"""
        record = self.create_log_record("Test message")
        record.user_id = "12345"
        record.request_id = "req_abc123"
        
        result = self.formatter.format(record)
        data = json.loads(result)
        
        self.assertEqual(data["user_id"], "12345")
        self.assertEqual(data["request_id"], "req_abc123")
    
    def test_format_excludes_builtin_attrs(self):
        """Test that builtin log record attributes are not included unless mapped"""
        record = self.create_log_record("Test message")
        result = self.formatter.format(record)
        data = json.loads(result)
        
        # These should not be in output unless explicitly mapped
        builtin_attrs = ["args", "levelno", "lineno", "pathname", "funcName"]
        for attr in builtin_attrs:
            self.assertNotIn(attr, data)
    
    def test_fmt_keys_precedence(self):
        """Test that fmt_keys mapping takes precedence"""
        formatter = MyJSONFormatter(fmt_keys={"msg_text": "message"})
        record = self.create_log_record("Test message")
        result = formatter.format(record)
        data = json.loads(result)
        
        # The mapped field should exist, original "message" should be consumed by mapping
        self.assertEqual(data["msg_text"], "Test message")
        self.assertNotIn("message", data)  # Should be consumed by the mapping
    
    def test_json_serializable_output(self):
        """Test that output is valid JSON"""
        record = self.create_log_record("Test message")
        record.custom_field = {"nested": "value"}
        record.number_field = 42
        
        result = self.formatter.format(record)
        # Should not raise exception
        data = json.loads(result)
        self.assertIsInstance(data, dict)
    
    @patch('datetime.datetime')
    def test_timestamp_format(self, mock_datetime):
        """Test timestamp formatting"""
        # Mock datetime to return predictable value
        mock_dt = Mock()
        mock_dt.isoformat.return_value = "2024-01-01T12:00:00+00:00"
        mock_datetime.fromtimestamp.return_value = mock_dt
        
        record = self.create_log_record("Test message")
        record.created = 1704110400.0  # 2024-01-01 12:00:00 UTC
        
        result = self.formatter.format(record)
        data = json.loads(result)
        
        mock_datetime.fromtimestamp.assert_called_once_with(
            1704110400.0, tz=dt.timezone.utc
        )
        self.assertEqual(data["timestamp"], "2024-01-01T12:00:00+00:00")


class TestNonErrorFilter(unittest.TestCase):
    def setUp(self):
        self.filter = NonErrorFilter()
    
    def create_log_record(self, level=logging.INFO):
        """Helper to create log records with specific levels"""
        return logging.LogRecord(
            name='test_logger',
            level=level,
            pathname='/test/path.py',
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None
        )
    
    def test_filter_debug_level(self):
        """Test DEBUG level passes filter"""
        record = self.create_log_record(logging.DEBUG)
        self.assertTrue(self.filter.filter(record))
    
    def test_filter_info_level(self):
        """Test INFO level passes filter"""
        record = self.create_log_record(logging.INFO)
        self.assertTrue(self.filter.filter(record))
    
    def test_filter_warning_level(self):
        """Test WARNING level is blocked"""
        record = self.create_log_record(logging.WARNING)
        self.assertFalse(self.filter.filter(record))
    
    def test_filter_error_level(self):
        """Test ERROR level is blocked"""
        record = self.create_log_record(logging.ERROR)
        self.assertFalse(self.filter.filter(record))
    
    def test_filter_critical_level(self):
        """Test CRITICAL level is blocked"""
        record = self.create_log_record(logging.CRITICAL)
        self.assertFalse(self.filter.filter(record))
    
    def test_filter_custom_level(self):
        """Test custom levels follow the same rule"""
        # Custom level between INFO and WARNING
        custom_level = logging.INFO + 5
        record = self.create_log_record(custom_level)
        self.assertFalse(self.filter.filter(record))
        
        # Custom level below INFO
        custom_level = logging.INFO - 5
        record = self.create_log_record(custom_level)
        self.assertTrue(self.filter.filter(record))


class TestIntegration(unittest.TestCase):
    """Integration tests for formatter and filter together"""
    
    def test_logger_with_formatter_and_filter(self):
        """Test logger setup with both formatter and filter"""
        # Setup logger
        logger = logging.getLogger('integration_test')
        logger.setLevel(logging.DEBUG)
        
        # Setup handler with formatter and filter
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(MyJSONFormatter(fmt_keys={"level": "levelname"}))
        handler.addFilter(NonErrorFilter())
        
        logger.addHandler(handler)
        
        # Test various log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")  # Should be filtered out
        logger.error("Error message")      # Should be filtered out
        
        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        # Should only have 2 lines (debug and info)
        self.assertEqual(len(lines), 2)
        
        # Check content
        debug_data = json.loads(lines[0])
        info_data = json.loads(lines[1])
        
        self.assertEqual(debug_data["message"], "Debug message")
        self.assertEqual(debug_data["level"], "DEBUG")
        self.assertEqual(info_data["message"], "Info message")
        self.assertEqual(info_data["level"], "INFO")
        
        # Cleanup
        logger.removeHandler(handler)


if __name__ == '__main__':
    unittest.main()