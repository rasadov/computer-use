import time

import pytest

from backend.base.decorators import retry_on_exception


class TestClass:
    "Test function to check `retry_on_exception` decorator and track function calls"
    def __init__(self, fail_till: int = 3):
        self.fail_till = fail_till
        self.function_calls = []
        self.success_calls = []
        self.attempts = 0

    @retry_on_exception(max_retries=3, delay=0)
    def test_function(self, exception: Exception) -> None:
        self.attempts += 1
        self.function_calls.append("test_function")
        if self.attempts <= self.fail_till:
            raise exception
        self.success_calls.append("test_function")

    @retry_on_exception(max_retries=3, delay=1)
    def test_function_with_delay(self, exception: Exception) -> None:
        self.attempts += 1
        self.function_calls.append("test_function_with_delay")
        if self.attempts <= self.fail_till:
            raise exception
        self.success_calls.append("test_function_with_delay")

    def __repr__(self) -> str:
        return f"TestClass(fail_till={self.fail_till}, function_calls={self.function_calls}, success_calls={self.success_calls})"


@pytest.mark.asyncio
async def test_retry_on_exception():
    test_instance = TestClass(fail_till=4)  # Will fail all 4 attempts (1 initial + 3 retries)

    with pytest.raises(Exception) as e:
        test_instance.test_function(Exception("Test exception"))
    assert str(e.value) == "Test exception"
    assert test_instance.function_calls == ["test_function", "test_function", 
                              "test_function", "test_function"]
    assert test_instance.success_calls == []


@pytest.mark.asyncio
async def test_retry_on_exception_with_delay():
    test_instance = TestClass()

    assert test_instance.test_function_with_delay(Exception("Test exception")) is None

    assert len(test_instance.function_calls) == 4
    assert test_instance.success_calls == ["test_function_with_delay"]


@pytest.mark.asyncio
async def test_retry_on_exception_with_successful_call():
    test_instance = TestClass()

    assert test_instance.test_function(Exception("Test exception")) is None
    assert test_instance.function_calls == ["test_function", "test_function", 
                              "test_function", "test_function"]
    assert test_instance.success_calls == ["test_function"]


@pytest.mark.asyncio
async def test_retry_on_exception_with_successful_retry():
    test_instance = TestClass(fail_till=2)

    assert test_instance.test_function(Exception("Test exception")) is None
    assert test_instance.function_calls == ["test_function", "test_function", "test_function"]
    assert test_instance.success_calls == ["test_function"]
