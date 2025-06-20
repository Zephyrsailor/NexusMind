from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import uuid
from typing import Dict
import logging
from datetime import datetime
from pydantic import BaseModel

from ..core.config import settings
from ..core.orchestrator import NexusMindOrchestrator
from ..core.context_manager import ContextManager
from ..models.schemas import UserRequest, TaskResponse, TaskStatus
from ..utils.a2a_client import A2AClient

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="NexusMind 多智能体协作系统",
    debug=settings.debug
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
orchestrator = None
active_connections: Dict[str, WebSocket] = {}
context_manager = None


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global orchestrator, context_manager
    
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    
    # 初始化 Orchestrator
    orchestrator = NexusMindOrchestrator()
    await orchestrator.initialize()
    
    # 获取上下文管理器
    context_manager = orchestrator.context_manager
    
    logger.info("NexusMind 系统已启动")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("正在关闭应用...")
    
    # 关闭所有WebSocket连接
    for connection in active_connections.values():
        await connection.close()
    
    # 清理orchestrator资源
    if orchestrator:
        await orchestrator.cleanup()
    
    logger.info("应用已安全关闭")


# ==================== 核心 API ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "NexusMind智能体平台",
        "version": "1.0.0", 
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    audio_data: str = None
    image_data: str = None
    metadata: dict = {}


@app.post("/api/v1/chat", response_model=TaskResponse)
async def chat(request: ChatRequest):
    """
    主要聊天接口 - 所有请求的统一入口
    
    请求格式:
    {
        "message": "用户消息",
        "audio_data": "base64音频数据（可选）",
        "image_data": "base64图像数据（可选）",
        "metadata": {}
    }
    
    响应格式:
    {
        "task_id": "任务ID",
        "status": "processing|completed|failed",
        "message": "状态说明",
        "payload": {
            "reply_message": "AI回复",
            "details": {}
        }
    }
    """
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="系统正在初始化")
        
        # 构建统一的用户请求
        user_request = UserRequest(
            message=request.message,
            audio_data=request.audio_data,
            image_data=request.image_data,
            metadata=request.metadata
        )
        
        # 通过 Orchestrator 处理（LLM Function Calling）
        response = await orchestrator.process_request(user_request)
        
        return response
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}", exc_info=True)
        return TaskResponse(
            task_id=str(uuid.uuid4()),
            status=TaskStatus.FAILED,
            message="处理失败",
            payload={
                "reply_message": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "error": str(e)
            }
        )


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if not context_manager:
        raise HTTPException(status_code=503, detail="系统未初始化")
    
    try:
        # 获取任务上下文
        task_context = await context_manager.get_task_context(task_id)
        if not task_context:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取任务摘要
        summary = await context_manager.get_task_summary(task_id)
        
        return {
            "task_id": task_id,
            "summary": summary,
            "context": task_context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket ====================

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 聊天接口"""
    await websocket.accept()
    client_id = f"ws_{uuid.uuid4().hex[:8]}"
    active_connections[client_id] = websocket
    
    logger.info(f"WebSocket客户端 {client_id} 已连接")
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "连接成功"
        })
        
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 构建请求
            chat_request = ChatRequest(**message_data)
            
            # 发送处理中状态
            task_id = str(uuid.uuid4())
            await websocket.send_json({
                "type": "processing",
                "task_id": task_id
            })
            
            # 处理请求
            user_request = UserRequest(
                message=chat_request.message,
                audio_data=chat_request.audio_data,
                image_data=chat_request.image_data,
                metadata=chat_request.metadata
            )
            
            response = await orchestrator.process_request(user_request)
            
            # 发送结果
            await websocket.send_json({
                "type": "result",
                "task_id": task_id,
                "status": response.status,
                "reply": response.payload.get("reply_message", ""),
                "details": response.payload
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket客户端 {client_id} 已断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        if client_id in active_connections:
            del active_connections[client_id]


# ==================== 监控 API ====================

@app.get("/api/v1/status")
async def get_system_status():
    """获取系统状态"""
    return {
        "status": "running",
        "orchestrator": {
            "ready": orchestrator is not None,
            "model": settings.llm_model
        },
        "connections": {
            "websocket": len(active_connections)
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/agents")
async def list_agents():
    """列出所有智能体"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="系统未初始化")
    
    # 获取内置智能体信息
    agent_info = []
    if orchestrator and orchestrator.agent_manager:
        agent_info = orchestrator.agent_manager.get_agent_info()
    
    return {
        "count": len(agent_info),
        "agents": agent_info
    }


# ==================== 开发/调试 API ====================

@app.get("/api/v1/debug/config")
async def get_debug_config():
    """获取系统配置（仅在调试模式下可用）"""
    if not settings.debug:
        raise HTTPException(status_code=403, detail="仅在调试模式下可用")
    
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "redis_url": settings.redis_url,
        "rabbitmq_url": settings.rabbitmq_url
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )