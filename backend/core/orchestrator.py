<<<<<<< HEAD
"""
NexusMind Orchestrator - 使用LLM Function Calling
改进版：包含工具注册表、系统提示词管理和更好的错误处理
"""

import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from redis import asyncio as aioredis
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import Tool
from langchain.schema import BaseMessage

from ..models.schemas import UserRequest, TaskResponse, TaskStatus, InputType
from ..core.config import settings
from ..utils.a2a_client import A2AClient
from ..core.context_manager import ContextManager
from ..core.agent_manager import InternalAgentManager

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表 - 集中管理所有工具定义"""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 语音转录工具
        self.register_tool(
            name="voice_transcription",
            description="将语音转录为文字。支持中英文等多种语言。",
            parameters={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "语言代码，如zh、en", "default": "zh"}
                },
                "required": []
            }
        )
        
        # 视觉分析工具
        self.register_tool(
            name="vision_analysis",
            description="分析图像内容，识别物体、场景等。如果用户没有提供图像数据，会自动触发拍照。",
            parameters={
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["general", "scene", "objects", "text"],
                        "description": "分析类型",
                        "default": "general"
                    }
                },
                "required": []
            }
        )
        
        # 拍照工具
        self.register_tool(
            name="capture_photo",
            description="当用户询问视觉相关问题但没有提供图像时（如'我手上拿的是什么'、'看看周围'），自动拍照并分析。",
            parameters={
                "type": "object",
                "properties": {
                    "purpose": {"type": "string", "description": "拍照的目的或用户的问题"}
                },
                "required": []
            }
        )
    
    def register_tool(self, name: str, description: str, parameters: Dict):
        """注册工具"""
        self.tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
    
    def get_tools(self) -> List[Dict]:
        """获取所有工具定义"""
        return list(self.tools.values())
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self.tools.keys())


class SystemPromptManager:
    """系统提示词管理器 - 灵活配置系统提示词"""
    
    def __init__(self):
        self.base_prompt = """你是NexusMind智能助手。你可以理解用户意图并调用合适的工具来完成任务。"""
        self.tool_instructions = {}
        self._load_default_instructions()
    
    def _load_default_instructions(self):
        """加载默认工具使用说明"""
        self.tool_instructions = {
            "voice": "当用户提到'语音'、'录音'、'转录'、'听写'等关键词，或提供音频数据时，使用语音转录工具。",
            "vision": "当用户提到'看'、'图片'、'图像'、'分析'、'识别'等关键词，或提供图像数据时，使用图像分析工具。",
            "photo": "重要：当用户询问需要视觉信息的问题但没有提供图像时，必须先调用capture_photo工具！例如：'我手上拿的是什么'、'看看周围'、'这是什么'、'房间里有什么'等。"
        }
    
    def build_system_prompt(self, available_tools: List[str]) -> str:
        """构建系统提示词"""
        prompt = self.base_prompt + "\n\n"
        
        # 添加工具使用说明
        prompt += "工具使用指南：\n"
        for category, instruction in self.tool_instructions.items():
            prompt += f"- {instruction}\n"
        
        # 添加重要规则
        prompt += "\n重要规则：\n"
        prompt += "1. 仔细理解用户意图，选择合适的工具\n"
        prompt += "2. 如果用户提供了媒体数据，优先处理这些数据\n"
        prompt += "3. 当用户询问需要视觉信息但没提供图像时，必须调用capture_photo工具！\n"
        prompt += "4. 基于工具调用结果，给出详细、有用的答案来完整回答用户问题\n"
        prompt += "5. 对于视觉分析结果，要综合描述看到的内容，不要只说物品名称\n"
        prompt += "6. 回复要详细、准确、有帮助，让用户获得完整的信息\n"
        prompt += "7. 如果无法完成任务，明确说明原因和建议\n"
        
        # 列出可用工具
        prompt += f"\n可用工具：{', '.join(available_tools)}"
        
        return prompt


class NexusMindOrchestrator:
    """改进版协调器 - 集成了工具注册表和系统提示词管理"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.tool_registry = ToolRegistry()
        self.prompt_manager = SystemPromptManager()
        self.a2a_client = None
        self.context_manager = None
        self.redis_client = None
        self.agent_manager = None
        self.tool_handlers = {}
        self._register_tool_handlers()
        
    async def initialize(self):
        """初始化"""
        # Redis
        self.redis_client = await aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
            decode_responses=False
        )
        
        # A2A客户端
        self.a2a_client = A2AClient()
        await self.a2a_client.initialize()
        
        # 上下文管理器
        self.context_manager = ContextManager(self.redis_client)
        
        # 内置智能体管理器
        self.agent_manager = InternalAgentManager()
        await self.agent_manager.initialize()
        
        logger.info("Orchestrator initialized with improved architecture")
    
    def _initialize_llm(self):
        """初始化LLM"""
        return ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens
        )
    
    def _register_tool_handlers(self):
        """注册工具处理器"""
        self.tool_handlers = {
            "voice_transcription": self._handle_voice_transcription,
            "vision_analysis": self._handle_vision_analysis,
            "capture_photo": self._handle_capture_photo
        }
    
    async def process_request(self, request: UserRequest) -> TaskResponse:
        """处理用户请求"""
        task_id = str(uuid.uuid4())
        logger.info(f"\n{'='*80}")
        logger.info(f"[ORCHESTRATOR] 开始处理请求 - Task ID: {task_id}")
        logger.info(f"[ORCHESTRATOR] 用户消息: {request.message}")
        logger.info(f"[ORCHESTRATOR] 输入类型: {[inp.type for inp in request.inputs] if request.inputs else 'None'}")
        logger.info(f"[ORCHESTRATOR] 音频数据: {'Yes' if request.audio_data else 'No'} ({len(request.audio_data) if request.audio_data else 0} chars)")
        logger.info(f"[ORCHESTRATOR] 图像数据: {'Yes' if request.image_data else 'No'} ({len(request.image_data) if request.image_data else 0} chars)")
        
        try:
            # 1. 准备上下文
            context = await self._prepare_context(request, task_id)
            
            # 2. 向新输入格式转换（向后兼容）
            converted_request = self._convert_legacy_inputs(request)
            
            # 3. 准备数据供工具调用
            self._current_request_data = {
                "audio_data": converted_request.audio_data,
                "image_data": converted_request.image_data,
                "inputs": converted_request.inputs
            }
            
            # 4. 构建消息
            messages = self._build_messages(converted_request, context)
            
            # 5. 调用LLM
            response = await self._call_llm_with_tools(messages)
            
            # 6. 处理响应
            result = await self._process_llm_response(response, task_id, converted_request.message)
            
            logger.info(f"[ORCHESTRATOR] 完整响应: {result.payload.get('reply_message', '')}")
            logger.info(f"{'='*80}\n")
            return result
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] 处理失败: {e}", exc_info=True)
=======
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
>>>>>>> 01cf403c2b0a835be223e934a41fb7845c50ec97
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                message=f"处理失败: {str(e)}",
                payload={"error": str(e)}
            )
    
