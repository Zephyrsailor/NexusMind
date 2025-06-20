"""
测试API接口
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from backend.api.main import app, orchestrator, a2a_client, context_manager
from backend.models.schemas import TaskResponse, TaskStatus


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """模拟orchestrator"""
    with patch('backend.api.main.orchestrator') as mock:
        mock.process_request = AsyncMock(return_value=TaskResponse(
            task_id="test_123",
            status=TaskStatus.COMPLETED,
            message="测试完成",
            payload={"result": "success"}
        ))
        yield mock


@pytest.fixture
def mock_a2a_client():
    """模拟A2A客户端"""
    with patch('backend.api.main.a2a_client') as mock:
        mock.discover_agents = AsyncMock(return_value={
            "agent1": {"name": "Agent 1", "capabilities": ["cap1"]},
            "agent2": {"name": "Agent 2", "capabilities": ["cap2"]}
        })
        mock.get_all_agent_statuses = AsyncMock(return_value=[
            {"agent_id": "agent1", "status": "online"},
            {"agent_id": "agent2", "status": "processing"}
        ])
        yield mock


@pytest.fixture
def mock_context_manager():
    """模拟上下文管理器"""
    with patch('backend.api.main.context_manager') as mock:
        mock.get_active_tasks = AsyncMock(return_value=["task_123", "task_456"])
        mock.get_task_summary = AsyncMock(return_value={
            "task_id": "task_123",
            "active_agents": ["agent1"],
            "context_count": 2
        })
        yield mock


class TestBasicAPIs:
    """测试基础API"""
    
    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "NexusMind" in data["service"]
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_system_status(self, client, mock_orchestrator):
        """测试系统状态"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "orchestrator" in data
        assert "connections" in data
        assert "config" in data


class TestProcessingAPIs:
    """测试处理API"""
    
    def test_process_request(self, client, mock_orchestrator):
        """测试处理请求"""
        request_data = {
            "message": "测试消息",
            "metadata": {}
        }
        
        response = client.post("/api/v1/process", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test_123"
        assert data["status"] == "completed"
        assert data["message"] == "测试完成"
    
    def test_process_request_with_audio(self, client, mock_orchestrator):
        """测试处理包含音频的请求"""
        request_data = {
            "message": "转录音频",
            "audio_data": "base64_encoded_audio",
            "metadata": {"audio_format": "wav"}
        }
        
        response = client.post("/api/v1/process", json=request_data)
        assert response.status_code == 200


class TestAgentAPIs:
    """测试智能体API"""
    
    def test_list_agents(self, client, mock_a2a_client):
        """测试列出智能体"""
        response = client.get("/api/v1/agents/list")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert "agent1" in data["agents"]
        assert "agent2" in data["agents"]
    
    def test_get_all_agents_status(self, client, mock_a2a_client):
        """测试获取所有智能体状态"""
        response = client.get("/api/v1/agents/status")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["statuses"]) == 2
    
    def test_get_agent_status(self, client, mock_a2a_client):
        """测试获取特定智能体状态"""
        mock_a2a_client.get_agent_status = AsyncMock(return_value={
            "agent_id": "test_agent",
            "status": "online",
            "last_seen": "2024-01-01T12:00:00"
        })
        
        response = client.get("/api/v1/agents/test_agent/status")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test_agent"
        assert data["status"] == "online"


class TestTaskAPIs:
    """测试任务API"""
    
    def test_get_active_tasks(self, client, mock_context_manager):
        """测试获取活跃任务"""
        response = client.get("/api/v1/tasks/active")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["tasks"]) == 2
    
    def test_get_task_context(self, client, mock_context_manager):
        """测试获取任务上下文"""
        mock_context_manager.get_task_context = AsyncMock(return_value={
            "agent1": {"data": "context1"},
            "agent2": {"data": "context2"}
        })
        mock_context_manager.get_task_history = AsyncMock(return_value=[
            {"timestamp": "2024-01-01T12:00:00", "event": "started"}
        ])
        
        response = client.get("/api/v1/tasks/task_123/context")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_123"
        assert data["agent_count"] == 2
        assert "contexts" in data
        assert "history" in data


class TestMonitoringAPIs:
    """测试监控API"""
    
    def test_dashboard_data(self, client, mock_a2a_client, mock_context_manager):
        """测试仪表板数据"""
        response = client.get("/api/v1/monitor/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert data["agents"]["total"] == 2
        assert data["agents"]["online"] == 1
        assert data["tasks"]["active"] == 2
    
    def test_system_metrics(self, client, mock_a2a_client, mock_context_manager):
        """测试系统度量"""
        response = client.get("/api/v1/monitor/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "counters" in data
        assert "gauges" in data
        assert "histograms" in data
        assert data["counters"]["agents_total"] == 2
    
    def test_detailed_health(self, client):
        """测试详细健康检查"""
        # 模拟各个组件
        with patch('backend.api.main.orchestrator') as mock_orch:
            mock_orch.redis_client = AsyncMock()
            mock_orch.redis_client.ping = AsyncMock()
            mock_orch.llm = MagicMock()
            
            with patch('backend.api.main.a2a_client') as mock_a2a:
                mock_a2a.rabbitmq_connection = MagicMock()
                mock_a2a.get_all_agent_statuses = AsyncMock(return_value=[
                    {"status": "online"}
                ])
                
                response = client.get("/api/v1/monitor/health/detailed")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] in ["healthy", "degraded"]
                assert "checks" in data
                assert "redis" in data["checks"]
                assert "rabbitmq" in data["checks"]


class TestWebSocketAPIs:
    """测试WebSocket API"""
    
    def test_websocket_connection(self, client):
        """测试WebSocket连接"""
        with client.websocket_connect("/ws/test_client") as websocket:
            # 接收欢迎消息
            data = websocket.receive_json()
            assert data["type"] == "connection"
            assert "test_client" in data["message"]
            
            # 发送ping
            websocket.send_json({
                "type": "ping"
            })
            
            # 接收pong
            data = websocket.receive_json()
            assert data["type"] == "pong"
    
    def test_websocket_user_request(self, client, mock_orchestrator):
        """测试通过WebSocket发送用户请求"""
        with client.websocket_connect("/ws/test_client") as websocket:
            # 跳过欢迎消息
            websocket.receive_json()
            
            # 发送用户请求
            websocket.send_json({
                "type": "user_request",
                "payload": {
                    "message": "测试WebSocket请求",
                    "metadata": {}
                }
            })
            
            # 接收处理开始通知
            data = websocket.receive_json()
            assert data["type"] == "task_started"
            assert "task_id" in data
            
            # 接收完成通知
            data = websocket.receive_json()
            assert data["type"] == "task_completed"
            assert data["status"] == "completed"
    
    def test_websocket_monitor(self, client, mock_a2a_client, mock_context_manager):
        """测试监控WebSocket"""
        # 由于监控WebSocket会无限循环，我们只测试第一次更新
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # 让sleep立即抛出异常以退出循环
            mock_sleep.side_effect = WebSocketDisconnect()
            
            try:
                with client.websocket_connect("/ws/monitor") as websocket:
                    # 应该收到至少一次状态更新
                    data = websocket.receive_json()
                    assert data["type"] == "status_update"
                    assert "data" in data
                    assert "agents" in data["data"]
                    assert "tasks" in data["data"]
                    assert "system" in data["data"]
            except WebSocketDisconnect:
                # 预期的断开
                pass