"""
测试核心协调器
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.core.orchestrator import NexusMindOrchestrator, OrchestratorState
from backend.models.schemas import UserRequest, TaskResponse, TaskStatus, A2AMessage, A2AResponse


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """测试协调器初始化"""
    orchestrator = NexusMindOrchestrator()
    
    assert orchestrator.orchestrator_agent_id == "nexusmind_orchestrator"
    assert orchestrator.llm is not None
    
    # 模拟依赖
    with patch('aioredis.create_redis_pool', new_callable=AsyncMock) as mock_redis:
        with patch.object(orchestrator, 'a2a_client') as mock_a2a:
            mock_a2a.initialize = AsyncMock()
            orchestrator.a2a_client = mock_a2a
            
            await orchestrator.initialize()
            
            assert orchestrator.redis_client is not None
            assert orchestrator.context_manager is not None
            assert orchestrator.tools is not None
            assert orchestrator.graph is not None


@pytest.mark.asyncio
async def test_process_simple_request():
    """测试处理简单请求"""
    orchestrator = NexusMindOrchestrator()
    
    # 模拟已初始化状态
    orchestrator.graph = MagicMock()
    orchestrator.graph.ainvoke = AsyncMock(return_value=OrchestratorState(
        task_id="test_123",
        user_request=UserRequest(message="测试消息"),
        final_result={"reply_message": "处理完成"}
    ))
    
    # 模拟Redis
    orchestrator.redis_client = AsyncMock()
    
    # 处理请求
    request = UserRequest(message="测试消息")
    response = await orchestrator.process_request(request)
    
    assert response.status == TaskStatus.COMPLETED
    assert response.message == "任务已完成"
    assert response.payload["reply_message"] == "处理完成"


@pytest.mark.asyncio
async def test_analyze_request_with_audio():
    """测试分析包含音频的请求"""
    orchestrator = NexusMindOrchestrator()
    orchestrator.context_manager = AsyncMock()
    orchestrator.llm = MagicMock()
    
    # 模拟LLM响应
    orchestrator.llm.invoke = MagicMock(return_value=MagicMock(
        content=json.dumps({
            "intent": "transcribe_audio",
            "required_agents": ["voice_interaction_agent"],
            "actions": {"voice_interaction_agent": "speech_to_text"},
            "context_sharing_needed": True
        })
    ))
    
    # 创建包含音频的请求
    state = OrchestratorState(
        task_id="test_123",
        user_request=UserRequest(
            message="请转录这段音频",
            audio_data="base64_encoded_audio"
        )
    )
    
    # 执行分析
    result = await orchestrator._analyze_request(state)
    
    assert "request_analysis" in result.intermediate_results
    analysis = result.intermediate_results["request_analysis"]
    assert analysis["intent"] == "transcribe_audio"
    assert "voice_interaction_agent" in analysis["required_agents"]
    assert analysis["context_sharing_needed"] is True


@pytest.mark.asyncio
async def test_analyze_request_with_image():
    """测试分析包含图像的请求"""
    orchestrator = NexusMindOrchestrator()
    orchestrator.context_manager = AsyncMock()
    
    # 使用简单分析（不依赖LLM）
    state = OrchestratorState(
        task_id="test_123",
        user_request=UserRequest(
            message="识别图片中的文字",
            image_data="base64_encoded_image"
        )
    )
    
    # 模拟LLM失败，触发简单分析
    orchestrator.llm = MagicMock()
    orchestrator.llm.invoke = MagicMock(side_effect=Exception("LLM error"))
    
    result = await orchestrator._analyze_request(state)
    
    analysis = result.intermediate_results["request_analysis"]
    assert "vision_capture_agent" in analysis["required_agents"]
    assert analysis["actions"]["vision_capture_agent"] == "ocr"


@pytest.mark.asyncio
async def test_plan_execution():
    """测试执行计划规划"""
    orchestrator = NexusMindOrchestrator()
    
    state = OrchestratorState(
        task_id="test_123",
        user_request=UserRequest(message="测试"),
        intermediate_results={
            "request_analysis": {
                "required_agents": ["agent1", "agent2"],
                "actions": {
                    "agent1": "action1",
                    "agent2": "action2"
                },
                "context_sharing_needed": True
            }
        }
    )
    
    result = await orchestrator._plan_execution(state)
    
    plan = result.intermediate_results["execution_plan"]
    assert plan["agents_to_call"] == ["agent1", "agent2"]
    assert plan["parallel_execution"] is True
    assert plan["context_sharing"] is True


@pytest.mark.asyncio
async def test_execute_a2a_agents_parallel():
    """测试并行执行智能体"""
    orchestrator = NexusMindOrchestrator()
    orchestrator.a2a_client = AsyncMock()
    
    # 模拟智能体响应
    async def mock_send_message(message, timeout):
        if message.target == "voice_agent":
            return A2AResponse(
                correlation_id=message.message_id,
                sender="voice_agent",
                success=True,
                result={"text": "Hello world"}
            )
        elif message.target == "vision_agent":
            return A2AResponse(
                correlation_id=message.message_id,
                sender="vision_agent",
                success=True,
                result={"faces": [{"bbox": [10, 20, 100, 100]}]}
            )
        return None
    
    orchestrator.a2a_client.send_message = mock_send_message
    
    state = OrchestratorState(
        task_id="test_123",
        user_request=UserRequest(
            message="测试",
            audio_data="audio",
            image_data="image"
        ),
        intermediate_results={
            "execution_plan": {
                "agents_to_call": ["voice_agent", "vision_agent"],
                "actions": {
                    "voice_agent": "speech_to_text",
                    "vision_agent": "face_recognition"
                },
                "parallel_execution": True,
                "context_sharing": False
            }
        }
    )
    
    result = await orchestrator._execute_a2a_agents(state)
    
    agent_results = result.intermediate_results["agent_results"]
    assert "voice_agent" in agent_results
    assert "vision_agent" in agent_results
    assert agent_results["voice_agent"]["text"] == "Hello world"
    assert len(agent_results["vision_agent"]["faces"]) == 1


@pytest.mark.asyncio
async def test_aggregate_results():
    """测试聚合结果"""
    orchestrator = NexusMindOrchestrator()
    orchestrator.context_manager = AsyncMock()
    
    # 模拟上下文
    orchestrator.context_manager.get_task_context = AsyncMock(return_value={
        "voice_agent": {"transcription": "Hello"},
        "vision_agent": {"objects": ["person", "car"]}
    })
    
    state = OrchestratorState(
        task_id="test_123",
        user_request=UserRequest(message="测试"),
        intermediate_results={
            "execution_plan": {
                "context_sharing": True
            },
            "agent_results": {
                "voice_interaction_agent": {
                    "text": "Hello world",
                    "confidence": 0.95
                },
                "vision_capture_agent": {
                    "scene": {
                        "brightness": 0.7,
                        "is_indoor": True
                    }
                }
            }
        }
    )
    
    result = await orchestrator._aggregate_results(state)
    
    aggregated = result.intermediate_results["aggregated_results"]
    assert "task_id" in aggregated
    assert len(aggregated["agents_called"]) == 2
    assert "combined_analysis" in aggregated
    assert aggregated["combined_analysis"]["transcription"] == "Hello world"


@pytest.mark.asyncio
async def test_format_response():
    """测试格式化响应"""
    orchestrator = NexusMindOrchestrator()
    
    state = OrchestratorState(
        task_id="test_123",
        user_request=UserRequest(message="识别图片并转录音频"),
        intermediate_results={
            "request_analysis": {
                "intent": "multimodal_processing"
            },
            "agent_results": {
                "voice_interaction_agent": {
                    "text": "这是一段测试音频",
                    "confidence": 0.92
                },
                "vision_capture_agent": {
                    "text": "图片中的文字",
                    "faces": [{"bbox": [10, 20, 100, 100]}],
                    "count": 1
                }
            },
            "aggregated_results": {
                "task_id": "test_123"
            }
        }
    )
    
    result = orchestrator._format_response(state)
    
    assert result.final_result is not None
    final = result.final_result
    assert "task_id" in final
    assert "reply_message" in final
    assert "语音识别结果" in final["reply_message"]
    assert "OCR识别结果" in final["reply_message"]
    assert "检测到 1 个人脸" in final["reply_message"]


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    orchestrator = NexusMindOrchestrator()
    
    # 模拟graph执行错误
    orchestrator.graph = MagicMock()
    orchestrator.graph.ainvoke = AsyncMock(side_effect=Exception("测试错误"))
    
    orchestrator.redis_client = AsyncMock()
    
    request = UserRequest(message="测试错误处理")
    response = await orchestrator.process_request(request)
    
    assert response.status == TaskStatus.FAILED
    assert "处理失败" in response.message
    assert "测试错误" in response.message