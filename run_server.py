#!/usr/bin/env python
"""
NexusMind服务器启动脚本
"""

import uvicorn
import asyncio
import logging
from backend.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """启动NexusMind服务器"""
    logger.info(f"🚀 启动 {settings.app_name} v{settings.app_version}")
    logger.info(f"📡 API地址: http://{settings.host}:{settings.port}")
    logger.info(f"📚 API文档: http://{settings.host}:{settings.port}/docs")
    
    # 运行服务器
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )


if __name__ == "__main__":
    main()