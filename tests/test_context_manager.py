"""
测试上下文管理器
"""
import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from backend.core.context_manager import ContextManager


@pytest.mark.asyncio
async def test_share_context():
    """测试共享上下文"""
    # 模拟Redis客户端
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.publish = AsyncMock()
    redis_mock.lpush = AsyncMock()
    redis_mock.ltrim = AsyncMock()
    redis_mock.expire = AsyncMock()
    
    context_manager = ContextManager(redis_mock)
    
    # 测试共享上下文
    task_id = "test_task_123"
    agent_id = "test_agent"
    context = {"data": "test_data", "value": 42}
    
    result = await context_manager.share_context(task_id, agent_id, context)
    
    assert result is True
    
    # 验证Redis调用
    redis_mock.setex.assert_called_once()
    call_args = redis_mock.setex.call_args
    assert call_args[0][0] == f"nexusmind:context:{task_id}:{agent_id}"
    assert call_args[0][1] == 3600  # TTL
    
    # 验证存储的数据包含元数据
    stored_data = json.loads(call_args[0][2])
    assert stored_data["data"] == "test_data"
    assert stored_data["value"] == 42
    assert "_metadata" in stored_data
    assert stored_data["_metadata"]["agent_id"] == agent_id
    assert stored_data["_metadata"]["task_id"] == task_id
    
    # 验证发布事件
    redis_mock.publish.assert_called_once()


@pytest.mark.asyncio
async def test_get_shared_context():
    """测试获取共享上下文"""
    redis_mock = AsyncMock()
    
    # 模拟Redis返回数据
    context_data = {
        "data": "test_data",
        "value": 42,
        "_metadata": {
            "agent_id": "test_agent",
            "task_id": "test_task_123",
            "shared_at": datetime.now().isoformat()
        }
    }
    redis_mock.get = AsyncMock(return_value=json.dumps(context_data).encode())
    
    context_manager = ContextManager(redis_mock)
    
    # 测试获取上下文
    result = await context_manager.get_shared_context("test_task_123", "test_agent")
    
    assert result is not None
    assert result["data"] == "test_data"
    assert result["value"] == 42
    assert "_metadata" not in result  # 元数据应该被移除


@pytest.mark.asyncio
async def test_get_shared_context_not_found():
    """测试获取不存在的上下文"""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    
    context_manager = ContextManager(redis_mock)
    
    result = await context_manager.get_shared_context("nonexistent_task", "test_agent")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_task_context():
    """测试获取任务的所有上下文"""
    redis_mock = AsyncMock()
    
    # 模拟scan返回的keys
    keys = [
        b"nexusmind:context:task_123:agent1",
        b"nexusmind:context:task_123:agent2"
    ]
    redis_mock.scan = AsyncMock(side_effect=[(1, keys[:1]), (0, keys[1:])])
    
    # 模拟get返回的数据
    context1 = {"data": "from_agent1", "_metadata": {"agent_id": "agent1"}}
    context2 = {"data": "from_agent2", "_metadata": {"agent_id": "agent2"}}
    
    redis_mock.get = AsyncMock(side_effect=[
        json.dumps(context1).encode(),
        json.dumps(context2).encode()
    ])
    
    context_manager = ContextManager(redis_mock)
    
    # 测试获取任务上下文
    result = await context_manager.get_task_context("task_123")
    
    assert len(result) == 2
    assert "agent1" in result
    assert "agent2" in result
    assert result["agent1"]["data"] == "from_agent1"
    assert result["agent2"]["data"] == "from_agent2"
    assert "_metadata" not in result["agent1"]
    assert "_metadata" not in result["agent2"]


