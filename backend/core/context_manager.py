"""
智能体间上下文共享管理器
实现智能体之间的上下文数据共享和管理
"""
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
import asyncio
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


class ContextManager:
    """智能体间上下文共享管理器"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.context_prefix = "nexusmind:context:"
        self.task_prefix = "nexusmind:task:"
        self.subscription_prefix = "nexusmind:subscription:"
        self._subscribers: Dict[str, Set[str]] = {}  # task_id -> set of agent_ids
        
    async def share_context(
        self,
        task_id: str,
        agent_id: str,
        context: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """
        共享上下文数据
        
        Args:
            task_id: 任务ID
            agent_id: 智能体ID
            context: 要共享的上下文数据
            ttl: 过期时间（秒），默认1小时
            
        Returns:
            bool: 是否成功
        """
        try:
            # 构建key
            key = f"{self.context_prefix}{task_id}:{agent_id}"
            
            # 添加元数据
            context_with_meta = {
                **context,
                "_metadata": {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "shared_at": datetime.now().isoformat(),
                    "ttl": ttl
                }
            }
            
            # 存储到Redis
            await self.redis.setex(
                key,
                ttl,
                json.dumps(context_with_meta)
            )
            
            # 发布上下文更新事件
            await self._publish_context_update(task_id, agent_id)
            
            # 记录到任务历史
            await self._add_to_task_history(task_id, agent_id, "context_shared", context)
            
            logger.info(f"Context shared: task={task_id}, agent={agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to share context: {e}")
            return False
            
    async def get_shared_context(
        self,
        task_id: str,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取特定智能体的共享上下文
        
        Args:
            task_id: 任务ID
            agent_id: 智能体ID
            
        Returns:
            共享的上下文数据，如果不存在则返回None
        """
        try:
            key = f"{self.context_prefix}{task_id}:{agent_id}"
            data = await self.redis.get(key)
            
            if data:
                context = json.loads(data)
                # 移除元数据，只返回实际上下文
                context.pop("_metadata", None)
                return context
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return None
            
    async def get_task_context(
        self,
        task_id: str,
        include_metadata: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        获取任务的所有共享上下文
        
        Args:
            task_id: 任务ID
            include_metadata: 是否包含元数据
            
        Returns:
            Dict[agent_id, context]: 所有智能体的上下文
        """
        try:
            pattern = f"{self.context_prefix}{task_id}:*"
            contexts = {}
            
            # 扫描匹配的keys
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                for key in keys:
                    # 提取agent_id
                    agent_id = key.decode('utf-8').split(":")[-1]
                    
                    # 获取上下文
                    data = await self.redis.get(key)
                    if data:
                        context = json.loads(data)
                        if not include_metadata:
                            context.pop("_metadata", None)
                        contexts[agent_id] = context
                        
                if cursor == 0:
                    break
                    
            return contexts
            
        except Exception as e:
            logger.error(f"Failed to get task context: {e}")
            return {}
            
    async def merge_contexts(
        self,
        task_id: str,
        agent_ids: List[str]
    ) -> Dict[str, Any]:
        """
        合并多个智能体的上下文
        
        Args:
            task_id: 任务ID
            agent_ids: 要合并的智能体ID列表
            
        Returns:
            合并后的上下文
        """
        merged = {}
        
        for agent_id in agent_ids:
            context = await self.get_shared_context(task_id, agent_id)
            if context:
                # 使用agent_id作为命名空间避免冲突
                merged[agent_id] = context
                
        return merged
        
    async def subscribe_to_context_updates(
        self,
        task_id: str,
        agent_id: str,
        callback: Optional[callable] = None
    ):
        """
        订阅任务的上下文更新
        
        Args:
            task_id: 任务ID
            agent_id: 订阅的智能体ID
            callback: 回调函数（可选）
        """
        # 记录订阅关系
        if task_id not in self._subscribers:
            self._subscribers[task_id] = set()
        self._subscribers[task_id].add(agent_id)
        
        # 存储订阅信息到Redis
        key = f"{self.subscription_prefix}{task_id}"
        await self.redis.sadd(key, agent_id)
        await self.redis.expire(key, 3600)  # 1小时过期
        
        # 如果提供了回调，启动监听
        if callback:
            asyncio.create_task(
                self._listen_for_updates(task_id, agent_id, callback)
            )
            
    async def _publish_context_update(self, task_id: str, agent_id: str):
        """发布上下文更新事件"""
        channel = f"context_update:{task_id}"
        message = json.dumps({
            "task_id": task_id,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        })
        
        await self.redis.publish(channel, message)
        
    async def _listen_for_updates(
        self,
        task_id: str,
        agent_id: str,
        callback: callable
    ):
        """监听上下文更新"""
        channel = f"context_update:{task_id}"
        pubsub = self.redis.pubsub()
        
        try:
            await pubsub.subscribe(channel)
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    
                    # 不处理自己的更新
                    if data["agent_id"] != agent_id:
                        await callback(data)
                        
        except Exception as e:
            logger.error(f"Error in context listener: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            
    async def _add_to_task_history(
        self,
        task_id: str,
        agent_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """添加到任务历史"""
        history_key = f"{self.task_prefix}{task_id}:history"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "event_type": event_type,
            "data": data
        }
        
        # 添加到列表
        await self.redis.lpush(history_key, json.dumps(entry))
        
        # 只保留最近100条
        await self.redis.ltrim(history_key, 0, 99)
        
        # 设置过期时间
        await self.redis.expire(history_key, 86400)  # 24小时
        
    async def get_task_history(
        self,
        task_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取任务历史"""
        history_key = f"{self.task_prefix}{task_id}:history"
        
        # 获取历史记录
        history_data = await self.redis.lrange(history_key, 0, limit - 1)
        
        history = []
        for item in history_data:
            history.append(json.loads(item))
            
        return history
        
    async def cleanup_expired_contexts(self):
        """清理过期的上下文（此方法由定期任务调用）"""
        # Redis会自动处理过期，这里可以添加额外的清理逻辑
        pass
        
    async def get_active_tasks(self) -> List[str]:
        """获取所有活跃的任务ID"""
        pattern = f"{self.context_prefix}*"
        task_ids = set()
        
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor,
                match=pattern,
                count=100
            )
            
            for key in keys:
                # 提取task_id
                parts = key.decode('utf-8').split(":")
                if len(parts) >= 3:
                    task_id = parts[2]
                    task_ids.add(task_id)
                    
            if cursor == 0:
                break
                
        return list(task_ids)
        
    async def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """获取任务摘要信息"""
        # 获取所有相关智能体
        contexts = await self.get_task_context(task_id, include_metadata=True)
        
        # 获取历史记录
        history = await self.get_task_history(task_id, limit=10)
        
        # 获取订阅者
        sub_key = f"{self.subscription_prefix}{task_id}"
        subscribers = await self.redis.smembers(sub_key)
        
        return {
            "task_id": task_id,
            "active_agents": list(contexts.keys()),
            "subscriber_count": len(subscribers),
            "context_count": len(contexts),
            "recent_events": len(history),
            "last_update": history[0]["timestamp"] if history else None
        }