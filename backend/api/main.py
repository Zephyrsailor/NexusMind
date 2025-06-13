from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import uuid
from typing import Dict
import logging

from ..core.config import settings
from ..core.orchestrator import SimpleOrchestrator
from ..models.schemas import UserRequest, TaskResponse, TaskStatus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="NexusMind智能体平台",
    version="1.0.0",
    description="基于语音和视觉的智能体协调平台",
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
orchestrator = SimpleOrchestrator()
active_connections: Dict[str, WebSocket] = {}


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 启动NexusMind智能体平台")
    logger.info("正在初始化协调器...")
    await orchestrator.initialize()
    logger.info("✅ 系统启动完成")


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
        "service": "NexusMind智能体平台",
        "version": "1.0.0", 
        "status": "running",
        "message": "🧠 NexusMind智能协调服务运行正常",
        "features": ["语音录制与识别", "摄像头拍照与分析", "智能决策协调"]
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "NexusMind",
        "version": "1.0.0",
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
            "message": f"🎉 欢迎连接到NexusMind！客户端ID: {client_id}",
            "features": {
                "audio": "语音录制与识别",
                "camera": "摄像头拍照与分析",
                "status": "设备状态查询"
            },
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
            "message": "🔄 正在处理您的请求...",
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
            "message": f"❌ 处理请求时发生错误: {str(e)}"
        })


@app.get("/api/v1/status")
async def get_system_status():
    """获取系统状态"""
    try:
        # 获取Agent状态
        from ..core.audio_agent import AudioAgent
        from ..core.camera_agent import CameraAgent
        
        audio_agent = AudioAgent()
        camera_agent = CameraAgent()
        
        audio_status = await audio_agent.get_status()
        camera_status = await camera_agent.get_status()
        
        return {
            "orchestrator": {
                "status": "running",
                "type": "SimpleOrchestrator"
            },
            "agents": {
                "audio": audio_status,
                "camera": camera_status
            },
            "connections": {
                "active_websocket_connections": len(active_connections),
                "client_ids": list(active_connections.keys())
            },
            "system_ready": any([
                audio_status.get("status") == "ready",
                camera_status.get("status") == "ready"
            ])
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return {
            "error": str(e),
            "status": "error"
        }


@app.post("/api/v1/agents/test")
async def test_agents():
    """测试Agent功能"""
    test_results = {}
    
    try:
        # 测试语音Agent状态
        audio_request = UserRequest(message="设备状态")
        audio_response = await orchestrator.process_request(audio_request)
        test_results["audio_status"] = {
            "status": audio_response.status,
            "result": audio_response.payload
        }
        
        # 测试摄像头Agent状态
        camera_request = UserRequest(message="摄像头状态")
        camera_response = await orchestrator.process_request(camera_request)
        test_results["camera_status"] = {
            "status": camera_response.status,
            "result": camera_response.payload
        }
        
        return {
            "message": "Agent测试完成",
            "results": test_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent测试失败: {str(e)}")


@app.post("/api/v1/audio/record")
async def record_audio(duration: int = 5):
    """录音接口"""
    try:
        request = UserRequest(message=f"录音{duration}秒")
        response = await orchestrator.process_request(request)
        return response.payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"录音失败: {str(e)}")


@app.post("/api/v1/camera/capture")
async def capture_image():
    """拍照接口"""
    try:
        request = UserRequest(message="拍照")
        response = await orchestrator.process_request(request)
        return response.payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"拍照失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )