#!/usr/bin/env python3
"""
NexusMind服务器启动脚本
"""

import uvicorn
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.core.config import settings

def main():
    """启动FastAPI服务器"""
    print(f"🚀 启动 {settings.app_name} v{settings.app_version}")
    print(f"📍 服务地址: http://{settings.host}:{settings.port}")
    print(f"🔧 调试模式: {'开启' if settings.debug else '关闭'}")
    print(f"🤖 LLM提供商: {settings.llm_provider}")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "backend.api.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n⏹️  服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()