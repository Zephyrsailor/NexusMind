from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import asyncio
import uuid
from typing import Dict
import logging

from ..core.config import settings
from ..core.orchestrator import NexusMindOrchestrator
from ..models.schemas import UserRequest, TaskResponse, TaskStatus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="NexusMind智能体联邦平台 - 核心协调服务",
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
orchestrator = NexusMindOrchestrator()
active_connections: Dict[str, WebSocket] = {}


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    logger.info("核心协调器已初始化")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("正在关闭应用...")
    # 关闭所有WebSocket连接
    for connection in active_connections.values():
        await connection.close()


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "message": "NexusMind核心协调服务运行正常"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "orchestrator": "ready"
    }


@app.post("/api/v1/process", response_model=TaskResponse)
async def process_request(request: UserRequest):
    """同步处理用户请求"""
    try:
        logger.info(f"收到用户请求: {request.message}")
        
        # 处理请求
        response = await orchestrator.process_request(request)
        
        logger.info(f"请求处理完成，任务ID: {response.task_id}")
        return response
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接端点，支持实时通信"""
    await websocket.accept()
    active_connections[client_id] = websocket
    
    logger.info(f"WebSocket客户端 {client_id} 已连接")
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connection",
            "message": f"欢迎连接到NexusMind！客户端ID: {client_id}",
            "timestamp": str(asyncio.get_event_loop().time())
        })
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            logger.info(f"收到WebSocket消息: {message_data}")
            
            # 处理不同类型的消息
            if message_data.get("type") == "user_request":
                await handle_user_request_ws(websocket, message_data, client_id)
            elif message_data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": str(asyncio.get_event_loop().time())})
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知消息类型: {message_data.get('type')}"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket客户端 {client_id} 已断开连接")
        if client_id in active_connections:
            del active_connections[client_id]
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
        await websocket.close()
        if client_id in active_connections:
            del active_connections[client_id]


async def handle_user_request_ws(websocket: WebSocket, message_data: dict, client_id: str):
    """处理WebSocket用户请求"""
    try:
        # 解析用户请求
        user_request = UserRequest(**message_data.get("payload", {}))
        
        # 立即发送处理开始通知
        task_id = str(uuid.uuid4())
        await websocket.send_json({
            "type": "task_started",
            "task_id": task_id,
            "message": "正在处理您的请求...",
            "status": TaskStatus.PROCESSING
        })
        
        # 异步处理请求
        response = await orchestrator.process_request(user_request)
        response.task_id = task_id  # 使用预生成的任务ID
        
        # 发送最终结果
        await websocket.send_json({
            "type": "task_completed",
            "task_id": response.task_id,
            "status": response.status,
            "message": response.message,
            "payload": response.payload
        })
        
    except Exception as e:
        logger.error(f"处理WebSocket请求时发生错误: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": f"处理请求时发生错误: {str(e)}"
        })


@app.get("/api/v1/status")
async def get_system_status():
    """获取系统状态"""
    return {
        "orchestrator": {
            "status": "running",
            "tools_count": len(orchestrator.tools),
            "tools": [tool.name for tool in orchestrator.tools]
        },
        "connections": {
            "active_websocket_connections": len(active_connections),
            "client_ids": list(active_connections.keys())
        },
        "config": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "max_concurrent_tasks": settings.max_concurrent_tasks
        }
    }


@app.post("/api/v1/tools/test")
async def test_tools():
    """测试本地工具功能"""
    test_results = {}
    
    try:
        # 测试计算器
        calc_request = UserRequest(message="计算 2 + 3 * 4")
        calc_response = await orchestrator.process_request(calc_request)
        test_results["calculator"] = {
            "status": calc_response.status,
            "result": calc_response.payload
        }
        
        # 测试文本解析器
        text_request = UserRequest(message="请分析这段文本：Hello world! 这是一个测试。联系邮箱：test@example.com")
        text_response = await orchestrator.process_request(text_request)
        test_results["text_parser"] = {
            "status": text_response.status,
            "result": text_response.payload
        }
        
        return {
            "message": "工具测试完成",
            "results": test_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工具测试失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )