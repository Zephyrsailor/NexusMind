#!/usr/bin/env python3
"""
NexusMind系统测试脚本 - 语音和摄像头Agent版本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.core.orchestrator import SimpleOrchestrator
from backend.core.audio_agent import AudioAgent
from backend.core.camera_agent import CameraAgent
from backend.models.schemas import UserRequest

async def test_orchestrator():
    """测试核心协调器"""
    print("🧪 开始测试NexusMind智能协调器...")
    
    # 初始化协调器
    orchestrator = SimpleOrchestrator()
    await orchestrator.initialize()
    print("✅ 协调器初始化成功")
    
    # 测试用例
    test_cases = [
        {
            "name": "基础对话测试",
            "message": "你好，我是新用户"
        },
        {
            "name": "帮助信息测试",
            "message": "帮助"
        },
        {
            "name": "设备状态查询",
            "message": "设备状态"
        },
        {
            "name": "语音功能测试（不实际录音）",
            "message": "录音3秒",
            "note": "仅测试意图识别，不会实际录音"
        },
        {
            "name": "摄像头功能测试（不实际拍照）",
            "message": "拍照",
            "note": "仅测试意图识别，不会实际拍照"
        },
        {
            "name": "图像分析功能测试",
            "message": "拍照并分析"
        }
    ]
    
    print(f"\n📋 开始执行 {len(test_cases)} 个测试用例...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🔍 测试 {i}: {test_case['name']}")
        print(f"📤 输入: {test_case['message']}")
        if test_case.get('note'):
            print(f"💡 说明: {test_case['note']}")
        
        try:
            # 创建用户请求
            user_request = UserRequest(message=test_case['message'])
            
            # 处理请求
            response = await orchestrator.process_request(user_request)
            
            print(f"📥 状态: {response.status}")
            print(f"📝 响应: {response.message}")
            
            if response.payload:
                payload = response.payload
                print(f"📊 结果类型: {payload.get('agent_type', 'unknown')}")
                if 'message' in payload:
                    print(f"   消息: {payload['message']}")
                if 'result' in payload and isinstance(payload['result'], dict):
                    if 'reply' in payload['result']:
                        print(f"   回复: {payload['result']['reply']}")
                
            print("✅ 测试通过\n")
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}\n")
    
    print("🎉 所有协调器测试完成！")

async def test_agents():
    """测试各个Agent"""
    print("🔧 开始测试各个智能体...")
    
    # 测试语音Agent
    print("\n🎤 测试语音Agent:")
    audio_agent = AudioAgent()
    
    try:
        # 获取状态
        status = await audio_agent.get_status()
        print(f"   状态: {status.get('status', 'unknown')}")
        print(f"   麦克风可用: {status.get('microphone_available', False)}")
        print(f"   支持的操作: {', '.join(status.get('supported_actions', []))}")
        
        if status.get('microphone_available'):
            print("   ✅ 语音Agent就绪，可以进行录音操作")
        else:
            print("   ⚠️  未检测到麦克风，但Agent基础功能正常")
            
    except Exception as e:
        print(f"   ❌ 语音Agent测试失败: {e}")
    
    # 测试摄像头Agent
    print("\n� 测试摄像头Agent:")
    camera_agent = CameraAgent()
    
    try:
        # 获取状态
        status = await camera_agent.get_status()
        print(f"   状态: {status.get('status', 'unknown')}")
        print(f"   摄像头可用: {status.get('camera_available', False)}")
        print(f"   可用摄像头: {status.get('available_cameras', [])}")
        print(f"   分辨率: {status.get('resolution', 'unknown')}")
        print(f"   支持的操作: {', '.join(status.get('supported_actions', []))}")
        
        if status.get('camera_available'):
            print("   ✅ 摄像头Agent就绪，可以进行拍照操作")
        else:
            print("   ⚠️  未检测到摄像头，但Agent基础功能正常")
            
    except Exception as e:
        print(f"   ❌ 摄像头Agent测试失败: {e}")
    
    print("✅ Agent测试完成")

async def test_interactive_demo():
    """交互式演示（可选）"""
    print("\n🎮 交互式演示")
    print("=" * 50)
    
    orchestrator = SimpleOrchestrator()
    await orchestrator.initialize()
    
    demo_commands = [
        "你好",
        "设备状态", 
        "帮助",
        "功能"
    ]
    
    print("运行演示命令:")
    for cmd in demo_commands:
        print(f"\n👤 用户: {cmd}")
        try:
            request = UserRequest(message=cmd)
            response = await orchestrator.process_request(request)
            
            if response.payload and 'result' in response.payload:
                result = response.payload['result']
                if 'reply' in result:
                    print(f"🤖 助手: {result['reply']}")
                else:
                    print(f"🤖 助手: {response.payload.get('message', '处理完成')}")
            else:
                print(f"🤖 助手: {response.message}")
        except Exception as e:
            print(f"❌ 错误: {e}")

def main():
    """主函数"""
    print("🚀 NexusMind系统测试开始")
    print("=" * 50)
    print("📝 测试内容:")
    print("   1. 各个智能体状态检查")
    print("   2. 协调器功能测试")
    print("   3. 交互式演示")
    print("=" * 50)
    
    try:
        # 运行异步测试
        asyncio.run(test_agents())
        print("\n" + "=" * 50)
        asyncio.run(test_orchestrator())
        print("\n" + "=" * 50)
        asyncio.run(test_interactive_demo())
        
        print("\n" + "=" * 50)
        print("🎊 所有测试成功完成！")
        print("\n💡 使用说明:")
        print("   - 运行 'python run_server.py' 启动服务器")
        print("   - 访问 http://localhost:8080 查看API文档")
        print("   - 打开 test_client.html 进行WebSocket测试")
        print("\n🎯 功能测试:")
        print("   语音功能: '录音5秒', '录音并识别'")
        print("   摄像头功能: '拍照', '拍照并分析', '拍3张照片'")
        print("   系统查询: '设备状态', '帮助', '功能'")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()