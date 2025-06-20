"""
测试A2A客户端
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from backend.utils.a2a_client import A2AClient
from backend.models.schemas import A2AMessage, A2AResponse


@pytest.mark.asyncio
async def test_initialize():
    """测试A2A客户端初始化"""
    client = A2AClient()
    
    # 模拟连接
    with patch('aio_pika.connect_robust', new_callable=AsyncMock) as mock_connect:
        with patch('aioredis.create_redis_pool', new_callable=AsyncMock) as mock_redis:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_exchange = AsyncMock()
            
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_connect.return_value = mock_connection
            
            await client.initialize()
            
            assert client.rabbitmq_connection is not None
            assert client.rabbitmq_channel is not None
            assert client.redis_client is not None
            assert client.context_manager is not None
            
            # 验证连接被调用
            mock_connect.assert_called_once()
            mock_redis.assert_called_once()


@pytest.mark.asyncio
async def test_register_agent():
    """测试注册智能体"""
    client = A2AClient()
    client.redis_client = AsyncMock()
    client.rabbitmq_channel = AsyncMock()
    
    # 模拟队列
    mock_queue = AsyncMock()
    client.rabbitmq_channel.declare_queue = AsyncMock(return_value=mock_queue)
    
    agent_card = {
        "agent_id": "test_agent",
        "name": "Test Agent",
        "capabilities": ["test", "demo"],
        "description": "Test agent for unit testing"
    }
    
    result = await client.register_agent(agent_card)
    
    assert result is True
    assert "test_agent" in client.agent_registry
    
    # 验证Redis调用
    client.redis_client.hset.assert_called_once()
    call_args = client.redis_client.hset.call_args
    assert call_args[0][0] == "nexusmind:agents"
    assert call_args[0][1] == "test_agent"
    
    # 验证队列创建
    client.rabbitmq_channel.declare_queue.assert_called_once()
    queue_args = client.rabbitmq_channel.declare_queue.call_args
    assert queue_args[0][0] == "nexusmind.agent.test_agent"


@pytest.mark.asyncio
async def test_register_agent_invalid():
    """测试注册无效的智能体"""
    client = A2AClient()
    
    # 缺少必需字段
    invalid_card = {
        "agent_id": "test_agent",
        # 缺少name和capabilities
    }
    
    result = await client.register_agent(invalid_card)
    
    assert result is False


@pytest.mark.asyncio
async def test_discover_agents():
    """测试发现智能体"""
    client = A2AClient()
    client.redis_client = AsyncMock()
    
    # 模拟Redis返回的智能体数据
    agents_data = {
        b"agent1": json.dumps({
            "agent_id": "agent1",
            "name": "Agent 1",
            "capabilities": ["cap1"]
        }).encode(),
        b"agent2": json.dumps({
            "agent_id": "agent2",
            "name": "Agent 2",
            "capabilities": ["cap2"]
        }).encode()
    }
    
    client.redis_client.hgetall = AsyncMock(return_value=agents_data)
    
    result = await client.discover_agents()
    
    assert len(result) == 2
    assert "agent1" in result
    assert "agent2" in result
    assert result["agent1"]["name"] == "Agent 1"
    assert result["agent2"]["capabilities"] == ["cap2"]


@pytest.mark.asyncio
async def test_send_message():
    """测试发送消息"""
    client = A2AClient()
    client.rabbitmq_channel = AsyncMock()
    client.a2a_exchange = AsyncMock()
    
    # 模拟响应队列
    mock_response_queue = AsyncMock()
    mock_response_queue.name = "response.123"
    
    # 模拟消息响应
    mock_incoming_message = MagicMock()
    mock_incoming_message.body = json.dumps({
        "correlation_id": "123",
        "sender": "test_agent",
        "success": True,
        "result": {"data": "test_result"}
    }).encode()
    mock_incoming_message.ack = AsyncMock()
    
    # 设置异步迭代器
    async def async_iterator():
        yield mock_incoming_message
    
    mock_response_queue.__aiter__ = async_iterator
    mock_response_queue.delete = AsyncMock()
    
    client.rabbitmq_channel.declare_queue = AsyncMock(return_value=mock_response_queue)
    
    # 发送消息
    message = A2AMessage(
        message_id="123",
        sender="orchestrator",
        target="test_agent",
        action="test_action",
        payload={"test": "data"}
    )
    
    response = await client.send_message(message, timeout=5)
    
    assert response is not None
    assert response.success is True
    assert response.result["data"] == "test_result"
    
    # 验证交换机发布
    client.a2a_exchange.publish.assert_called_once()
    
    # 验证队列删除
    mock_response_queue.delete.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_timeout():
    """测试消息发送超时"""
    client = A2AClient()
    client.rabbitmq_channel = AsyncMock()
    client.a2a_exchange = AsyncMock()
    
    # 模拟响应队列但不返回消息
    mock_response_queue = AsyncMock()
    mock_response_queue.name = "response.123"
    
    # 空的异步迭代器（模拟超时）
    async def empty_iterator():
        # 模拟等待但不产生任何消息
        import asyncio
        await asyncio.sleep(0.1)
        return
        yield  # 使其成为生成器
    
    mock_response_queue.__aiter__ = empty_iterator
    mock_response_queue.delete = AsyncMock()
    
    client.rabbitmq_channel.declare_queue = AsyncMock(return_value=mock_response_queue)
    
    # 发送消息
    message = A2AMessage(
        message_id="123",
        sender="orchestrator",
        target="test_agent",
        action="test_action",
        payload={"test": "data"}
    )
    
    # 使用很短的超时时间
    response = await client.send_message(message, timeout=0.05)
    
    assert response is None


@pytest.mark.asyncio
async def test_get_agent_status():
    """测试获取智能体状态"""
    client = A2AClient()
    client.redis_client = AsyncMock()
    
    # 模拟状态数据
    status_data = {
        "agent_id": "test_agent",
        "status": "online",
        "last_seen": "2024-01-01T12:00:00",
        "metadata": {"version": "1.0"}
    }
    
    client.redis_client.get = AsyncMock(
        return_value=json.dumps(status_data).encode()
    )
    
    result = await client.get_agent_status("test_agent")
    
    assert result["agent_id"] == "test_agent"
    assert result["status"] == "online"
    assert result["metadata"]["version"] == "1.0"


@pytest.mark.asyncio
async def test_get_agent_status_unknown():
    """测试获取未知智能体状态"""
    client = A2AClient()
    client.redis_client = AsyncMock()
    client.redis_client.get = AsyncMock(return_value=None)
    
    result = await client.get_agent_status("unknown_agent")
    
    assert result["agent_id"] == "unknown_agent"
    assert result["status"] == "unknown"
    assert result["last_seen"] is None


@pytest.mark.asyncio
async def test_update_agent_status():
    """测试更新智能体状态"""
    client = A2AClient()
    client.redis_client = AsyncMock()
    
    await client.update_agent_status(
        "test_agent",
        "processing",
        {"current_task": "task_123"}
    )
    
    # 验证Redis调用
    client.redis_client.setex.assert_called_once()
    call_args = client.redis_client.setex.call_args
    assert call_args[0][0] == "nexusmind:agent_status:test_agent"
    assert call_args[0][1] == 300  # 5分钟TTL
    
    # 验证存储的数据
    stored_data = json.loads(call_args[0][2])
    assert stored_data["agent_id"] == "test_agent"
    assert stored_data["status"] == "processing"
    assert stored_data["metadata"]["current_task"] == "task_123"


@pytest.mark.asyncio
async def test_broadcast_message():
    """测试广播消息"""
    client = A2AClient()
    client.a2a_exchange = AsyncMock()
    
    message = A2AMessage(
        message_id="broadcast_123",
        sender="orchestrator",
        target="*",
        action="announcement",
        payload={"message": "System update"}
    )
    
    await client.broadcast_message(message)
    
    # 验证广播
    client.a2a_exchange.publish.assert_called_once()
    call_args = client.a2a_exchange.publish.call_args
    assert call_args[1]["routing_key"] == "agent.*"