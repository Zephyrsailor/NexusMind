import asyncio
import io
import wave
import tempfile
import os
from typing import Optional, Dict, Any
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import logging

logger = logging.getLogger(__name__)


class AudioAgent:
    """语音处理智能体"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_recording = False
        
    async def initialize(self) -> bool:
        """初始化音频设备"""
        try:
            # 检查麦克风
            mic_list = sr.Microphone.list_microphone_names()
            if not mic_list:
                logger.warning("未检测到麦克风设备")
                return False
                
            self.microphone = sr.Microphone()
            
            # 调整环境噪音
            with self.microphone as source:
                logger.info("正在调整环境噪音...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
            logger.info(f"语音Agent初始化成功，检测到 {len(mic_list)} 个音频设备")
            return True
            
        except Exception as e:
            logger.error(f"音频设备初始化失败: {e}")
            return False
    
    async def record_audio(self, duration: int = 5) -> Optional[Dict[str, Any]]:
        """录制音频"""
        if not self.microphone:
            await self.initialize()
            
        try:
            logger.info(f"开始录音 {duration} 秒...")
            
            with self.microphone as source:
                # 录制音频
                audio_data = self.recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
                
            # 转换为WAV格式
            wav_data = audio_data.get_wav_data()
            
            # 保存临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_path = temp_file.name
            
            # 获取音频信息
            audio_segment = AudioSegment.from_wav(temp_path)
            duration_ms = len(audio_segment)
            
            result = {
                "success": True,
                "file_path": temp_path,
                "duration_ms": duration_ms,
                "format": "wav",
                "sample_rate": audio_segment.frame_rate,
                "channels": audio_segment.channels,
                "message": f"录音完成，时长: {duration_ms/1000:.2f}秒"
            }
            
            logger.info(f"录音成功: {result['message']}")
            return result
            
        except sr.WaitTimeoutError:
            return {
                "success": False,
                "error": "录音超时，未检测到声音",
                "message": "请检查麦克风是否正常工作"
            }
        except Exception as e:
            logger.error(f"录音失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "录音过程中发生错误"
            }
    
    async def speech_to_text(self, audio_file_path: Optional[str] = None, audio_data: Optional[bytes] = None) -> Dict[str, Any]:
        """语音转文字"""
        try:
            if audio_file_path:
                # 从文件读取
                with sr.AudioFile(audio_file_path) as source:
                    audio = self.recognizer.record(source)
            elif audio_data:
                # 从字节数据读取
                audio = sr.AudioData(audio_data, 16000, 2)
            else:
                return {
                    "success": False,
                    "error": "需要提供音频文件路径或音频数据",
                    "message": "语音识别失败"
                }
            
            # 使用Google语音识别（免费）
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            
            result = {
                "success": True,
                "text": text,
                "message": f"识别成功: {text}"
            }
            
            logger.info(f"语音识别成功: {text}")
            return result
            
        except sr.UnknownValueError:
            return {
                "success": False,
                "error": "无法识别语音内容",
                "message": "请说话清晰一些或检查音频质量"
            }
        except sr.RequestError as e:
            return {
                "success": False,
                "error": f"语音识别服务错误: {e}",
                "message": "语音识别服务暂时不可用"
            }
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "语音识别过程中发生错误"
            }
    
    async def text_to_speech(self, text: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """文字转语音（简单实现）"""
        try:
            # 这里可以集成更好的TTS服务，目前返回提示信息
            logger.info(f"TTS请求: {text}")
            
            result = {
                "success": True,
                "text": text,
                "message": f"TTS功能准备就绪，文本: {text}",
                "note": "可以集成Azure TTS、百度语音等服务"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "语音合成过程中发生错误"
            }
    
    async def record_and_recognize(self, duration: int = 5) -> Dict[str, Any]:
        """录音并识别（一键操作）"""
        # 先录音
        record_result = await self.record_audio(duration)
        
        if not record_result.get("success"):
            return record_result
        
        # 再识别
        recognition_result = await self.speech_to_text(record_result["file_path"])
        
        # 清理临时文件
        try:
            os.unlink(record_result["file_path"])
        except:
            pass
        
        # 合并结果
        result = {
            "success": recognition_result.get("success", False),
            "text": recognition_result.get("text", ""),
            "recording_info": {
                "duration_ms": record_result.get("duration_ms", 0),
                "format": record_result.get("format", "unknown")
            },
            "message": recognition_result.get("message", "处理完成")
        }
        
        if recognition_result.get("error"):
            result["error"] = recognition_result["error"]
        
        return result
    
    async def get_status(self) -> Dict[str, Any]:
        """获取语音Agent状态"""
        mic_available = self.microphone is not None
        
        if not mic_available:
            mic_available = await self.initialize()
        
        return {
            "agent_type": "audio",
            "status": "ready" if mic_available else "error",
            "microphone_available": mic_available,
            "microphone_count": len(sr.Microphone.list_microphone_names()) if mic_available else 0,
            "supported_actions": [
                "record_audio",
                "speech_to_text", 
                "text_to_speech",
                "record_and_recognize"
            ]
        }