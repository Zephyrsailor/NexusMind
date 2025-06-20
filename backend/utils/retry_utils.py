"""
重试工具模块
提供通用的重试装饰器和异步重试功能
"""
import asyncio
import functools
import logging
from typing import TypeVar, Callable, Any, Optional, Union, Type, Tuple
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """重试失败时抛出的异常"""
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    计算指数退避延迟时间
    
    Args:
        attempt: 当前尝试次数（从0开始）
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        jitter: 是否添加随机抖动
        
    Returns:
        float: 延迟时间（秒）
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    if jitter:
        # 添加±25%的随机抖动
        delay = delay * (0.75 + random.random() * 0.5)
        
    return delay


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    同步函数重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 是否使用指数退避
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
        
    Returns:
        装饰后的函数
        
    Example:
        @retry(max_attempts=3, delay=1.0)
        def unstable_function():
            # 可能失败的操作
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        if on_retry:
                            on_retry(e, attempt + 1)
                            
                        wait_time = exponential_backoff(attempt, delay) if backoff else delay
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {wait_time:.2f}s delay. Error: {e}"
                        )
                        
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
                        
            raise RetryError(
                f"Failed after {max_attempts} attempts",
                last_exception
            )
            
        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], Any]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    异步函数重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 是否使用指数退避
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数（可以是异步函数）
        
    Returns:
        装饰后的异步函数
        
    Example:
        @async_retry(max_attempts=3, delay=1.0)
        async def unstable_async_function():
            # 可能失败的异步操作
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        if on_retry:
                            if asyncio.iscoroutinefunction(on_retry):
                                await on_retry(e, attempt + 1)
                            else:
                                on_retry(e, attempt + 1)
                                
                        wait_time = exponential_backoff(attempt, delay) if backoff else delay
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {wait_time:.2f}s delay. Error: {e}"
                        )
                        
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
                        
            raise RetryError(
                f"Failed after {max_attempts} attempts",
                last_exception
            )
            
        return wrapper
    return decorator


class RetryContext:
    """
    重试上下文管理器
    
    提供更灵活的重试控制，支持在运行时决定是否重试
    
    Example:
        async with RetryContext(max_attempts=3) as retry_ctx:
            for attempt in retry_ctx:
                try:
                    result = await some_operation()
                    break
                except SomeError as e:
                    if not retry_ctx.should_retry(e):
                        raise
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.current_attempt = 0
        self.last_exception = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False
        
    def __iter__(self):
        """同步迭代"""
        while self.current_attempt < self.max_attempts:
            yield self.current_attempt
            self.current_attempt += 1
            
    async def __aiter__(self):
        """异步迭代"""
        while self.current_attempt < self.max_attempts:
            yield self.current_attempt
            self.current_attempt += 1
            
    def should_retry(self, exception: Exception) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 发生的异常
            
        Returns:
            bool: 是否应该重试
        """
        self.last_exception = exception
        
        if self.current_attempt >= self.max_attempts:
            return False
            
        return isinstance(exception, self.exceptions)
        
    async def wait_before_retry(self) -> None:
        """等待重试延迟"""
        if self.current_attempt > 0:
            wait_time = (
                exponential_backoff(self.current_attempt - 1, self.delay)
                if self.backoff
                else self.delay
            )
            await asyncio.sleep(wait_time)