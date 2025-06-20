"""
重试工具模块的单元测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, call
from backend.utils.retry_utils import (
    retry,
    async_retry,
    exponential_backoff,
    RetryError,
    RetryContext
)


class TestExponentialBackoff:
    """指数退避算法测试"""
    
    def test_exponential_backoff_basic(self):
        """测试基本指数退避"""
        # 无抖动
        assert exponential_backoff(0, base_delay=1.0, jitter=False) == 1.0
        assert exponential_backoff(1, base_delay=1.0, jitter=False) == 2.0
        assert exponential_backoff(2, base_delay=1.0, jitter=False) == 4.0
        assert exponential_backoff(3, base_delay=1.0, jitter=False) == 8.0
        
    def test_exponential_backoff_max_delay(self):
        """测试最大延迟限制"""
        assert exponential_backoff(10, base_delay=1.0, max_delay=5.0, jitter=False) == 5.0
        
    def test_exponential_backoff_jitter(self):
        """测试随机抖动"""
        # 使用抖动时，结果应该在75%到125%之间
        delay = exponential_backoff(2, base_delay=1.0, jitter=True)
        assert 3.0 <= delay <= 5.0  # 4.0的75%到125%


class TestRetryDecorator:
    """同步重试装饰器测试"""
    
    def test_retry_success_first_attempt(self):
        """测试第一次尝试就成功"""
        mock_func = Mock(return_value="success")
        
        @retry(max_attempts=3)
        def test_func():
            return mock_func()
            
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1
        
    def test_retry_success_after_failures(self):
        """测试失败后重试成功"""
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        
        @retry(max_attempts=3, delay=0.01)
        def test_func():
            return mock_func()
            
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3
        
    def test_retry_all_attempts_fail(self):
        """测试所有尝试都失败"""
        mock_func = Mock(side_effect=Exception("always fail"))
        
        @retry(max_attempts=3, delay=0.01)
        def test_func():
            return mock_func()
            
        with pytest.raises(RetryError) as exc_info:
            test_func()
            
        assert "Failed after 3 attempts" in str(exc_info.value)
        assert mock_func.call_count == 3
        
    def test_retry_specific_exceptions(self):
        """测试只重试特定异常"""
        mock_func = Mock(side_effect=[ValueError("retry this"), "success"])
        
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def test_func():
            return mock_func()
            
        result = test_func()
        assert result == "success"
        
        # 不重试其他异常
        mock_func.side_effect = TypeError("don't retry this")
        with pytest.raises(TypeError):
            test_func()
            
    def test_retry_callback(self):
        """测试重试回调"""
        callback = Mock()
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        
        @retry(max_attempts=3, delay=0.01, on_retry=callback)
        def test_func():
            return mock_func()
            
        test_func()
        
        # 验证回调被调用
        assert callback.call_count == 1
        callback.assert_called_with(mock_func.side_effect[0], 1)


class TestAsyncRetryDecorator:
    """异步重试装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_async_retry_success_first_attempt(self):
        """测试异步函数第一次尝试就成功"""
        mock_func = Mock(return_value="success")
        
        @async_retry(max_attempts=3)
        async def test_func():
            return mock_func()
            
        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 1
        
    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self):
        """测试异步函数失败后重试成功"""
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        
        @async_retry(max_attempts=3, delay=0.01)
        async def test_func():
            return mock_func()
            
        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 3
        
    @pytest.mark.asyncio
    async def test_async_retry_with_async_callback(self):
        """测试异步重试回调"""
        callback_results = []
        
        async def async_callback(exc, attempt):
            callback_results.append((str(exc), attempt))
            
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        
        @async_retry(max_attempts=3, delay=0.01, on_retry=async_callback)
        async def test_func():
            return mock_func()
            
        await test_func()
        
        assert len(callback_results) == 1
        assert callback_results[0] == ("fail", 1)


class TestRetryContext:
    """重试上下文管理器测试"""
    
    @pytest.mark.asyncio
    async def test_retry_context_basic(self):
        """测试基本的重试上下文"""
        attempts = []
        
        async with RetryContext(max_attempts=3, delay=0.01) as retry_ctx:
            async for attempt in retry_ctx:
                attempts.append(attempt)
                if attempt < 2:
                    exc = Exception(f"Attempt {attempt} failed")
                    if retry_ctx.should_retry(exc):
                        await retry_ctx.wait_before_retry()
                        continue
                break
                
        assert attempts == [0, 1, 2]
        
    @pytest.mark.asyncio
    async def test_retry_context_selective_retry(self):
        """测试选择性重试"""
        async with RetryContext(max_attempts=3, exceptions=(ValueError,)) as retry_ctx:
            async for attempt in retry_ctx:
                if attempt == 0:
                    # 应该重试ValueError
                    assert retry_ctx.should_retry(ValueError("retry"))
                    # 不应该重试TypeError
                    assert not retry_ctx.should_retry(TypeError("don't retry"))
                break
                
    def test_retry_context_sync_iteration(self):
        """测试同步迭代"""
        attempts = []
        
        with RetryContext(max_attempts=3) as retry_ctx:
            for attempt in retry_ctx:
                attempts.append(attempt)
                
        assert attempts == [0, 1, 2]