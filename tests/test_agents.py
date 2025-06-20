"""
测试智能体实现
"""
import pytest
import json
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.core.agents.base_agent import BaseAgent
from backend.core.agents.voice_agent import VoiceInteractionAgent
from backend.core.agents.vision_agent import VisionCaptureAgent
from backend.models.schemas import A2AMessage, A2AResponse


class TestBaseAgent:
    """测试基础智能体"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """测试智能体初始化"""
        # 创建测试智能体
        class TestAgent(BaseAgent):
            def get_capabilities(self):
                return ["test_capability"]
            
            def get_input_schema(self):
                return {"test": "schema"}
            
            def get_output_schema(self):
                return {"output": "schema"}
            
            async def process_request(self, message):
                return A2AResponse(
                    correlation_id=message.message_id,
                    sender=self.agent_id,
                    success=True,
                    result={"test": "result"}
                )
        
        agent = TestAgent("test_agent", "Test Agent", "Test description")
        
        assert agent.agent_id == "test_agent"
        assert agent.name == "Test Agent"
        assert agent.description == "Test description"
        assert agent.running is False
        
        # 测试获取智能体卡片
        card = agent.get_agent_card()
        assert card["agent_id"] == "test_agent"
        assert card["capabilities"] == ["test_capability"]
        assert card["protocol"] == "a2a/1.0"


class TestVoiceInteractionAgent:
    """测试语音交互智能体"""
    
    @pytest.mark.asyncio
    async def test_voice_agent_creation(self):
        """测试语音智能体创建"""
        agent = VoiceInteractionAgent()
        
        assert agent.agent_id == "voice_interaction_agent"
        assert "speech_to_text" in agent.get_capabilities()
        assert "start_meeting_record" in agent.get_capabilities()
        
        # 测试输入输出模式
        input_schema = agent.get_input_schema()
        assert "action" in input_schema
        assert "audio_data" in input_schema
        
        output_schema = agent.get_output_schema()
        assert "text" in output_schema
        assert "confidence" in output_schema
    
    @pytest.mark.asyncio
    async def test_speech_to_text_request(self):
        """测试语音转文字请求"""
        agent = VoiceInteractionAgent()
        
        # 模拟context manager
        agent.share_context = AsyncMock()
        agent.log_activity = AsyncMock()
        
        # 模拟音频数据
        audio_data = base64.b64encode(b"fake_audio_data").decode()
        
        message = A2AMessage(
            message_id="test_123",
            sender="orchestrator",
            target="voice_interaction_agent",
            action="speech_to_text",
            payload={
                "action": "speech_to_text",
                "audio_data": audio_data,
                "audio_format": "wav",
                "task_id": "task_123"
            }
        )
        
        # 模拟transcribe方法
        with patch.object(agent, '_transcribe_with_sr', 
                         return_value=("Hello world", 0.95, "en")):
            response = await agent.process_request(message)
        
        assert response.success is True
        assert response.result["text"] == "Hello world"
        assert response.result["confidence"] == 0.95
        assert response.result["language"] == "en"
        
        # 验证上下文共享
        agent.share_context.assert_called_once()
        context_args = agent.share_context.call_args[0]
        assert context_args[0] == "task_123"
        assert context_args[1]["transcription"] == "Hello world"
    
    @pytest.mark.asyncio
    async def test_meeting_management(self):
        """测试会议管理功能"""
        agent = VoiceInteractionAgent()
        agent.share_context = AsyncMock()
        agent.log_activity = AsyncMock()
        
        # 开始会议
        start_message = A2AMessage(
            message_id="start_123",
            sender="orchestrator",
            target="voice_interaction_agent",
            action="start_meeting_record",
            payload={
                "action": "start_meeting_record",
                "task_id": "task_123"
            }
        )
        
        response = await agent.process_request(start_message)
        
        assert response.success is True
        assert "session_id" in response.result
        session_id = response.result["session_id"]
        assert response.result["status"] == "recording"
        
        # 验证会议会话被创建
        assert session_id in agent.meeting_sessions
        
        # 停止会议
        stop_message = A2AMessage(
            message_id="stop_123",
            sender="orchestrator",
            target="voice_interaction_agent",
            action="stop_meeting_record",
            payload={
                "action": "stop_meeting_record",
                "session_id": session_id,
                "task_id": "task_123"
            }
        )
        
        response = await agent.process_request(stop_message)
        
        assert response.success is True
        assert response.result["status"] == "completed"
        assert session_id not in agent.meeting_sessions


class TestVisionCaptureAgent:
    """测试视觉捕获智能体"""
    
    @pytest.mark.asyncio
    async def test_vision_agent_creation(self):
        """测试视觉智能体创建"""
        agent = VisionCaptureAgent()
        
        assert agent.agent_id == "vision_capture_agent"
        assert "object_detection" in agent.get_capabilities()
        assert "face_recognition" in agent.get_capabilities()
        assert "ocr" in agent.get_capabilities()
        
        # 测试输入输出模式
        input_schema = agent.get_input_schema()
        assert "image_data" in input_schema
        assert "image_format" in input_schema
        
        output_schema = agent.get_output_schema()
        assert "detections" in output_schema
        assert "faces" in output_schema
    
    @pytest.mark.asyncio
    async def test_face_recognition(self):
        """测试人脸识别"""
        agent = VisionCaptureAgent()
        agent.share_context = AsyncMock()
        agent.log_activity = AsyncMock()
        
        # 模拟级联分类器
        agent.face_cascade = MagicMock()
        agent.eye_cascade = MagicMock()
        
        # 模拟检测结果
        agent.face_cascade.detectMultiScale = MagicMock(
            return_value=[(10, 20, 100, 100), (200, 50, 80, 80)]
        )
        agent.eye_cascade.detectMultiScale = MagicMock(
            return_value=[(0, 0, 20, 20), (30, 0, 20, 20)]
        )
        
        # 创建测试图像数据
        image_data = base64.b64encode(b"fake_image_data").decode()
        
        message = A2AMessage(
            message_id="test_123",
            sender="orchestrator",
            target="vision_capture_agent",
            action="face_recognition",
            payload={
                "action": "face_recognition",
                "image_data": image_data,
                "task_id": "task_123"
            }
        )
        
        # 模拟图像解码
        with patch.object(agent, '_decode_image', return_value=MagicMock(shape=(480, 640, 3))):
            with patch('cv2.cvtColor', return_value=MagicMock()):
                response = await agent.process_request(message)
        
        assert response.success is True
        assert response.result["count"] == 2
        assert len(response.result["faces"]) == 2
        
        # 验证上下文共享
        agent.share_context.assert_called_once()
        context_args = agent.share_context.call_args[0]
        assert context_args[0] == "task_123"
        assert context_args[1]["face_count"] == 2
    
    @pytest.mark.asyncio
    async def test_ocr_processing(self):
        """测试OCR处理"""
        agent = VisionCaptureAgent()
        agent.share_context = AsyncMock()
        agent.log_activity = AsyncMock()
        
        # 模拟OCR结果
        with patch('pytesseract.image_to_string', return_value="Hello World\nTest Text"):
            with patch('pytesseract.image_to_data', return_value={
                'conf': ['95', '90', '85', '92']
            }):
                with patch.object(agent, '_decode_image', return_value=MagicMock()):
                    with patch.object(agent, '_preprocess_for_ocr', return_value=MagicMock()):
                        
                        image_data = base64.b64encode(b"fake_image_data").decode()
                        
                        message = A2AMessage(
                            message_id="test_123",
                            sender="orchestrator",
                            target="vision_capture_agent",
                            action="ocr",
                            payload={
                                "action": "ocr",
                                "image_data": image_data,
                                "task_id": "task_123",
                                "options": {
                                    "language": "eng"
                                }
                            }
                        )
                        
                        response = await agent.process_request(message)
        
        assert response.success is True
        assert "Hello World" in response.result["text"]
        assert response.result["confidence"] > 0
        assert response.result["language"] == "eng"
        assert response.result["word_count"] == 3
    
    @pytest.mark.asyncio
    async def test_scene_analysis(self):
        """测试场景分析"""
        agent = VisionCaptureAgent()
        agent.share_context = AsyncMock()
        agent.log_activity = AsyncMock()
        
        # 模拟场景分析
        with patch.object(agent, '_decode_image', return_value=MagicMock(shape=(480, 640, 3))):
            with patch.object(agent, '_analyze_scene', return_value={
                "brightness": 0.6,
                "contrast": 0.4,
                "complexity": 0.3,
                "is_indoor": True,
                "is_daytime": True
            }):
                image_data = base64.b64encode(b"fake_image_data").decode()
                
                message = A2AMessage(
                    message_id="test_123",
                    sender="orchestrator",
                    target="vision_capture_agent",
                    action="scene_analysis",
                    payload={
                        "action": "scene_analysis",
                        "image_data": image_data,
                        "task_id": "task_123"
                    }
                )
                
                response = await agent.process_request(message)
        
        assert response.success is True
        assert response.result["scene"]["brightness"] == 0.6
        assert response.result["scene"]["is_indoor"] is True
        
        # 验证上下文共享
        agent.share_context.assert_called_once()
        context_args = agent.share_context.call_args[0]
        assert context_args[0] == "task_123"
        assert "scene_analysis" in context_args[1]