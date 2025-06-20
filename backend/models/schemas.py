"""
数据模型定义
"""
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InputType(str, Enum):
    """输入类型枚举"""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    STREAM = "stream"


class MediaInput(BaseModel):
    """媒体输入模型"""
    type: InputType
    data: Optional[str] = Field(None, description="Base64编码的数据（小文件）")
    url: Optional[str] = Field(None, description="媒体URL（大文件）")
    format: Optional[str] = Field(None, description="媒体格式，如wav, mp3, jpg, png")
    duration: Optional[float] = Field(None, description="时长（秒），用于音频/视频")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserRequest(BaseModel):
    """用户请求模型 - 支持多种输入类型"""
    message: str = Field(..., description="用户消息文本")
    inputs: List[MediaInput] = Field(default_factory=list, description="附加的媒体输入")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # 向后兼容字段（建议使用inputs）
    audio_data: Optional[str] = Field(None, description="[已废弃] 使用inputs代替")
    image_data: Optional[str] = Field(None, description="[已废弃] 使用inputs代替")
    metadata: Optional[Dict[str, Any]] = Field(None, description="[已废弃] 使用context代替")
    
    def __init__(self, **data):
        """处理向后兼容"""
        # 转换旧格式到新格式
        if 'audio_data' in data and data['audio_data']:
            if 'inputs' not in data:
                data['inputs'] = []
            data['inputs'].append({
                'type': InputType.AUDIO,
                'data': data['audio_data'],
                'format': 'wav'
            })
        
        if 'image_data' in data and data['image_data']:
            if 'inputs' not in data:
                data['inputs'] = []
            data['inputs'].append({
                'type': InputType.IMAGE,
                'data': data['image_data'],
                'format': 'jpg'
            })
        
        # 合并metadata到context
        if 'metadata' in data and data['metadata']:
            if 'context' not in data:
                data['context'] = {}
            data['context'].update(data['metadata'])
        
        super().__init__(**data)


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 快捷访问字段
    @property
    def reply(self) -> Optional[str]:
        """获取AI回复"""
        return self.payload.get("reply_message", self.payload.get("reply"))


# A2A协议相关
class A2AMessage(BaseModel):
    """A2A协议消息模型"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = Field(..., description="发送者标识")
    target: str = Field(..., description="目标智能体标识")
    action: str = Field(..., description="请求的动作")
    payload: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = Field(None, description="任务ID")
    correlation_id: Optional[str] = Field(None, description="关联消息ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    reply_to: Optional[str] = Field(None, description="回复队列")


class A2AResponse(BaseModel):
    """A2A协议响应模型"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(..., description="原始消息ID")
    sender: str = Field(..., description="响应者标识")
    status: Literal["success", "failed", "processing"] = Field(..., description="执行状态")
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now)


# Agent相关
class AgentInfo(BaseModel):
    """智能体信息"""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    status: Literal["online", "offline", "busy"] = "offline"
    last_heartbeat: Optional[datetime] = None


class AgentCapability(BaseModel):
    """智能体能力描述"""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)