<<<<<<< HEAD
    def _convert_legacy_inputs(self, request: UserRequest) -> UserRequest:
        """转换旧格式输入为新格式（向后兼容）"""
        return request  # 暂时直接返回，后续可扩展
    
    async def _prepare_context(self, request: UserRequest, task_id: str) -> Dict[str, Any]:
        """准备上下文信息"""
        context = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "has_audio": bool(request.audio_data or any(inp.type == InputType.AUDIO for inp in request.inputs)),
            "has_image": bool(request.image_data or any(inp.type == InputType.IMAGE for inp in request.inputs)),
            "has_video": any(inp.type == InputType.VIDEO for inp in request.inputs) if request.inputs else False,
            "input_types": [inp.type.value for inp in request.inputs] if request.inputs else []
        }
        
        logger.info(f"[ORCHESTRATOR] 上下文: {json.dumps(context, ensure_ascii=False)}")
        return context
    
    def _build_messages(self, request: UserRequest, context: Dict[str, Any]) -> List[BaseMessage]:
        """构建消息列表"""
        # 系统消息
        available_tools = self.tool_registry.get_tool_names()
        system_prompt = self.prompt_manager.build_system_prompt(available_tools)
        system_msg = SystemMessage(content=system_prompt)
        
        # 用户消息
        user_content = request.message
        
        # 添加上下文提示
        if context["has_audio"]:
            user_content += " [包含音频数据]"
        if context["has_image"]:
            user_content += " [包含图像数据]"
        if context["has_video"]:
            user_content += " [包含视频数据]"
        
        user_msg = HumanMessage(content=user_content)
        
        return [system_msg, user_msg]
    
    async def _call_llm_with_tools(self, messages: List[BaseMessage]) -> AIMessage:
        """调用LLM并处理工具"""
        tools = self.tool_registry.get_tools()
        logger.info(f"[ORCHESTRATOR] 可用工具: {self.tool_registry.get_tool_names()}")
        
        # 绑定工具
        llm_with_tools = self.llm.bind(tools=tools)
        
        # 调用LLM
        response = await llm_with_tools.ainvoke(messages)
        
        # 添加详细日志
        logger.info(f"[ORCHESTRATOR] LLM响应类型: {type(response)}")
        logger.info(f"[ORCHESTRATOR] LLM响应内容: {response.content}")
        logger.info(f"[ORCHESTRATOR] LLM工具调用: {response.additional_kwargs.get('tool_calls', [])}")
        
        return response
    
    async def _process_llm_response(self, response: AIMessage, task_id: str, original_message: str = "") -> TaskResponse:
        """处理LLM响应"""
        # 检查工具调用
        if hasattr(response, 'additional_kwargs') and 'tool_calls' in response.additional_kwargs:
            tool_calls = response.additional_kwargs['tool_calls']
            logger.info(f"[ORCHESTRATOR] 检测到 {len(tool_calls)} 个工具调用")
            
            # 执行工具调用
            tool_results = []
            for tool_call in tool_calls:
                result = await self._execute_tool_call(tool_call, task_id)
                tool_results.append(result)
            
            # 如果有工具调用结果，检查是否包含特殊指令
            if tool_results:
                combined_tool_result = "\n\n".join(tool_results)
                
                # 检查是否包含拍照请求指令
                for result in tool_results:
                    if self._is_special_action(result):
                        # 直接返回特殊指令，不让LLM处理
                        return TaskResponse(
                            task_id=task_id,
                            status=TaskStatus.COMPLETED,
                            message="需要用户操作",
                            payload={"reply_message": result}
                        )
                
                # 正常工具结果：让LLM基于结果生成最终回答
                system_msg = SystemMessage(content="请基于工具调用的结果简洁地回答用户的问题。如果用户问'手上拿的是什么'，请只回答具体的物品名称。")
                user_msg = HumanMessage(content=f"用户问题：{original_message}\n\n工具分析结果：{combined_tool_result}\n\n请简洁回答用户的问题：")
                
                # 调用LLM生成最终回答
                final_response = await self.llm.ainvoke([system_msg, user_msg])
                final_answer = final_response.content
                
                if not final_answer:
                    final_answer = combined_tool_result
                
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    message="分析完成",
                    payload={"reply_message": final_answer}
                )
        
        # 直接文本回复
        content = response.content
        
        # 确保有内容
        if not content:
            logger.warning("[ORCHESTRATOR] LLM返回空内容，使用默认回复")
            content = "抱歉，我理解了您的请求，但暂时无法提供具体的回复。请问还有什么其他可以帮助您的吗？"
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            message="请求已处理",
            payload={
                "reply_message": content,
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _is_special_action(self, result: str) -> bool:
        """检查工具结果是否包含特殊指令（如拍照请求）"""
        try:
            if result.startswith('{') and '"action"' in result:
                data = json.loads(result)
                return data.get("action") == "request_photo_capture"
        except:
            pass
        return False
    
    async def _execute_tool_call(self, tool_call: Dict, task_id: str) -> str:
        """执行单个工具调用"""
        function_name = tool_call['function']['name']
        function_args = json.loads(tool_call['function']['arguments'])
        
        logger.info(f"[ORCHESTRATOR] 执行工具: {function_name}")
        logger.info(f"[ORCHESTRATOR] 参数: {json.dumps(function_args, ensure_ascii=False)[:200]}")
        
        # 获取对应的处理器
        handler = self.tool_handlers.get(function_name)
        if handler:
            return await handler(function_args, task_id)
        else:
            logger.error(f"[ORCHESTRATOR] 未找到工具处理器: {function_name}")
            return f"工具 {function_name} 暂未实现"
    
    # 工具处理器实现
    
    async def _handle_voice_transcription(self, args: Dict, task_id: str) -> str:
        """处理语音转录请求"""
        try:
            # 使用内置的voice_interaction_agent
            from ..models.schemas import A2AMessage
            
            # 获取音频数据：优先使用参数中的，然后使用当前请求中的
            audio_data = args.get("audio_data") or getattr(self, '_current_request_data', {}).get("audio_data", "")
            
            if not audio_data:
                return "未找到音频数据，请提供音频输入。"
            
            message = A2AMessage(
                sender="orchestrator",
                target="voice_interaction_agent",
                action="speech_to_text",
                payload={
                    "audio_data": audio_data,
                    "audio_format": "wav",
                    "language": args.get("language", "zh"),
                    "task_id": task_id
                }
            )
            
            response = await self.agent_manager.send_message("voice_interaction_agent", message)
            
            if response and response.status == "success":
                data = response.data
                if isinstance(data, dict) and "text" in data:
                    return f"识别结果：{data['text']}"
                else:
                    return f"语音处理完成：{str(data)}"
            else:
                error = response.error if response else "未知错误"
                return f"语音识别失败: {error}"
                
        except Exception as e:
            logger.error(f"语音处理异常: {e}", exc_info=True)
            return f"语音处理出错: {str(e)}"
    
    async def _handle_vision_analysis(self, args: Dict, task_id: str) -> str:
        """处理视觉分析请求"""
        try:
            from ..models.schemas import A2AMessage
            
            # 获取图像数据：优先使用参数中的，然后使用当前请求中的
            image_data = args.get("image_data") or getattr(self, '_current_request_data', {}).get("image_data", "")
            
            # 检查是否为占位符文本或无效数据
            placeholder_texts = [
                "包含图像数据", "[包含图像数据]", "图像数据", "image_data", 
                "base64_image_data", "placeholder", "占位符"
            ]
            
            is_placeholder = False
            if image_data:
                # 检查是否为占位符
                is_placeholder = any(placeholder in image_data.lower() for placeholder in [p.lower() for p in placeholder_texts])
                # 检查长度是否太短（真实base64图像数据通常很长）
                if len(image_data) < 100:
                    is_placeholder = True
            
            if not image_data or is_placeholder:
                # 返回拍照请求指令
                return json.dumps({
                    "action": "request_photo_capture",
                    "purpose": "进行图像分析",
                    "message": "需要图像数据来进行分析，正在自动拍照..."
                })
            
            # 映射分析类型到具体的action
            analysis_type = args.get("analysis_type", "general")
            action_map = {
                "general": "scene_analysis",
                "scene": "scene_analysis",
                "objects": "object_detection",
                "text": "ocr",
                "artistic": "scene_analysis"
            }
            
            message = A2AMessage(
                sender="orchestrator",
                target="vision_capture_agent",
                action=action_map.get(analysis_type, "scene_analysis"),
                payload={
                    "image_data": image_data,
                    "task_id": task_id
                }
            )
            
            response = await self.agent_manager.send_message("vision_capture_agent", message)
            
            if response and response.status == "success":
                return self._format_vision_response(response.data)
            else:
                error = response.error if response else "未知错误"
                return f"图像分析失败: {error}"
                
        except Exception as e:
            logger.error(f"视觉处理异常: {e}", exc_info=True)
            return f"图像处理出错: {str(e)}"
    
    async def _handle_capture_photo(self, args: Dict, task_id: str) -> str:
        """处理拍照请求"""
        purpose = args.get("purpose", "回答用户问题")
        
        # 返回特殊指令，让客户端识别并自动拍照
        return json.dumps({
            "action": "request_photo_capture", 
            "purpose": purpose,
            "message": f"正在自动拍照来{purpose}..."
        })
    
    def _format_agent_response(self, agent_name: str, data: Any) -> str:
        """格式化智能体响应"""
        if isinstance(data, dict):
            if "text" in data:
                return f"{data['text']}"
            elif "description" in data:
                return f"{data['description']}"
            elif "summary" in data:
                return f"{data['summary']}"
            else:
                return f"{agent_name}处理完成"
        else:
            return str(data)
    
    def _format_vision_response(self, data: Dict) -> str:
        """格式化视觉响应"""
        if "analysis" in data:
            return data['analysis']
        elif "scene" in data:
            scene = data["scene"]
            # 优先返回 AI 生成的描述
            if "description" in scene:
                return scene["description"]
            # 否则返回基础分析
            elif "analysis_type" in scene:
                return f"这是一张{scene.get('complexity', '普通')}的图片"
            else:
                return "图像分析完成"
        elif "detections" in data:
            detections = data["detections"]
            analysis_type = data.get("analysis_type", "basic_detection")
            
            if analysis_type == "ai_generated" and detections:
                # AI 分析结果，返回描述
                first_detection = detections[0]
                if "description" in first_detection:
                    return first_detection["description"]
            
            # 基础检测结果
            count = len(detections)
            if count == 0:
                return "未检测到明显的物体"
            elif count == 1:
                return "检测到 1 个物体"
            else:
                return f"检测到 {count} 个物体"
        elif "text" in data:
            return f"识别到文字：{data['text']}"
        else:
            return "图像分析完成"
    
    async def cleanup(self):
        """清理资源"""
        if self.agent_manager:
            await self.agent_manager.cleanup()
        if self.a2a_client:
            await self.a2a_client.close()
        if self.redis_client:
            await self.redis_client.close()
=======
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
>>>>>>> 01cf403c2b0a835be223e934a41fb7845c50ec97
