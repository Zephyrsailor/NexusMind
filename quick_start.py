#!/usr/bin/env python3
"""
NexusMind 快速启动脚本
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("🧠 NexusMind 智能体平台 - 快速启动")
    print("=" * 60)
    print("🎤 语音录制与识别")
    print("📷 摄像头拍照与分析")
    print("🔧 智能决策协调")
    print("=" * 60)

def check_python():
    """检查Python版本"""
    print("🔍 检查Python环境...")
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    print(f"✅ Python版本: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """安装依赖"""
    print("\n📦 安装Python依赖...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 依赖安装成功")
            return True
        else:
            print(f"❌ 依赖安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 安装过程中出错: {e}")
        return False

def setup_environment():
    """设置环境"""
    print("\n🔧 配置环境...")
    
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 创建.env配置文件...")
        with open(".env", "w", encoding="utf-8") as f:
            f.write("""# NexusMind 环境配置

# 应用配置
DEBUG=true
HOST=0.0.0.0
PORT=8080

# LLM配置 (可选，用于扩展功能)
# LLM_API_KEY=your-api-key-here

# 如果需要使用在线语音识别，可以配置相关API
# 目前系统使用免费的Google Speech Recognition
""")
        print("✅ 已创建.env配置文件")
    else:
        print("✅ .env配置文件已存在")
    
    return True

def run_tests():
    """运行测试"""
    print("\n🧪 运行系统测试...")
    try:
        result = subprocess.run([sys.executable, "test_system.py"], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ 系统测试通过")
            return True
        else:
            print("⚠️  系统测试有警告，但可能仍可运行")
            print("详细信息请查看测试输出")
            return True  # 仍然允许继续，因为可能只是设备不可用
    except subprocess.TimeoutExpired:
        print("⚠️  测试超时，跳过测试步骤")
        return True
    except Exception as e:
        print(f"⚠️  测试过程中出错: {e}")
        return True

def start_server():
    """启动服务器"""
    print("\n🚀 启动NexusMind服务器...")
    print("📍 服务地址: http://localhost:8080")
    print("📖 API文档: http://localhost:8080/docs")
    print("🧪 测试页面: 请打开 test_client.html")
    print("\n⏹️  按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        # 启动服务器
        subprocess.run([sys.executable, "run_server.py"])
    except KeyboardInterrupt:
        print("\n\n⏹️  服务器已停止")

def open_test_page():
    """打开测试页面"""
    test_page = Path("test_client.html")
    if test_page.exists():
        print("\n🌐 打开测试页面...")
        try:
            webbrowser.open(f"file://{test_page.absolute()}")
            print("✅ 测试页面已在浏览器中打开")
        except Exception as e:
            print(f"⚠️  无法自动打开浏览器: {e}")
            print(f"请手动打开: {test_page.absolute()}")

def show_usage_tips():
    """显示使用提示"""
    print("\n💡 使用提示:")
    print("=" * 60)
    print("🎯 功能测试:")
    print("  • 语音功能: '录音5秒', '录音并识别'")
    print("  • 摄像头功能: '拍照', '拍照并分析'")
    print("  • 系统查询: '设备状态', '帮助'")
    
    print("\n📡 API测试:")
    print("  • 健康检查: GET http://localhost:8080/health")
    print("  • 系统状态: GET http://localhost:8080/api/v1/status")
    print("  • 录音接口: POST http://localhost:8080/api/v1/audio/record")
    print("  • 拍照接口: POST http://localhost:8080/api/v1/camera/capture")
    
    print("\n🔧 故障排除:")
    print("  • 如果麦克风不可用，请检查系统麦克风权限")
    print("  • 如果摄像头不可用，请检查摄像头连接和权限")
    print("  • 查看详细日志获取更多调试信息")
    print("=" * 60)

def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    if not check_python():
        sys.exit(1)
    
    # 安装依赖
    if not install_dependencies():
        print("\n❌ 环境准备失败，请手动安装依赖")
        print("运行命令: pip install -r requirements.txt")
        sys.exit(1)
    
    # 设置环境
    if not setup_environment():
        sys.exit(1)
    
    # 运行测试
    run_tests()
    
    # 显示使用提示
    show_usage_tips()
    
    # 询问是否立即启动
    try:
        choice = input("\n🚀 是否立即启动服务器? (y/n): ").strip().lower()
        if choice in ['y', 'yes', '是', '']:
            # 打开测试页面
            open_test_page()
            
            # 稍等一下让浏览器打开
            time.sleep(2)
            
            # 启动服务器
            start_server()
        else:
            print("\n💡 稍后可以运行以下命令启动:")
            print("   python run_server.py")
            print("   然后打开 test_client.html 进行测试")
    
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
        sys.exit(0)

if __name__ == "__main__":
    main()