"""
核心工具集
包含orchestrator用于调用A2A智能体的工具
"""
import json
import asyncio
import base64
import re
from typing import Dict, Any, Optional, List, Tuple
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import logging
from ..models.schemas import A2AMessage, A2AResponse
from ..utils.a2a_client import A2AClient

logger = logging.getLogger(__name__)


class AgentCallInput(BaseModel):
    """智能体调用输入模型"""
    agent_id: str = Field(..., description="目标智能体ID")
    action: str = Field(..., description="要执行的动作")
    payload: Dict[str, Any] = Field(default_factory=dict, description="传递给智能体的参数")
    task_id: Optional[str] = Field(None, description="任务ID")


class A2AAgentTool(BaseTool):
    """A2A智能体通信工具"""
    name: str = "call_agent"
    description: str = """调用专业智能体执行特定任务。
    可用的智能体:
    - voice_interaction_agent: 语音转文字、会议记录、语音命令
    - vision_capture_agent: 图像识别、OCR、人脸识别、场景分析
    """
    args_schema: type[BaseModel] = AgentCallInput
    a2a_client: Optional[A2AClient] = Field(default=None, exclude=True)
    
    def __init__(self, a2a_client: A2AClient, **data):
        super().__init__(**data)
        self.a2a_client = a2a_client
        
    def _run(self, agent_id: str, action: str, payload: Dict[str, Any], task_id: Optional[str] = None) -> str:
        """同步运行（实际调用异步方法）"""
        # LangChain要求同步方法，这里使用asyncio.run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._arun(agent_id, action, payload, task_id)
            )
            return result
        finally:
            loop.close()
            
    async def _arun(self, agent_id: str, action: str, payload: Dict[str, Any], task_id: Optional[str] = None) -> str:
        """异步调用智能体"""
        try:
            # 构建A2A消息
            message = A2AMessage(
                sender="orchestrator",
                target=agent_id,
                action=action,
                payload={
                    **payload,
                    "task_id": task_id or "default"
                }
            )
            
            logger.info(f"Calling agent {agent_id} with action {action}")
            
            # 发送消息并等待响应
            response = await self.a2a_client.send_message(message, timeout=30)
            
            if response and response.success:
                result = response.result
                return f"智能体{agent_id}执行成功: {json.dumps(result, ensure_ascii=False, indent=2)}"
            else:
                error = response.error if response else "超时无响应"
                return f"智能体{agent_id}执行失败: {error}"
                
        except Exception as e:
            logger.error(f"Error calling agent {agent_id}: {e}")
            return f"调用智能体出错: {str(e)}"


class AgentDiscoveryInput(BaseModel):
    """智能体发现输入模型"""
    capability: Optional[str] = Field(None, description="所需的能力（可选）")


