"""
基础智能体接口
所有专业智能体都应继承此类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import json
import logging
from datetime import datetime
import aio_pika
from ...models.schemas import A2AMessage, A2AResponse
from ...utils.a2a_client import A2AClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """基础智能体抽象类"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.a2a_client: Optional[A2AClient] = None
        self.running = False
        self._tasks: List[asyncio.Task] = []
        
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """返回智能体能力列表"""
        pass
        
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """返回输入参数模式"""
        pass
        
    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """返回输出结果模式"""
        pass
        
    @abstractmethod
    async def process_request(self, message: A2AMessage) -> A2AResponse:
        """
        处理请求的核心方法
        
        Args:
            message: A2A消息
            
        Returns:
            A2AResponse: 处理结果
        """
        pass
        
    def get_agent_card(self) -> Dict[str, Any]:
        """获取智能体卡片（用于注册）"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.get_capabilities(),
            "input_schema": self.get_input_schema(),
            "output_schema": self.get_output_schema(),
            "version": "1.0.0",
            "protocol": "a2a/1.0"
        }
        
    async def initialize(self):
        """初始化智能体"""
        self.a2a_client = A2AClient()
        await self.a2a_client.initialize()
        
        # 注册智能体
        success = await self.a2a_client.register_agent(self.get_agent_card())
        if success:
            logger.info(f"Agent {self.agent_id} registered successfully")
        else:
            logger.error(f"Failed to register agent {self.agent_id}")
            
        # 更新状态为online
        await self.a2a_client.update_agent_status(
            self.agent_id,
            "online",
            {"started_at": datetime.now().isoformat()}
        )
        
    async def shutdown(self):
        """关闭智能体"""
        self.running = False
        
        # 取消所有任务
        for task in self._tasks:
            if not task.done():
                task.cancel()
                
        # 等待任务结束
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        # 更新状态为offline
        if self.a2a_client:
            await self.a2a_client.update_agent_status(
                self.agent_id,
                "offline",
                {"stopped_at": datetime.now().isoformat()}
            )
            
            # 注销智能体
            await self.a2a_client.unregister_agent(self.agent_id)
            await self.a2a_client.close()
            
    async def start(self):
        """启动智能体服务"""
        self.running = True
        
        try:
            # 初始化
            await self.initialize()
            
            # 启动消息处理循环
            message_task = asyncio.create_task(self._message_loop())
            self._tasks.append(message_task)
            
            # 启动心跳
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._tasks.append(heartbeat_task)
            
            logger.info(f"Agent {self.agent_id} started")
            
            # 等待任务完成
            await asyncio.gather(*self._tasks)
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} error: {e}")
            raise
        finally:
            await self.shutdown()
            
    async def _message_loop(self):
        """消息处理循环"""
        # 连接到RabbitMQ
        connection = await aio_pika.connect_robust(
            "amqp://nexusmind:nexusmind123@localhost:5672/"
        )
        channel = await connection.channel()
        
        # 声明队列，匹配现有队列参数
        queue = await channel.declare_queue(
            f"nexusmind.agent.{self.agent_id}",
            durable=True,
            arguments={
                "x-message-ttl": 3600000,  # 1小时TTL
                "x-max-length": 1000  # 最大消息数量
            }
        )
        
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    # 解析消息
                    message_data = json.loads(message.body.decode())
                    logger.info(f"Received message data: {message_data}")
                    logger.info(f"Message correlation_id: {message.correlation_id}")
                    logger.info(f"Message expiration: {getattr(message, 'expiration', 'None')}")
                    
                    # 处理timestamp字段
                    if isinstance(message_data.get('timestamp'), str):
                        from datetime import datetime
                        try:
                            # 处理各种时间戳格式
                            timestamp_str = message_data['timestamp']
                            if timestamp_str.isdigit():
                                # 如果是纯数字，可能是毫秒时间戳
                                timestamp_ms = int(timestamp_str)
                                if timestamp_ms > 1000000000000:  # 毫秒时间戳
                                    message_data['timestamp'] = datetime.fromtimestamp(timestamp_ms / 1000)
                                else:  # 秒时间戳
                                    message_data['timestamp'] = datetime.fromtimestamp(timestamp_ms)
                            else:
                                # 尝试解析ISO格式的时间戳
                                timestamp_str = timestamp_str.replace('Z', '+00:00')
                                message_data['timestamp'] = datetime.fromisoformat(timestamp_str)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid timestamp format: {message_data['timestamp']}, error: {e}")
                            # 如果不是有效的时间戳格式，使用当前时间
                            message_data['timestamp'] = datetime.now()
                    elif isinstance(message_data.get('timestamp'), (int, float)):
                        # 处理数字时间戳
                        timestamp_num = message_data['timestamp']
                        if timestamp_num > 1000000000000:  # 毫秒时间戳
                            message_data['timestamp'] = datetime.fromtimestamp(timestamp_num / 1000)
                        else:  # 秒时间戳
                            message_data['timestamp'] = datetime.fromtimestamp(timestamp_num)
                    elif message_data.get('timestamp') is None:
                        message_data['timestamp'] = datetime.now()
                    
                    try:
                        a2a_message = A2AMessage(**message_data)
                        logger.info(f"Successfully created A2AMessage: {a2a_message.model_dump()}")
                    except Exception as create_error:
                        logger.error(f"Failed to create A2AMessage: {create_error}")
                        logger.error(f"Message data causing error: {message_data}")
                        raise create_error
                    
                    # 更新状态为processing
                    await self.a2a_client.update_agent_status(
                        self.agent_id,
                        "processing",
                        {"current_task": a2a_message.message_id}
                    )
                    
                    # 处理请求
                    response = await self.process_request(a2a_message)
                    
                    # 发送响应
                    if message.reply_to:
                        # 处理datetime序列化
                        response_dict = response.model_dump()
                        response_dict['timestamp'] = response_dict['timestamp'].isoformat() if hasattr(response_dict.get('timestamp'), 'isoformat') else str(response_dict.get('timestamp'))
                        
                        await channel.default_exchange.publish(
                            aio_pika.Message(
                                body=json.dumps(response_dict).encode(),
                                correlation_id=message.correlation_id
                            ),
                            routing_key=message.reply_to
                        )
                        
                    # 更新状态为online
                    await self.a2a_client.update_agent_status(
                        self.agent_id,
                        "online"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
                    # 发送错误响应
                    if message.reply_to:
                        error_response = A2AResponse(
                            correlation_id=message.correlation_id or "unknown",
                            sender=self.agent_id,
                            success=False,
                            error=str(e),
                            timestamp=datetime.now()
                        )
                        # 处理datetime序列化
                        error_dict = error_response.model_dump()
                        error_dict['timestamp'] = error_dict['timestamp'].isoformat() if hasattr(error_dict.get('timestamp'), 'isoformat') else str(error_dict.get('timestamp'))
                        
                        await channel.default_exchange.publish(
                            aio_pika.Message(
                                body=json.dumps(error_dict).encode(),
                                correlation_id=message.correlation_id
                            ),
                            routing_key=message.reply_to
                        )
                        
        # 开始消费消息
        await queue.consume(process_message)
        
        # 保持运行
        while self.running:
            await asyncio.sleep(1)
            
        await connection.close()
        
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                # 更新心跳
                await self.a2a_client.update_agent_status(
                    self.agent_id,
                    "online",
                    {"heartbeat": datetime.now().isoformat()}
                )
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                
            # 每30秒一次心跳
            await asyncio.sleep(30)
            
    async def share_context(self, task_id: str, context: Dict[str, Any]):
        """共享上下文给其他智能体"""
        if self.a2a_client and hasattr(self.a2a_client, 'context_manager'):
            await self.a2a_client.context_manager.share_context(
                task_id,
                self.agent_id,
                context
            )
        elif self.a2a_client and self.a2a_client.redis_client:
            # 退回到直接Redis操作
            key = f"nexusmind:context:{task_id}:{self.agent_id}"
            context_with_meta = {
                **context,
                "_metadata": {
                    "agent_id": self.agent_id,
                    "task_id": task_id,
                    "shared_at": datetime.now().isoformat()
                }
            }
            await self.a2a_client.redis_client.setex(
                key,
                3600,  # 1小时过期
                json.dumps(context_with_meta)
            )
            
    async def get_shared_context(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        """获取其他智能体的共享上下文"""
        if self.a2a_client and hasattr(self.a2a_client, 'context_manager'):
            return await self.a2a_client.context_manager.get_shared_context(
                task_id,
                agent_id
            ) or {}
        elif self.a2a_client and self.a2a_client.redis_client:
            # 退回到直接Redis操作
            key = f"nexusmind:context:{task_id}:{agent_id}"
            data = await self.a2a_client.redis_client.get(key)
            if data:
                context = json.loads(data.decode('utf-8'))
                context.pop("_metadata", None)
                return context
        return {}
        
    async def log_activity(self, activity_type: str, details: Dict[str, Any]):
        """记录活动日志"""
        log_entry = {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "activity_type": activity_type,
            "details": details
        }
        
        if self.a2a_client and self.a2a_client.redis_client:
            # 添加到活动日志列表
            key = f"nexusmind:activity_log:{self.agent_id}"
            await self.a2a_client.redis_client.lpush(
                key,
                json.dumps(log_entry)
            )
            # 只保留最近1000条
            await self.a2a_client.redis_client.ltrim(key, 0, 999)