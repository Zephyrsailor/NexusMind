"""
语音交互智能体
处理语音转文字、会议记录、语音命令等功能
"""
import asyncio
import base64
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import io
import wave
import numpy as np

# 语音识别相关
import speech_recognition as sr
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    WHISPER_AVAILABLE = False

from .base_agent import BaseAgent
from ...models.schemas import A2AMessage, A2AResponse, MediaInput, InputType
from ..multimodal_processor import get_multimodal_processor

logger = logging.getLogger(__name__)


class VoiceAgent(BaseAgent):
    """语音智能体"""
    
    def __init__(self):
        super().__init__(
            agent_id="voice_interaction_agent",
            name="语音交互智能体",
            description="处理语音输入、转录、会议记录和语音命令"
        )
        self.recognizer = sr.Recognizer()
        self.whisper_model = None
        self.meeting_sessions = {}  # 存储进行中的会议
        
    async def initialize(self):
        """初始化智能体"""
        await super().initialize()
        
        # 加载Whisper模型（用于高质量转录）
        if WHISPER_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model("base")
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load Whisper model: {e}")
        else:
            logger.warning("Whisper not available, using SpeechRecognition only")
            
    def get_capabilities(self) -> List[str]:
        """返回智能体能力列表"""
        return [
            "speech_to_text",           # 语音转文字
            "start_meeting_record",     # 开始会议记录
            "stop_meeting_record",      # 停止会议记录
            "get_meeting_transcript",   # 获取会议记录
            "voice_command",           # 语音命令识别
            "language_detection",      # 语言检测
            "speaker_diarization"      # 说话人分离（未来实现）
        ]
        
    def get_input_schema(self) -> Dict[str, Any]:
        """返回输入参数模式"""
        return {
            "action": {
                "type": "string",
                "enum": self.get_capabilities(),
                "description": "要执行的动作"
            },
            "audio_data": {
                "type": "string",
                "description": "Base64编码的音频数据（用于speech_to_text等）"
            },
            "audio_format": {
                "type": "string",
                "enum": ["wav", "mp3", "m4a", "flac"],
                "default": "wav",
                "description": "音频格式"
            },
            "session_id": {
                "type": "string",
                "description": "会议会话ID（用于会议记录）"
            },
            "language": {
                "type": "string",
                "default": "auto",
                "description": "语言代码（auto为自动检测）"
            },
            "options": {
                "type": "object",
                "description": "额外选项"
            }
        }
        
    def get_output_schema(self) -> Dict[str, Any]:
        """返回输出结果模式"""
        return {
            "text": {
                "type": "string",
                "description": "转录的文本"
            },
            "confidence": {
                "type": "number",
                "description": "置信度（0-1）"
            },
            "language": {
                "type": "string",
                "description": "检测到的语言"
            },
            "duration": {
                "type": "number",
                "description": "音频时长（秒）"
            },
            "session_id": {
                "type": "string",
                "description": "会议会话ID"
            },
            "transcript": {
                "type": "array",
                "description": "会议记录数组"
            },
            "metadata": {
                "type": "object",
                "description": "额外元数据"
            }
        }
        
    async def process_request(self, message: A2AMessage) -> A2AResponse:
        """处理语音请求"""
        logger.info(f"\n[VOICE_AGENT] {'='*60}")
        logger.info(f"[VOICE_AGENT] 收到A2A消息")
        logger.info(f"[VOICE_AGENT] Message ID: {message.message_id}")
        logger.info(f"[VOICE_AGENT] Sender: {message.sender}")
        logger.info(f"[VOICE_AGENT] Action: {message.action}")
        
        try:
            # action可能在message.action或payload.action中
            action = message.action or message.payload.get("action", "speech_recognition")
            task_id = message.payload.get("task_id", message.message_id)
            
            logger.info(f"[VOICE_AGENT] 处理动作: {action}")
            logger.info(f"[VOICE_AGENT] Task ID: {task_id}")
            
            # 记录活动
            logger.info(f"[VOICE_AGENT] 记录活动: request_received")
            await self.log_activity("request_received", {
                "action": action,
                "task_id": task_id
            })
            
            # 根据action处理请求
            logger.info(f"[VOICE_AGENT] 路由到具体处理函数")
            if action in ["speech_to_text", "speech_recognition"]:
                result = await self._handle_speech_to_text(message.payload, task_id)
            elif action == "start_recording":
                result = await self._handle_start_meeting(message.payload, task_id)
            elif action == "stop_recording":
                result = await self._handle_stop_meeting(message.payload, task_id)
            elif action == "voice_command":
                result = await self._handle_voice_command(message.payload, task_id)
            else:
                # 默认处理为语音转文字
                logger.info(f"[VOICE_AGENT] 未知action '{action}'，默认处理为语音转文字")
                result = await self._handle_speech_to_text(message.payload, task_id)
                
            response = A2AResponse(
                correlation_id=message.message_id,
                sender=self.agent_id,
                status="success",
                data=result,
                timestamp=datetime.now()  # 明确设置timestamp
            )
            
            logger.info(f"[VOICE_AGENT] 处理成功")
            logger.info(f"[VOICE_AGENT] 返回结果类型: {type(result)}")
            if isinstance(result, dict):
                logger.info(f"[VOICE_AGENT] 结果字段: {list(result.keys())}")
            logger.info(f"[VOICE_AGENT] {'='*60}\n")
            
            return response
            
        except Exception as e:
            logger.error(f"[VOICE_AGENT] 错误: {e}", exc_info=True)
            logger.info(f"[VOICE_AGENT] {'='*60}\n")
            return A2AResponse(
                correlation_id=message.message_id,
                sender=self.agent_id,
                status="failed",
                error=str(e)
            )
            
    async def _handle_speech_to_text(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理语音转文字"""
        logger.info(f"[VOICE_AGENT] 开始处理语音转文字")
        
        audio_data = payload.get("audio_data")
        audio_format = payload.get("audio_format", "wav")
        language = payload.get("language", "zh")  # 默认使用中文
        
        if not audio_data:
            raise ValueError("No audio data provided")
            
        logger.info(f"[VOICE_AGENT] 音频数据 - 格式: {audio_format}, 大小: {len(audio_data) if audio_data else 0} bytes")
        logger.info(f"[VOICE_AGENT] 语言设置: {language}")
            
        # 解码音频数据
        audio_bytes = base64.b64decode(audio_data)
        
        # 使用多模态处理器
        try:
            logger.info(f"[VOICE_AGENT] 使用多模态处理器进行语音识别")
            
            # 创建 MediaInput 对象
            media_input = MediaInput(
                type=InputType.AUDIO,
                data=audio_data,
                format=audio_format,
                metadata={"language": language}
            )
            
            # 获取多模态处理器
            processor = await get_multimodal_processor()
            
            # 分析媒体
            analysis = await processor._analyze_media(media_input)
            
            # 预处理
            processed = await processor._preprocess_media(media_input, analysis)
            
            if processed.success and processed.processed_data:
                # 执行 AI 分析
                ai_result = await processor._perform_ai_analysis(media_input, processed.processed_data)
                
                if ai_result and ai_result.get("type") == "speech_recognition":
                    text = ai_result.get("text", "")
                    confidence = ai_result.get("confidence", 0.95)
                    detected_lang = language
                    logger.info(f"[VOICE_AGENT] AI 语音识别成功: '{text[:100]}...'")
                else:
                    raise Exception("AI 语音识别失败")
            else:
                raise Exception(f"预处理失败: {processed.error}")
                
        except Exception as e:
            logger.warning(f"[VOICE_AGENT] 多模态处理器失败: {e}，尝试备用方案")
            
            # 使用备用方案
            if self.whisper_model:
                logger.info(f"[VOICE_AGENT] 使用本地Whisper模型进行转录")
                text, confidence, detected_lang = await self._transcribe_with_whisper(
                    audio_bytes, language
                )
            else:
                # 退回到speech_recognition
                logger.info(f"[VOICE_AGENT] 使用SpeechRecognition进行转录")
                text, confidence, detected_lang = await self._transcribe_with_sr(
                    audio_bytes, audio_format, language
                )
        
        logger.info(f"[VOICE_AGENT] 转录结果: '{text[:100]}...' (置信度: {confidence})")
            
        # 共享转录结果到上下文
        logger.info(f"[VOICE_AGENT] 共享转录结果到上下文")
        await self.share_context(task_id, {
            "transcription": text,
            "confidence": confidence,
            "language": detected_lang,
            "timestamp": datetime.now().isoformat()
        })
        
        # 记录活动
        await self.log_activity("transcription_completed", {
            "task_id": task_id,
            "text_length": len(text),
            "confidence": confidence
        })
        
        result = {
            "text": text,
            "confidence": confidence,
            "language": detected_lang,
            "metadata": {
                "engine": "whisper" if self.whisper_model else "speech_recognition",
                "task_id": task_id
            }
        }
        
        logger.info(f"[VOICE_AGENT] 语音转文字完成")
        return result
        
    async def _handle_start_meeting(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """开始会议记录"""
        session_id = payload.get("session_id") or f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建会议会话
        self.meeting_sessions[session_id] = {
            "session_id": session_id,
            "start_time": datetime.now(),
            "transcript": [],
            "participants": set(),
            "task_id": task_id
        }
        
        # 共享会议开始状态
        await self.share_context(task_id, {
            "meeting_started": True,
            "session_id": session_id,
            "start_time": datetime.now().isoformat()
        })
        
        logger.info(f"Started meeting recording: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "recording",
            "start_time": datetime.now().isoformat()
        }
        
    async def _handle_stop_meeting(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """停止会议记录"""
        session_id = payload.get("session_id")
        
        if not session_id or session_id not in self.meeting_sessions:
            raise ValueError(f"Meeting session not found: {session_id}")
            
        session = self.meeting_sessions[session_id]
        session["end_time"] = datetime.now()
        
        # 计算会议时长
        duration = (session["end_time"] - session["start_time"]).total_seconds()
        
        # 生成会议摘要
        transcript = session["transcript"]
        
        # 共享完整会议记录
        await self.share_context(task_id, {
            "meeting_ended": True,
            "session_id": session_id,
            "duration": duration,
            "transcript": transcript,
            "end_time": datetime.now().isoformat()
        })
        
        # 清理会话
        del self.meeting_sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": "completed",
            "duration": duration,
            "transcript_count": len(transcript)
        }
        
    async def _handle_get_transcript(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """获取会议记录"""
        session_id = payload.get("session_id")
        
        # 检查进行中的会议
        if session_id in self.meeting_sessions:
            session = self.meeting_sessions[session_id]
            return {
                "session_id": session_id,
                "status": "recording",
                "transcript": session["transcript"],
                "duration": (datetime.now() - session["start_time"]).total_seconds()
            }
            
        # 从共享上下文获取已结束的会议
        meeting_context = await self.get_shared_context(task_id, self.agent_id)
        if meeting_context and meeting_context.get("session_id") == session_id:
            return {
                "session_id": session_id,
                "status": "completed",
                "transcript": meeting_context.get("transcript", [])
            }
            
        raise ValueError(f"Meeting session not found: {session_id}")
        
    async def _handle_voice_command(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理语音命令"""
        # 先转录语音
        transcription_result = await self._handle_speech_to_text(payload, task_id)
        text = transcription_result["text"]
        
        # 识别命令意图
        command = await self._parse_voice_command(text)
        
        return {
            "text": text,
            "command": command,
            "confidence": transcription_result["confidence"]
        }
        
    async def _handle_language_detection(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """检测语音语言"""
        audio_data = payload.get("audio_data")
        
        if not audio_data:
            raise ValueError("No audio data provided")
            
        # 使用Whisper检测语言
        if self.whisper_model:
            audio_bytes = base64.b64decode(audio_data)
            # 这里简化处理，实际需要完整实现
            detected_lang = "zh"  # 示例
            confidence = 0.95
        else:
            detected_lang = "unknown"
            confidence = 0.0
            
        return {
            "language": detected_lang,
            "confidence": confidence
        }
        
    async def _transcribe_with_whisper(
        self,
        audio_bytes: bytes,
        language: str
    ) -> tuple[str, float, str]:
        """使用Whisper进行转录"""
        # 将音频保存为临时文件（Whisper需要文件路径）
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name
            
        try:
            # 使用Whisper转录
            if language == "auto":
                result = self.whisper_model.transcribe(tmp_file_path)
            else:
                result = self.whisper_model.transcribe(tmp_file_path, language=language)
                
            text = result["text"]
            # Whisper没有直接的置信度，使用概率估算
            confidence = 0.95 if text else 0.0
            detected_lang = result.get("language", language)
            
            return text, confidence, detected_lang
            
        finally:
            # 清理临时文件
            import os
            os.unlink(tmp_file_path)
            
    async def _transcribe_with_sr(
        self,
        audio_bytes: bytes,
        audio_format: str,
        language: str
    ) -> tuple[str, float, str]:
        """使用speech_recognition进行转录"""
        # 转换音频格式为WAV（speech_recognition需要）
        audio_file = io.BytesIO(audio_bytes)
        
        try:
            # 使用speech_recognition
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
                
            # 尝试使用Google Speech Recognition
            try:
                if language == "auto":
                    text = self.recognizer.recognize_google(audio)
                    detected_lang = "auto"
                else:
                    text = self.recognizer.recognize_google(audio, language=language)
                    detected_lang = language
                    
                confidence = 0.8  # Google不提供置信度，使用默认值
                
            except sr.UnknownValueError:
                text = ""
                confidence = 0.0
                detected_lang = "unknown"
                
            return text, confidence, detected_lang
            
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            return "", 0.0, "error"
            
    async def _parse_voice_command(self, text: str) -> Dict[str, Any]:
        """解析语音命令"""
        # 简单的命令识别逻辑
        text_lower = text.lower()
        
        commands = {
            "开始会议": {"action": "start_meeting", "type": "control"},
            "结束会议": {"action": "stop_meeting", "type": "control"},
            "记录这个": {"action": "bookmark", "type": "annotation"},
            "重要": {"action": "mark_important", "type": "annotation"}
        }
        
        for keyword, command in commands.items():
            if keyword in text_lower:
                return command
                
        # 默认返回
        return {"action": "unknown", "type": "text", "original": text}
        
    async def add_to_meeting_transcript(
        self,
        session_id: str,
        text: str,
        speaker: Optional[str] = None,
        confidence: float = 1.0
    ):
        """添加内容到会议记录"""
        if session_id not in self.meeting_sessions:
            raise ValueError(f"Meeting session not found: {session_id}")
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "speaker": speaker or "Unknown",
            "confidence": confidence
        }
        
        self.meeting_sessions[session_id]["transcript"].append(entry)
        
        # 如果识别到参与者
        if speaker:
            self.meeting_sessions[session_id]["participants"].add(speaker)