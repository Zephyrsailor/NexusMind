"""
pytest配置文件
提供测试夹具和配置
"""
import pytest
import asyncio
import os
from typing import AsyncGenerator, Generator
import redis.asyncio as aioredis
import aio_pika
from unittest.mock import Mock, AsyncMock

# 设置测试环境变量
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["LLM_API_KEY"] = "test_key"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def redis_client() -> AsyncGenerator:
    """创建Redis测试客户端"""
    client = await aioredis.from_url(
        "redis://localhost:6379/15",  # 使用测试数据库
        decode_responses=False,
        max_connections=2
    )
    
    # 清理测试数据库
    await client.flushdb()
    
    yield client
    
    # 清理并关闭
    await client.flushdb()
    await client.close()


@pytest.fixture
async def rabbitmq_connection() -> AsyncGenerator:
    """创建RabbitMQ测试连接"""
    connection = await aio_pika.connect_robust(
        "amqp://nexusmind:nexusmind123@localhost:5672/"
    )
    
    yield connection
    
    await connection.close()


@pytest.fixture
async def rabbitmq_channel(rabbitmq_connection) -> AsyncGenerator:
    """创建RabbitMQ测试通道"""
    channel = await rabbitmq_connection.channel()
    yield channel
    await channel.close()


@pytest.fixture
def mock_llm():
    """模拟LLM"""
    mock = Mock()
    mock.invoke = Mock(return_value=Mock(content='{"intent": "test", "required_agents": []}'))
    return mock


@pytest.fixture
def mock_a2a_client():
    """模拟A2A客户端"""
    client = AsyncMock()
    client.discover_agents = AsyncMock(return_value={})
    client.send_message = AsyncMock(return_value=Mock(success=True, result={"test": "result"}))
    client.register_agent = AsyncMock(return_value=True)
    client.get_agent_status = AsyncMock(return_value={"status": "online"})
    return client


@pytest.fixture
async def test_agent_card():
    """测试用智能体卡片"""
    return {
        "agent_id": "test_agent",
        "name": "Test Agent",
        "description": "Agent for testing",
        "capabilities": ["test_capability"],
        "input_schema": {"test_input": "string"},
        "output_schema": {"test_output": "string"},
        "version": "1.0.0",
        "protocol": "a2a/1.0"
    }


@pytest.fixture
async def test_user_request():
    """测试用用户请求"""
    from backend.models.schemas import UserRequest
    return UserRequest(
        message="Test message",
        metadata={"test": "metadata"}
    )


@pytest.fixture
async def test_a2a_message():
    """测试用A2A消息"""
    from backend.models.schemas import A2AMessage
    return A2AMessage(
        sender="test_sender",
        target="test_target",
        action="test_action",
        payload={"test": "payload"}
    )