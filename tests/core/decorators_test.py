import time

import pytest

from backend.base.decorators import retry_on_exception


@pytest.mark.asyncio
async def test_retry_on_exception():
    function_calls = []

    @retry_on_exception(max_retries=3, delay=0)
    def test_function():
        function_calls.append("test_function")
        raise Exception("Test exception")

    with pytest.raises(Exception) as e:
        test_function()
    assert str(e.value) == "Test exception"
    assert function_calls == ["test_function",
                              "test_function", "test_function"]


@pytest.mark.asyncio
async def test_retry_on_exception_with_delay():
    function_calls = []

    start_time = time.perf_counter()

    @retry_on_exception(max_retries=3, delay=1)
    def test_function():
        function_calls.append("test_function")
        raise Exception("Test exception")

    with pytest.raises(Exception) as e:
        test_function()
    assert str(e.value) == "Test exception"
    assert function_calls == ["test_function",
                              "test_function", "test_function"]
    elapsed_time = time.perf_counter() - start_time
    assert elapsed_time >= 2


@pytest.mark.asyncio
async def test_retry_on_exception_with_successful_call():
    function_calls = []

    @retry_on_exception(max_retries=3, delay=0)
    def test_function():
        function_calls.append("test_function")
        return "Test function"

    assert test_function() == "Test function"
    assert function_calls == ["test_function"]


@pytest.mark.asyncio
async def test_retry_on_exception_with_successful_retry():
    function_calls = []

    @retry_on_exception(max_retries=3, delay=0)
    def test_function():
        if len(function_calls) == 0:
            function_calls.append("test_function")
            raise Exception("Test exception")
        return "Test function"

    assert test_function() == "Test function"
    assert function_calls == ["test_function"]
