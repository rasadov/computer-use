import os
from unittest import mock

import pytest

from backend.services.connection_manager import RedisConnectionManager


@pytest.fixture(autouse=True)
def mock_screen_dimensions():
    with mock.patch.dict(
        os.environ, {"HEIGHT": "768", "WIDTH": "1024", "DISPLAY_NUM": "1"}
    ):
        yield

@pytest.fixture
async def connection_manager():
    """Create a real connection manager instance for testing"""
    manager = RedisConnectionManager()
    # Mock Redis to avoid actual Redis dependency
    manager.redis_client = mock.AsyncMock()
    yield manager