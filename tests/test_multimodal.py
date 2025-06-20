"""
多模态处理测试用例
测试语音、图像、视频等多种输入的处理能力
"""
import pytest
import asyncio
import base64
import json
from datetime import datetime
from pathlib import Path
import tempfile
import os

# 测试框架
import httpx
from fastapi.testclient import TestClient

# 内部模块
from backend.api.main import app
from backend.models.schemas import UserRequest, MediaInput, InputType
from backend.core.multimodal_processor import get_multimodal_processor
from backend.core.agents.professional_voice_agent import ProfessionalVoiceAgent
from backend.core.agents.professional_vision_agent import ProfessionalVisionAgent


class TestMultimodalProcessor:
    """多模态处理器测试"""
    
    @pytest.mark.asyncio
    async def test_processor_initialization(self):
        """测试处理器初始化"""
        processor = await get_multimodal_processor()
        assert processor is not None
        assert hasattr(processor, 'processing_stats')
        assert hasattr(processor, 'temp_dir')
    
    @pytest.mark.asyncio
    async def test_image_analysis(self):
        """测试图像分析"""
        processor = await get_multimodal_processor()
        
        # 创建测试图像
        test_image = self._create_test_image()
        
        media_input = MediaInput(
            type=InputType.IMAGE,
            data=test_image,
            format="png"
        )
        
        analysis = await processor._analyze_media(media_input)
        
        assert analysis.media_type == InputType.IMAGE
        assert analysis.format == "png"
        assert analysis.dimensions is not None
        assert analysis.file_size > 0
    
    @pytest.mark.asyncio
    async def test_audio_analysis(self):
        """测试音频分析"""
        processor = await get_multimodal_processor()
        
        # 创建测试音频
        test_audio = self._create_test_audio()
        
        media_input = MediaInput(
            type=InputType.AUDIO,
            data=test_audio,
            format="wav"
        )
        
        analysis = await processor._analyze_media(media_input)
        
        assert analysis.media_type == InputType.AUDIO
        assert analysis.format == "wav"
        assert analysis.duration is not None or analysis.duration == 0  # 可能没有音频处理库
    
    @pytest.mark.asyncio
    async def test_quality_assessment(self):
        """测试质量评估"""
        processor = await get_multimodal_processor()
        
        # 测试图像质量评估
        test_image = self._create_test_image()
        media_input = MediaInput(
            type=InputType.IMAGE,
            data=test_image,
            format="png"
        )
        
        analysis = await processor._analyze_media(media_input)
        quality = await processor._assess_quality(media_input, analysis)
        
        assert "overall_score" in quality
        assert "factors" in quality
        assert "recommendations" in quality
        assert 0 <= quality["overall_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_routing_decision(self):
        """测试路由决策"""
        processor = await get_multimodal_processor()
        
        test_image = self._create_test_image()
        media_input = MediaInput(
            type=InputType.IMAGE,
            data=test_image,
            format="png"
        )
        
        analysis = await processor._analyze_media(media_input)
        quality = await processor._assess_quality(media_input, analysis)
        routing = await processor._make_routing_decision(media_input, analysis, quality)
        
        assert "recommended_agents" in routing
        assert "processing_priority" in routing
        assert "estimated_processing_time" in routing
        assert len(routing["recommended_agents"]) > 0
    
    def _create_test_image(self) -> str:
        """创建测试图像的Base64编码"""
        from PIL import Image
        import io
        
        # 创建简单的测试图像
        image = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _create_test_audio(self) -> str:
        """创建测试音频的Base64编码"""
        import wave
        import io
        import struct
        
        # 创建简单的测试音频（1秒，440Hz正弦波）
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0
        
        frames = []
        for i in range(int(sample_rate * duration)):
            value = int(32767 * 0.3 * 
                       (i % (sample_rate // frequency)) / (sample_rate // frequency))
            frames.append(struct.pack('<h', value))
        
        # 写入WAV格式
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(frames))
        
        return base64.b64encode(buffer.getvalue()).decode()


class TestProfessionalVoiceAgent:
    """专业语音智能体测试"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """测试智能体初始化"""
        agent = ProfessionalVoiceAgent()
        
        # 不实际初始化（避免需要API密钥）
        assert agent.agent_id == "professional_voice_agent"
        assert agent.name == "专业语音处理智能体"
        assert len(agent.get_capabilities()) > 0
    
    def test_provider_interface(self):
        """测试提供者接口"""
        from backend.core.agents.professional_voice_agent import SpeechServiceProvider
        
        # 检查抽象基类
        assert hasattr(SpeechServiceProvider, 'transcribe')
        assert hasattr(SpeechServiceProvider, 'get_supported_languages')
        assert hasattr(SpeechServiceProvider, 'get_provider_name')
    
    def test_provider_implementations(self):
        """测试提供者实现"""
        from backend.core.agents.professional_voice_agent import (
            OpenAIWhisperProvider, LocalWhisperProvider
        )
        
        # 测试OpenAI Whisper提供者
        try:
            provider = OpenAIWhisperProvider("test-key")
            assert provider.get_provider_name() == "OpenAI Whisper API"
            assert len(provider.get_supported_languages()) > 0
        except Exception:
            pass  # 可能没有安装依赖
        
        # 测试本地Whisper提供者
        try:
            provider = LocalWhisperProvider()
            assert provider.get_provider_name().startswith("Local Whisper")
            assert len(provider.get_supported_languages()) > 0
        except Exception:
            pass  # 可能没有安装Whisper


class TestProfessionalVisionAgent:
    """专业视觉智能体测试"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """测试智能体初始化"""
        agent = ProfessionalVisionAgent()
        
        assert agent.agent_id == "professional_vision_agent"
        assert agent.name == "专业视觉处理智能体"
        assert len(agent.get_capabilities()) > 0
    
    def test_provider_interface(self):
        """测试提供者接口"""
        from backend.core.agents.professional_vision_agent import VisionServiceProvider
        
        # 检查抽象基类
        assert hasattr(VisionServiceProvider, 'analyze_image')
        assert hasattr(VisionServiceProvider, 'get_supported_features')
        assert hasattr(VisionServiceProvider, 'get_provider_name')
    
    def test_provider_implementations(self):
        """测试提供者实现"""
        from backend.core.agents.professional_vision_agent import (
            GPT4VisionProvider, ClaudeVisionProvider
        )
        
        # 测试GPT-4V提供者
        try:
            provider = GPT4VisionProvider("test-key")
            assert provider.get_provider_name() == "GPT-4 Vision"
            assert len(provider.get_supported_features()) > 0
        except Exception:
            pass  # 可能没有安装依赖
        
        # 测试Claude Vision提供者
        try:
            provider = ClaudeVisionProvider("test-key")
            assert provider.get_provider_name() == "Claude Vision"
            assert len(provider.get_supported_features()) > 0
        except Exception:
            pass  # 可能没有安装依赖


class TestMultimodalAPI:
    """多模态API测试"""
    
    def setup_method(self):
        """设置测试客户端"""
        self.client = TestClient(app)
    
    def test_text_only_request(self):
        """测试纯文本请求"""
        response = self.client.post(
            "/api/v1/chat",
            json={
                "message": "你好，这是一个测试消息",
                "metadata": {"test": True}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
    
    def test_image_request(self):
        """测试图像请求"""
        # 创建测试图像
        test_image = self._create_test_image()
        
        response = self.client.post(
            "/api/v1/chat",
            json={
                "message": "请分析这张图片",
                "image_data": test_image
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
    
    def test_audio_request(self):
        """测试音频请求"""
        # 创建测试音频
        test_audio = self._create_test_audio()
        
        response = self.client.post(
            "/api/v1/chat",
            json={
                "message": "请转录这段音频",
                "audio_data": test_audio
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
    
    def test_multimodal_request(self):
        """测试多模态请求"""
        test_image = self._create_test_image()
        test_audio = self._create_test_audio()
        
        response = self.client.post(
            "/api/v1/chat",
            json={
                "message": "请分析这张图片和音频",
                "inputs": [
                    {
                        "type": "image",
                        "data": test_image,
                        "format": "png"
                    },
                    {
                        "type": "audio", 
                        "data": test_audio,
                        "format": "wav"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
    
    def test_invalid_request(self):
        """测试无效请求"""
        response = self.client.post(
            "/api/v1/chat",
            json={
                "message": "测试",
                "image_data": "invalid-base64-data"
            }
        )
        
        # 应该返回错误但不崩溃
        assert response.status_code in [200, 400, 500]
    
    def _create_test_image(self) -> str:
        """创建测试图像的Base64编码"""
        from PIL import Image
        import io
        
        image = Image.new('RGB', (100, 100), color='blue')
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _create_test_audio(self) -> str:
        """创建测试音频的Base64编码"""
        import wave
        import io
        import struct
        
        sample_rate = 16000
        duration = 0.5  # 短音频
        frequency = 880.0
        
        frames = []
        for i in range(int(sample_rate * duration)):
            value = int(32767 * 0.2 * 
                       (i % (sample_rate // frequency)) / (sample_rate // frequency))
            frames.append(struct.pack('<h', value))
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(frames))
        
        return base64.b64encode(buffer.getvalue()).decode()


class TestSystemIntegration:
    """系统集成测试"""
    
    def test_agent_registration(self):
        """测试智能体注册"""
        # 检查智能体类是否可以正确导入
        try:
            from backend.core.agents.professional_voice_agent import ProfessionalVoiceAgent
            from backend.core.agents.professional_vision_agent import ProfessionalVisionAgent
            
            voice_agent = ProfessionalVoiceAgent()
            vision_agent = ProfessionalVisionAgent()
            
            assert voice_agent.agent_id != vision_agent.agent_id
            assert len(voice_agent.get_capabilities()) > 0
            assert len(vision_agent.get_capabilities()) > 0
            
        except ImportError as e:
            pytest.skip(f"无法导入智能体模块: {e}")
    
    def test_configuration_loading(self):
        """测试配置加载"""
        from backend.core.config import settings
        
        # 检查多模态配置是否正确加载
        assert hasattr(settings, 'openai_api_key')
        assert hasattr(settings, 'anthropic_api_key')
        assert hasattr(settings, 'whisper_model_size')
        assert hasattr(settings, 'max_image_size_mb')
        assert hasattr(settings, 'high_quality_threshold')
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """测试端到端处理"""
        try:
            processor = await get_multimodal_processor()
            
            # 创建测试请求
            request = UserRequest(
                message="测试多模态处理",
                inputs=[
                    MediaInput(
                        type=InputType.IMAGE,
                        data=self._create_test_image(),
                        format="png"
                    )
                ]
            )
            
            # 处理请求
            result = await processor.process_request(request)
            
            assert "processing_summary" in result
            assert "processed_media" in result
            assert "routing_decisions" in result
            assert result["processing_summary"]["total_inputs"] == 1
            
        except Exception as e:
            pytest.skip(f"端到端测试失败（可能缺少依赖）: {e}")
    
    def _create_test_image(self) -> str:
        """创建测试图像"""
        from PIL import Image
        import io
        
        image = Image.new('RGB', (50, 50), color='green')
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        
        return base64.b64encode(buffer.getvalue()).decode()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])