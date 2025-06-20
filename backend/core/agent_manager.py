"""
内置智能体管理器
管理系统内置的智能体，使它们作为内部服务运行
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .agents.voice_agent import VoiceAgent
from .agents.vision_agent import VisionAgent
from ..models.schemas import A2AMessage, A2AResponse

logger = logging.getLogger(__name__)


class InternalAgentManager:
    """内置智能体管理器"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self._running = False
        
    async def initialize(self):
        """初始化所有内置智能体"""
        logger.info("初始化内置智能体管理器...")
        
        # 创建内置智能体
        voice_agent = VoiceAgent()
        vision_agent = VisionAgent()
        
        # 注册智能体
        self.agents["voice_interaction_agent"] = voice_agent
        self.agents["vision_capture_agent"] = vision_agent
        
        # 为每个智能体创建消息队列
        for agent_id in self.agents:
            self.message_queues[agent_id] = asyncio.Queue()
            
        # 启动智能体
        self._running = True
        for agent_id, agent in self.agents.items():
            # 初始化智能体（但不连接外部服务）
            agent.a2a_client = None  # 不使用外部A2A
            agent.context_manager = None  # 使用共享的context manager
            
            # 启动消息处理任务
            task = asyncio.create_task(self._run_agent(agent_id, agent))
            self.tasks[agent_id] = task
            
        logger.info(f"已启动 {len(self.agents)} 个内置智能体")
        
    async def _run_agent(self, agent_id: str, agent):
        """运行单个智能体的消息处理循环"""
        logger.info(f"启动智能体 {agent_id} 的内部服务")
        
        while self._running:
            try:
                # 从队列获取消息
                message = await self.message_queues[agent_id].get()
                
                # 处理消息
                logger.debug(f"智能体 {agent_id} 处理消息: {message.action}")
                response = await agent.process_request(message)
                
                # 如果有回调队列，发送响应
                if hasattr(message, '_callback') and message._callback is not None:
                    try:
                        if asyncio.iscoroutinefunction(message._callback):
                            await message._callback(response)
                        else:
                            message._callback(response)
                    except asyncio.InvalidStateError:
                        # Future 已经被取消或完成，忽略
                        logger.debug(f"响应 Future 已失效，忽略响应")
                    except Exception as e:
                        logger.error(f"发送响应时出错: {e}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"智能体 {agent_id} 处理消息时出错: {e}", exc_info=True)
                
    async def send_message(self, agent_id: str, message: A2AMessage) -> Optional[A2AResponse]:
        """发送消息给内置智能体"""
        if agent_id not in self.agents:
            logger.error(f"未找到智能体: {agent_id}")
            return None
            
        # 创建响应Future
        response_future = asyncio.Future()
        
        # 添加回调到消息，检查 Future 状态
        def safe_callback(resp):
            if not response_future.done():
                response_future.set_result(resp)
            else:
                logger.debug(f"响应 Future 已完成，忽略迟到的响应")
        
        message._callback = safe_callback
        
        # 将消息放入队列
        await self.message_queues[agent_id].put(message)
        
        # 等待响应（带超时）
        try:
            # 根据不同的智能体设置不同的超时时间
            timeout_map = {
                "vision_capture_agent": 120.0,  # 视觉分析需要更长时间
                "voice_interaction_agent": 60.0
            }
            timeout = timeout_map.get(agent_id, 30.0)
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.error(f"等待智能体 {agent_id} 响应超时")
            # 标记消息已超时，避免后续处理
            message._callback = None
            return A2AResponse(
                correlation_id=message.message_id,
                sender=agent_id,
                status="failed",
                error="响应超时"
            )
            
    def get_agent_info(self) -> List[Dict[str, Any]]:
        """获取所有内置智能体信息"""
        info = []
        for agent_id, agent in self.agents.items():
            info.append({
                "agent_id": agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.get_capabilities(),
                "status": "online" if self._running else "offline"
            })
        return info
        
    async def cleanup(self):
        """清理资源"""
        logger.info("关闭内置智能体管理器...")
        self._running = False
        
        # 取消所有任务
        for task in self.tasks.values():
            task.cancel()
            
        # 等待任务结束
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        # 清理智能体资源
        for agent in self.agents.values():
            if hasattr(agent, 'cleanup'):
                await agent.cleanup()
                
        logger.info("内置智能体管理器已关闭")