import asyncio
import uuid
import re
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from .audio_agent import AudioAgent
from .camera_agent import CameraAgent
from ..models.schemas import UserRequest, TaskResponse, TaskStatus

logger = logging.getLogger(__name__)


class SimpleOrchestrator:
    """简化版智能协调器"""
    
    def __init__(self):
        self.audio_agent = AudioAgent()
        self.camera_agent = CameraAgent()
        self.agents_initialized = False
        
    async def initialize(self):
        """初始化所有Agent"""
        if self.agents_initialized:
            return
            
        logger.info("正在初始化内置Agent...")
        
        # 初始化语音Agent
        audio_ok = await self.audio_agent.initialize()
        logger.info(f"语音Agent初始化: {'成功' if audio_ok else '失败'}")
        
        # 初始化摄像头Agent
        camera_ok = await self.camera_agent.initialize()
        logger.info(f"摄像头Agent初始化: {'成功' if camera_ok else '失败'}")
        
        self.agents_initialized = True
        
    async def process_request(self, user_request: UserRequest) -> TaskResponse:
        """处理用户请求"""
        task_id = str(uuid.uuid4())
        
        try:
            # 确保Agent已初始化
            await self.initialize()
            
            # 分析用户意图
            intent = await self._analyze_intent(user_request.message)
            
            # 执行相应操作
            result = await self._execute_action(intent, user_request)
            
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                message="处理完成",
                payload=result
            )
            
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                message=f"处理失败: {str(e)}"
            )
    
    async def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """分析用户意图（简单规则匹配）"""
        message_lower = message.lower()
        
        intent = {
            "type": "unknown",
            "confidence": 0.0,
            "params": {}
        }
        
        # 语音相关意图
        if any(keyword in message_lower for keyword in ['录音', '语音', '说话', '听', 'record', 'audio', 'speech']):
            intent["type"] = "audio"
            intent["confidence"] = 0.9
            
            # 提取录音时长
            duration_match = re.search(r'(\d+)[秒|分]', message)
            if duration_match:
                duration = int(duration_match.group(1))
                if '分' in message:
                    duration *= 60
                intent["params"]["duration"] = min(duration, 30)  # 最多30秒
            else:
                intent["params"]["duration"] = 5  # 默认5秒
                
            # 判断是否需要识别
            if any(keyword in message_lower for keyword in ['识别', '转换', '文字', 'recognize', 'stt']):
                intent["params"]["action"] = "record_and_recognize"
            else:
                intent["params"]["action"] = "record_audio"
        
        # 摄像头相关意图
        elif any(keyword in message_lower for keyword in ['拍照', '摄像', '照片', '图片', 'photo', 'camera', 'capture']):
            intent["type"] = "camera"
            intent["confidence"] = 0.9
            
            # 提取拍照数量
            count_match = re.search(r'(\d+)[张|次|个]', message)
            if count_match:
                count = int(count_match.group(1))
                intent["params"]["count"] = min(count, 10)  # 最多10张
            else:
                intent["params"]["count"] = 1
                
            # 判断是否需要分析
            if any(keyword in message_lower for keyword in ['分析', '检测', '识别', 'analyze', 'detect']):
                intent["params"]["action"] = "capture_and_analyze"
            elif intent["params"]["count"] > 1:
                intent["params"]["action"] = "capture_multiple"
            else:
                intent["params"]["action"] = "capture_image"
        
        # 状态查询
        elif any(keyword in message_lower for keyword in ['状态', '设备', '可用', 'status', 'device']):
            intent["type"] = "status"
            intent["confidence"] = 0.8
        
        # 基础对话
        else:
            intent["type"] = "chat"
            intent["confidence"] = 0.5
            
        logger.info(f"意图分析结果: {intent}")
        return intent
    
    async def _execute_action(self, intent: Dict[str, Any], user_request: UserRequest) -> Dict[str, Any]:
        """执行具体操作"""
        intent_type = intent["type"]
        params = intent.get("params", {})
        
        if intent_type == "audio":
            return await self._handle_audio_request(params)
            
        elif intent_type == "camera":
            return await self._handle_camera_request(params)
            
        elif intent_type == "status":
            return await self._handle_status_request()
            
        elif intent_type == "chat":
            return await self._handle_chat_request(user_request.message)
            
        else:
            return {
                "success": False,
                "message": f"暂不支持的请求类型: {intent_type}",
                "suggestion": "请尝试语音录制、拍照或查询设备状态"
            }
    
    async def _handle_audio_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理语音请求"""
        action = params.get("action", "record_audio")
        duration = params.get("duration", 5)
        
        try:
            if action == "record_and_recognize":
                result = await self.audio_agent.record_and_recognize(duration)
            else:
                result = await self.audio_agent.record_audio(duration)
                
            return {
                "success": result.get("success", False),
                "agent_type": "audio",
                "action": action,
                "result": result,
                "message": result.get("message", "语音处理完成")
            }
            
        except Exception as e:
            logger.error(f"语音处理失败: {e}")
            return {
                "success": False,
                "agent_type": "audio",
                "error": str(e),
                "message": "语音处理过程中发生错误"
            }
    
    async def _handle_camera_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理摄像头请求"""
        action = params.get("action", "capture_image")
        count = params.get("count", 1)
        
        try:
            if action == "capture_and_analyze":
                result = await self.camera_agent.capture_and_analyze()
            elif action == "capture_multiple":
                result = await self.camera_agent.capture_multiple(count)
            else:
                result = await self.camera_agent.capture_image()
                
            return {
                "success": result.get("success", False),
                "agent_type": "camera",
                "action": action,
                "result": result,
                "message": result.get("message", "图像处理完成")
            }
            
        except Exception as e:
            logger.error(f"摄像头处理失败: {e}")
            return {
                "success": False,
                "agent_type": "camera", 
                "error": str(e),
                "message": "图像处理过程中发生错误"
            }
    
    async def _handle_status_request(self) -> Dict[str, Any]:
        """处理状态查询请求"""
        try:
            audio_status = await self.audio_agent.get_status()
            camera_status = await self.camera_agent.get_status()
            
            return {
                "success": True,
                "agent_type": "system",
                "action": "status_check",
                "result": {
                    "audio_agent": audio_status,
                    "camera_agent": camera_status,
                    "system_ready": audio_status.get("status") == "ready" or camera_status.get("status") == "ready"
                },
                "message": "系统状态查询完成"
            }
            
        except Exception as e:
            logger.error(f"状态查询失败: {e}")
            return {
                "success": False,
                "agent_type": "system",
                "error": str(e),
                "message": "状态查询过程中发生错误"
            }
    
    async def _handle_chat_request(self, message: str) -> Dict[str, Any]:
        """处理基础对话请求"""
        responses = {
            "你好": "您好！我是NexusMind智能助手，可以帮您进行语音录制和图像拍摄。",
            "帮助": "我可以帮您：\n1. 语音录制和识别\n2. 拍照和图像分析\n3. 设备状态查询",
            "功能": "主要功能：\n• 录音：'请录音5秒'\n• 语音识别：'录音并识别'\n• 拍照：'请拍照'\n• 图像分析：'拍照并分析'\n• 状态查询：'设备状态'"
        }
        
        # 简单的关键词匹配
        for key, response in responses.items():
            if key in message:
                return {
                    "success": True,
                    "agent_type": "chat",
                    "action": "basic_chat",
                    "result": {"reply": response},
                    "message": response
                }
        
        return {
            "success": True,
            "agent_type": "chat", 
            "action": "basic_chat",
            "result": {
                "reply": f"我已收到您的消息：'{message}'。请告诉我您想要录音还是拍照？"
            },
            "message": "基础对话响应"
        }