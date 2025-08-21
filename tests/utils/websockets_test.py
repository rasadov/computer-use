from unittest.mock import AsyncMock, Mock, patch

import orjson
import pytest
from fastapi import WebSocket

from backend.utils.websocket import send_websocket_message


class TestSendWebsocketMessage:

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket object"""
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        with patch('backend.utils.websocket.logger') as mock_logger:
            yield mock_logger

    @pytest.mark.asyncio
    async def test_successful_message_send(self, mock_websocket, mock_logger):
        """Test successful message sending with valid inputs"""
        # Arrange
        task_status = "in_progress"
        message_type = "status_update"
        content = {"progress": 50, "details": "Processing data"}

        expected_message = orjson.dumps({
            "type": message_type,
            "task_status": task_status,
            "content": content
        }).decode("utf-8")

        # Act
        await send_websocket_message(mock_websocket, task_status, message_type, content)

        # Assert
        mock_websocket.send_text.assert_called_once_with(expected_message)
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_websocket_handling(self, mock_logger):
        """Test behavior when websocket is None"""
        # Act
        await send_websocket_message(None, "completed", "result", {"data": "test"})

        # Assert
        mock_logger.warning.assert_called_once_with("No websocket connection")

    @pytest.mark.asyncio
    async def test_websocket_send_exception(self, mock_websocket, mock_logger):
        """Test exception handling during websocket send"""
        # Arrange
        mock_websocket.send_text.side_effect = Exception("Connection closed")

        # Act
        await send_websocket_message(mock_websocket, "error", "notification", "test")

        # Assert
        mock_logger.error.assert_called_once_with("Error sending websocket message: Connection closed")

    @pytest.mark.asyncio
    async def test_various_content_types(self, mock_websocket):
        """Test function with different content types"""
        test_cases = [
            "string content",
            {"key": "value"},
            [1, 2, 3],
            42,
            3.14,
            True,
            None
        ]

        for content in test_cases:
            mock_websocket.reset_mock()

            await send_websocket_message(mock_websocket, "test", "data", content)

            # Verify the message was sent
            assert mock_websocket.send_text.call_count == 1

            # Verify the content can be serialized and deserialized
            sent_args = mock_websocket.send_text.call_args[0][0]
            parsed_message = orjson.loads(sent_args)
            assert parsed_message["content"] == content

    @pytest.mark.asyncio
    async def test_special_characters_in_strings(self, mock_websocket):
        """Test function with special characters and unicode"""
        special_contents = [
            "Message with émojis: 🚀 🎉",
            "Quotes: \"Hello\" and 'World'",
            "Newlines:\nLine 1\nLine 2",
            "Unicode: こんにちは 世界",
            "Special chars: @#$%^&*()[]{}|\\:;\"'<>,.?/~`"
        ]

        for content in special_contents:
            mock_websocket.reset_mock()

            await send_websocket_message(mock_websocket, "test", "message", content)

            # Verify message was sent and can be parsed back
            sent_args = mock_websocket.send_text.call_args[0][0]
            parsed_message = orjson.loads(sent_args)
            assert parsed_message["content"] == content

    @pytest.mark.asyncio
    async def test_message_structure(self, mock_websocket):
        """Test that the message structure is correct"""
        # Arrange
        task_status = "completed"
        message_type = "result"
        content = {"result": "success", "data": [1, 2, 3]}

        # Act
        await send_websocket_message(mock_websocket, task_status, message_type, content)

        # Assert
        sent_message = mock_websocket.send_text.call_args[0][0]
        parsed = orjson.loads(sent_message)

        assert parsed["type"] == message_type
        assert parsed["task_status"] == task_status
        assert parsed["content"] == content
        assert len(parsed.keys()) == 3  # Ensure no extra fields

    @pytest.mark.asyncio
    async def test_empty_strings(self, mock_websocket):
        """Test function with empty string parameters"""
        await send_websocket_message(mock_websocket, "", "", "")

        sent_message = mock_websocket.send_text.call_args[0][0]
        parsed = orjson.loads(sent_message)

        assert parsed["type"] == ""
        assert parsed["task_status"] == ""
        assert parsed["content"] == ""

    @pytest.mark.asyncio
    async def test_large_content(self, mock_websocket):
        """Test function with large content"""
        # Create a large content object
        large_content = {"data": "x" * 10000, "numbers": list(range(1000))}

        await send_websocket_message(mock_websocket, "processing", "bulk_data", large_content)

        # Verify it was sent successfully
        mock_websocket.send_text.assert_called_once()
        sent_message = mock_websocket.send_text.call_args[0][0]
        parsed = orjson.loads(sent_message)
        assert parsed["content"] == large_content

    @pytest.mark.asyncio
    async def test_orjson_serialization_error(self, mock_websocket, mock_logger):
        """Test handling of content that cannot be serialized"""
        # Create content that orjson cannot serialize (e.g., a function)
        def unserializable_func():
            pass

        with patch('orjson.dumps') as mock_dumps:
            mock_dumps.side_effect = TypeError("Object of type function is not JSON serializable")

            await send_websocket_message(mock_websocket, "error", "data", unserializable_func)

            mock_logger.error.assert_called_once()
            assert "Error sending websocket message:" in mock_logger.error.call_args[0][0]
