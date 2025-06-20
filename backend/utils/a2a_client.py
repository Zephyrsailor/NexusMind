"""
A2A (Agent-to-Agent) Protocol Client
基于Google A2A协议的智能体间通信客户端
"""
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import redis.asyncio as aioredis
import aio_pika
from ..models.schemas import A2AMessage, A2AResponse
from ..core.config import get_settings
from ..core.context_manager import ContextManager
from .retry_utils import async_retry, RetryError
from .validation import DataValidator, ValidationError

settings = get_settings()
logger = logging.getLogger(__name__)


class A2AClient:
    """A2A协议客户端，管理智能体间的通信"""
    
    def __init__(self):
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self.redis_client = None
        self.message_handlers: Dict[str, Callable] = {}
        self.context_manager: Optional[ContextManager] = None
        
    @async_retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError, TimeoutError))
    async def initialize(self):
        """
        初始化连接
        
        使用重试机制确保连接的可靠性
        
        Raises:
            RetryError: 多次重试后仍然失败
        """
        try:
            # 连接RabbitMQ
            self.rabbitmq_connection = await aio_pika.connect_robust(
                f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@"
                f"{settings.rabbitmq_host}:{settings.rabbitmq_port}/"
            )
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            
            # 设置channel的QoS
            await self.rabbitmq_channel.set_qos(prefetch_count=10)
            
            # 声明A2A交换机
            self.a2a_exchange = await self.rabbitmq_channel.declare_exchange(
                settings.a2a_exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # 连接Redis
            self.redis_client = await aioredis.from_url(
                f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=False,
                max_connections=10
            )
            
            # 初始化上下文管理器
            self.context_manager = ContextManager(self.redis_client)
            
            logger.info("[A2A-CLIENT] ✔ A2A客户端初始化成功")
            logger.info(f"[A2A-CLIENT] RabbitMQ: {settings.rabbitmq_host}:{settings.rabbitmq_port}")
            logger.info(f"[A2A-CLIENT] Redis: {settings.redis_host}:{settings.redis_port}")
            logger.info(f"[A2A-CLIENT] Exchange: {settings.a2a_exchange_name}")
            
        except Exception as e:
            logger.error(f"[A2A-CLIENT] ✖ A2A客户端初始化失败: {e}")
            raise
        
    async def close(self):
        """关闭连接"""
        if self.rabbitmq_connection:
            await self.rabbitmq_connection.close()
        if self.redis_client:
            await self.redis_client.close()
            
    async def register_agent(self, agent_card: Dict[str, Any]) -> bool:
        """
        注册智能体能力
        
        agent_card应包含:
        - agent_id: 唯一标识符
        - name: 智能体名称
        - description: 功能描述
        - capabilities: 能力列表
        - input_schema: 输入模式
        - output_schema: 输出模式
        
        Args:
            agent_card: 智能体卡片信息
            
        Returns:
            bool: 注册是否成功
            
        Raises:
            ValidationError: 智能体卡片格式无效
        """
        try:
            # 验证必需字段
            validator = DataValidator()
            validator.validate_required(agent_card, ["agent_id", "name", "capabilities"])
            
            agent_id = agent_card["agent_id"]
            
            # 验证agent_id格式
            validator.validate_string_length(agent_id, "agent_id", min_length=3, max_length=50)
            
            # 保存到内存注册表
            self.agent_registry[agent_id] = agent_card
            
            # 保存到Redis以便其他服务发现
            await self.redis_client.hset(
                "nexusmind:agents",
                agent_id,
                json.dumps(agent_card)
            )
            
            # 为该智能体创建专用队列
            queue = await self.rabbitmq_channel.declare_queue(
                f"nexusmind.agent.{agent_id}",
                durable=True,
                arguments={
                    "x-message-ttl": 3600000,  # 消息TTL: 1小时
                    "x-max-length": 1000  # 最大队列长度
                }
            )
            
            # 绑定到A2A交换机
            await queue.bind(
                self.a2a_exchange,
                routing_key=f"agent.{agent_id}"
            )
            
            logger.info(f"[A2A-CLIENT] ✔ Agent '{agent_id}' 注册成功")
            logger.info(f"[A2A-CLIENT] Queue: nexusmind.agent.{agent_id}")
            logger.info(f"[A2A-CLIENT] Routing Key: agent.{agent_id}")
            return True
            
        except (ValidationError, Exception) as e:
            logger.error(f"[A2A-CLIENT] ✖ Agent注册失败: {e}")
            return False
        
    async def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            await self.redis_client.hdel("nexusmind:agents", agent_id)
            
    async def discover_agents(self) -> Dict[str, Dict[str, Any]]:
        """发现所有可用的智能体"""
        # 从Redis获取所有注册的智能体
        agents_data = await self.redis_client.hgetall("nexusmind:agents")
        agents = {}
        
        for agent_id, agent_json in agents_data.items():
            agent_id = agent_id.decode('utf-8')
            agents[agent_id] = json.loads(agent_json.decode('utf-8'))
            
        return agents
        
    async def send_message(
        self,
        message: A2AMessage,
        timeout: Optional[int] = 30
    ) -> Optional[A2AResponse]:
        """
        发送A2A消息并等待响应
        
        Args:
            message: A2A消息
            timeout: 超时时间（秒）
            
        Returns:
            A2AResponse 或 None（超时）
        """
        logger.info(f"\n[A2A-CLIENT] ====== 发送A2A消息 ======")
        logger.info(f"[A2A-CLIENT] Message ID: {message.message_id}")
        logger.info(f"[A2A-CLIENT] Sender: {message.sender} -> Target: {message.target}")
        logger.info(f"[A2A-CLIENT] Action: {message.action}")
        logger.info(f"[A2A-CLIENT] Task ID: {message.task_id}")
        # 创建响应队列
        response_queue = await self.rabbitmq_channel.declare_queue(
            f"response.{message.message_id}",
            exclusive=True,
            auto_delete=True
        )
        
        # 发送消息
        # 将message转换为dict并处理datetime
        message_dict = message.model_dump()
        if hasattr(message_dict.get('timestamp'), 'isoformat'):
            message_dict['timestamp'] = message_dict['timestamp'].isoformat()
        elif message_dict.get('timestamp'):
            message_dict['timestamp'] = str(message_dict['timestamp'])
        
        logger.info(f"[A2A-CLIENT] 正在发布消息到队列: agent.{message.target}")
        logger.info(f"[A2A-CLIENT] 超时设置: {timeout}秒")
        
        await self.a2a_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_dict).encode(),
                reply_to=response_queue.name,
                correlation_id=message.message_id,
                expiration=int(timeout * 1000)  # 使用整数，不是字符串
            ),
            routing_key=f"agent.{message.target}"
        )
        
        logger.info(f"[A2A-CLIENT] ✔ 消息已发布到RabbitMQ")
        
        # 等待响应
        logger.info(f"[A2A-CLIENT] 等待响应中...")
        try:
            async with asyncio.timeout(timeout):
                async for message in response_queue:
                    response_data = json.loads(message.body.decode())
                    logger.info(f"[A2A-CLIENT] ✔ 收到响应")
                    logger.info(f"[A2A-CLIENT] Response Status: {response_data.get('status')}")
                    logger.info(f"[A2A-CLIENT] Response Data Keys: {list(response_data.get('data', {}).keys())}")
                    await message.ack()
                    return A2AResponse(**response_data)
        except asyncio.TimeoutError:
            logger.warning(f"[A2A-CLIENT] ⚠ 等待响应超时 ({timeout}秒)")
            return None
        finally:
            try:
                await response_queue.delete()
            except Exception as e:
                logger.warning(f"Failed to delete response queue: {e}")
            
    async def broadcast_message(self, message: A2AMessage):
        """广播消息给所有智能体"""
        await self.a2a_exchange.publish(
            aio_pika.Message(
                body=message.json().encode(),
                correlation_id=message.message_id
            ),
            routing_key="agent.*"
        )
        
    async def subscribe_to_agent(
        self,
        agent_id: str,
        handler: Callable[[A2AMessage], None]
    ):
        """订阅特定智能体的消息"""
        queue = await self.rabbitmq_channel.declare_queue(
            f"subscriber.{agent_id}.{id(handler)}",
            exclusive=True,
            auto_delete=True
        )
        
        await queue.bind(
            self.a2a_exchange,
            routing_key=f"agent.{agent_id}.broadcast"
        )
        
        self.message_handlers[queue.name] = handler
        
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                a2a_message = A2AMessage(**json.loads(message.body.decode()))
                await handler(a2a_message)
                
        await queue.consume(process_message)
        
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """获取智能体状态"""
        status_key = f"nexusmind:agent_status:{agent_id}"
        status_data = await self.redis_client.get(status_key)
        
        if status_data:
            return json.loads(status_data.decode('utf-8'))
        else:
            return {
                "agent_id": agent_id,
                "status": "unknown",
                "last_seen": None
            }
            
    async def update_agent_status(
        self,
        agent_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """更新智能体状态"""
        status_data = {
            "agent_id": agent_id,
            "status": status,
            "last_seen": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        status_key = f"nexusmind:agent_status:{agent_id}"
        await self.redis_client.setex(
            status_key,
            300,  # 5分钟过期
            json.dumps(status_data)
        )
        
    async def get_all_agent_statuses(self) -> List[Dict[str, Any]]:
        """获取所有智能体状态"""
        agents = await self.discover_agents()
        statuses = []
        
        for agent_id in agents:
            status = await self.get_agent_status(agent_id)
            statuses.append(status)
            
        return statuses