@pytest.mark.asyncio
async def test_merge_contexts():
    """测试合并多个智能体的上下文"""
    redis_mock = AsyncMock()
    
    # 模拟两个智能体的上下文
    context1 = {"transcription": "Hello world", "confidence": 0.95}
    context2 = {"faces": [{"bbox": [10, 20, 100, 100]}], "count": 1}
    
    redis_mock.get = AsyncMock(side_effect=[
        json.dumps({**context1, "_metadata": {}}).encode(),
        json.dumps({**context2, "_metadata": {}}).encode()
    ])
    
    context_manager = ContextManager(redis_mock)
    
    # 测试合并上下文
    result = await context_manager.merge_contexts("task_123", ["voice_agent", "vision_agent"])
    
    assert len(result) == 2
    assert "voice_agent" in result
    assert "vision_agent" in result
    assert result["voice_agent"]["transcription"] == "Hello world"
    assert result["vision_agent"]["count"] == 1


@pytest.mark.asyncio
async def test_get_task_history():
    """测试获取任务历史"""
    redis_mock = AsyncMock()
    
    # 模拟历史记录
    history_entries = [
        {
            "timestamp": "2024-01-01T12:00:00",
            "agent_id": "agent1",
            "event_type": "context_shared",
            "data": {"test": "data1"}
        },
        {
            "timestamp": "2024-01-01T12:01:00",
            "agent_id": "agent2",
            "event_type": "context_shared",
            "data": {"test": "data2"}
        }
    ]
    
    redis_mock.lrange = AsyncMock(return_value=[
        json.dumps(entry).encode() for entry in history_entries
    ])
    
    context_manager = ContextManager(redis_mock)
    
    # 测试获取历史
    result = await context_manager.get_task_history("task_123", limit=10)
    
    assert len(result) == 2
    assert result[0]["agent_id"] == "agent1"
    assert result[1]["agent_id"] == "agent2"
    
    # 验证Redis调用
    redis_mock.lrange.assert_called_once_with(
        "nexusmind:task:task_123:history", 0, 9
    )


@pytest.mark.asyncio
async def test_get_active_tasks():
    """测试获取活跃任务"""
    redis_mock = AsyncMock()
    
    # 模拟scan返回的keys
    keys = [
        b"nexusmind:context:task_123:agent1",
        b"nexusmind:context:task_456:agent2",
        b"nexusmind:context:task_123:agent3"
    ]
    redis_mock.scan = AsyncMock(return_value=(0, keys))
    
    context_manager = ContextManager(redis_mock)
    
    # 测试获取活跃任务
    result = await context_manager.get_active_tasks()
    
    assert len(result) == 2
    assert "task_123" in result
    assert "task_456" in result


@pytest.mark.asyncio
async def test_get_task_summary():
    """测试获取任务摘要"""
    redis_mock = AsyncMock()
    
    # 模拟上下文数据
    contexts = {
        b"nexusmind:context:task_123:agent1": json.dumps({
            "data": "context1",
            "_metadata": {"agent_id": "agent1", "task_id": "task_123"}
        }).encode(),
        b"nexusmind:context:task_123:agent2": json.dumps({
            "data": "context2",
            "_metadata": {"agent_id": "agent2", "task_id": "task_123"}
        }).encode()
    }
    
    redis_mock.scan = AsyncMock(return_value=(0, list(contexts.keys())))
    redis_mock.get = AsyncMock(side_effect=list(contexts.values()))
    
    # 模拟历史记录
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent_id": "agent1",
        "event_type": "context_shared",
        "data": {}
    }
    redis_mock.lrange = AsyncMock(return_value=[json.dumps(history_entry).encode()])
    
    # 模拟订阅者
    redis_mock.smembers = AsyncMock(return_value={b"agent1", b"agent2"})
    
    context_manager = ContextManager(redis_mock)
    
    # 测试获取摘要
    result = await context_manager.get_task_summary("task_123")
    
    assert result["task_id"] == "task_123"
    assert len(result["active_agents"]) == 2
    assert result["subscriber_count"] == 2
    assert result["context_count"] == 2
    assert result["recent_events"] == 1
    assert result["last_update"] is not None