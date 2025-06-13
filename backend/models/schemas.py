from typing import Dict, Any, Optional, List
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


class UserRequest(BaseModel):
    """用户请求模型"""
    message: str = Field(..., description="用户输入的文本消息")
    image_data: Optional[str] = Field(None, description="Base64编码的图像数据")
    audio_data: Optional[str] = Field(None, description="Base64编码的音频数据")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    status: TaskStatus
    message: str
    payload: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class A2AMessage(BaseModel):
    """A2A协议消息模型"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = Field(..., description="发送者标识")
    target: str = Field(..., description="目标智能体标识")
    action: str = Field(..., description="请求的动作")
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = Field(None, description="关联任务ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    reply_to: Optional[str] = Field(None, description="回复队列")


class A2AResponse(BaseModel):
    """A2A协议响应模型"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(..., description="原始消息ID")
    sender: str = Field(..., description="响应者标识")
    success: bool = Field(..., description="操作是否成功")
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentCapability(BaseModel):
    """智能体能力描述模型"""
    agent_id: str
    name: str
    description: str
    actions: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class TaskState(BaseModel):
    """任务状态跟踪模型"""
    task_id: str
    user_request: UserRequest
    status: TaskStatus
    current_step: str
    steps_completed: List[str] = Field(default_factory=list)
    intermediate_results: Dict[str, Any] = Field(default_factory=dict)
    final_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)