class AgentDiscoveryTool(BaseTool):
    """智能体发现工具"""
    name: str = "discover_agents"
    description: str = "发现可用的智能体及其能力"
    args_schema: type[BaseModel] = AgentDiscoveryInput
    a2a_client: Optional[A2AClient] = Field(default=None, exclude=True)
    
    def __init__(self, a2a_client: A2AClient, **data):
        super().__init__(**data)
        self.a2a_client = a2a_client
        
    def _run(self, capability: Optional[str] = None) -> str:
        """同步运行"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._arun(capability)
            )
            return result
        finally:
            loop.close()
            
    async def _arun(self, capability: Optional[str] = None) -> str:
        """异步发现智能体"""
        try:
            # 获取所有注册的智能体
            agents = await self.a2a_client.discover_agents()
            
            if capability:
                # 过滤具有特定能力的智能体
                filtered_agents = {}
                for agent_id, agent_info in agents.items():
                    capabilities = agent_info.get("capabilities", [])
                    if capability in capabilities:
                        filtered_agents[agent_id] = agent_info
                agents = filtered_agents
                
            # 格式化输出
            if not agents:
                return "没有找到可用的智能体"
                
            result = "可用的智能体:\n"
            for agent_id, info in agents.items():
                result += f"\n- {info.get('name', agent_id)} ({agent_id})\n"
                result += f"  描述: {info.get('description', '无描述')}\n"
                result += f"  能力: {', '.join(info.get('capabilities', []))}\n"
                
            return result
            
        except Exception as e:
            logger.error(f"Error discovering agents: {e}")
            return f"发现智能体出错: {str(e)}"


class AgentStatusInput(BaseModel):
    """智能体状态查询输入模型"""
    agent_id: Optional[str] = Field(None, description="智能体ID（可选，不提供则返回所有）")


class AgentStatusTool(BaseTool):
    """智能体状态查询工具"""
    name: str = "check_agent_status"
    description: str = "查询智能体的运行状态"
    args_schema: type[BaseModel] = AgentStatusInput
    a2a_client: Optional[A2AClient] = Field(default=None, exclude=True)
    
    def __init__(self, a2a_client: A2AClient, **data):
        super().__init__(**data)
        self.a2a_client = a2a_client
        
    def _run(self, agent_id: Optional[str] = None) -> str:
        """同步运行"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._arun(agent_id)
            )
            return result
        finally:
            loop.close()
            
    async def _arun(self, agent_id: Optional[str] = None) -> str:
        """异步查询状态"""
        try:
            if agent_id:
                # 查询特定智能体状态
                status = await self.a2a_client.get_agent_status(agent_id)
                return f"{agent_id}状态: {json.dumps(status, ensure_ascii=False, indent=2)}"
            else:
                # 查询所有智能体状态
                statuses = await self.a2a_client.get_all_agent_statuses()
                
                result = "所有智能体状态:\n"
                for status in statuses:
                    agent_id = status.get("agent_id", "unknown")
                    state = status.get("status", "unknown")
                    last_seen = status.get("last_seen", "never")
                    result += f"\n- {agent_id}: {state} (最后活跃: {last_seen})\n"
                    
                return result
                
        except Exception as e:
            logger.error(f"Error checking agent status: {e}")
            return f"查询状态出错: {str(e)}"


def safe_base64_decode(data: str) -> Tuple[bytes, bool]:
    """
    安全地解码 base64 数据，处理各种格式和编码问题
    
    Args:
        data: 要解码的 base64 字符串
        
    Returns:
        Tuple[bytes, bool]: (解码后的字节数据, 是否成功)
    """
    try:
        # 移除可能的 data URL 前缀
        if data.startswith('data:'):
            # 查找 base64 数据的开始位置
            comma_index = data.find(',')
            if comma_index != -1:
                data = data[comma_index + 1:]
        
        # 移除所有空白字符
        data = ''.join(data.split())
        
        # 只保留 base64 有效字符
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        cleaned_data = ''.join(c for c in data if c in valid_chars)
        
        # 确保长度是4的倍数（base64 要求）
        while len(cleaned_data) % 4 != 0:
            cleaned_data += '='
            
        # 解码
        decoded_bytes = base64.b64decode(cleaned_data)
        return decoded_bytes, True
        
    except Exception as e:
        logger.error(f"Base64 解码失败: {e}")
        return b'', False


def clean_base64_data(data: str) -> str:
    """
    清理 base64 数据，移除前缀和非法字符
    
    Args:
        data: 原始 base64 字符串
        
    Returns:
        str: 清理后的 base64 字符串
    """
    # 移除可能的 data URL 前缀
    if data.startswith('data:'):
        # 查找 base64 数据的开始位置
        comma_index = data.find(',')
        if comma_index != -1:
            data = data[comma_index + 1:]
    
    # 移除所有空白字符
    data = ''.join(data.split())
    
    # 只保留 base64 有效字符
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    cleaned_data = ''.join(c for c in data if c in valid_chars)
    
    # 确保长度是4的倍数（base64 要求）
    while len(cleaned_data) % 4 != 0:
        cleaned_data += '='
        
    return cleaned_data