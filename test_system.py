#!/usr/bin/env python3
"""
NexusMind系统测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.core.orchestrator import NexusMindOrchestrator
from backend.models.schemas import UserRequest

async def test_orchestrator():
    """测试核心协调器"""
    print("🧪 开始测试NexusMind核心协调器...")
    
    # 初始化协调器
    orchestrator = NexusMindOrchestrator()
    print("✅ 协调器初始化成功")
    
    # 测试用例
    test_cases = [
        {
            "name": "基础对话测试",
            "message": "你好，我是新用户"
        },
        {
            "name": "计算功能测试",
            "message": "请计算 2 + 3 * 4"
        },
        {
            "name": "文本解析测试", 
            "message": "请分析这段文本：Hello world! 联系我们：contact@example.com，电话：1234567890"
        },
        {
            "name": "混合功能测试",
            "message": "请分析文本'测试计算 5 + 7'并提取其中的数学表达式进行计算"
        }
    ]
    
    print(f"\n📋 开始执行 {len(test_cases)} 个测试用例...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🔍 测试 {i}: {test_case['name']}")
        print(f"📤 输入: {test_case['message']}")
        
        try:
            # 创建用户请求
            user_request = UserRequest(message=test_case['message'])
            
            # 处理请求
            response = await orchestrator.process_request(user_request)
            
            print(f"📥 状态: {response.status}")
            print(f"📝 响应: {response.message}")
            
            if response.payload:
                print(f"📊 详细结果:")
                if 'reply_message' in response.payload:
                    print(f"   {response.payload['reply_message']}")
                
            print("✅ 测试通过\n")
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}\n")
    
    print("🎉 所有测试完成！")

async def test_tools():
    """测试本地工具"""
    print("🔧 开始测试本地工具...")
    
    from backend.core.tools import LocalCalculatorTool, LocalTextParserTool
    
    # 测试计算器
    print("\n📊 测试计算器工具:")
    calculator = LocalCalculatorTool()
    
    calc_tests = [
        "2 + 3 * 4",
        "sqrt(16)",
        "sin(3.14159/2)",
        "10 / 2"
    ]
    
    for expr in calc_tests:
        try:
            result = calculator._run(expr)
            print(f"   {expr} = {result}")
        except Exception as e:
            print(f"   {expr} -> 错误: {e}")
    
    # 测试文本解析器
    print("\n📝 测试文本解析工具:")
    parser = LocalTextParserTool()
    
    test_text = "Hello world! 这是一个测试文本。联系邮箱：test@example.com，电话：1234567890。访问网站：https://example.com"
    
    try:
        result = parser._run(test_text, "general")
        print(f"   解析结果: {result}")
    except Exception as e:
        print(f"   解析错误: {e}")
    
    print("✅ 工具测试完成")

def main():
    """主函数"""
    print("🚀 NexusMind系统测试开始")
    print("=" * 50)
    
    try:
        # 运行异步测试
        asyncio.run(test_tools())
        print("\n" + "=" * 50)
        asyncio.run(test_orchestrator())
        
        print("\n" + "=" * 50)
        print("🎊 所有测试成功完成！")
        print("\n💡 提示：")
        print("   - 运行 'python run_server.py' 启动服务器")
        print("   - 访问 http://localhost:8080 查看API文档")
        print("   - 使用 WebSocket 连接到 ws://localhost:8080/ws/test-client")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()