#!/usr/bin/env python3
"""
NexusMind 智能安装脚本
自动检测环境并提供不同层次的安装选项
"""

import os
import sys
import subprocess
import platform

def run_command(cmd, ignore_error=False):
    """运行命令并返回结果"""
    print(f"🔧 执行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 成功")
            return True, result.stdout
        else:
            if not ignore_error:
                print(f"❌ 失败: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        if not ignore_error:
            print(f"❌ 异常: {e}")
        return False, str(e)

def check_poetry():
    """检查Poetry是否安装"""
    success, _ = run_command("poetry --version", ignore_error=True)
    return success

def check_docker():
    """检查Docker是否运行"""
    success, _ = run_command("docker ps", ignore_error=True)
    return success

def check_system_deps():
    """检查系统依赖"""
    system = platform.system()
    if system == "Darwin":  # macOS
        # 检查Homebrew
        brew_ok, _ = run_command("brew --version", ignore_error=True)
        if not brew_ok:
            print("⚠️  建议安装Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        
        # 检查portaudio
        portaudio_ok, _ = run_command("brew list portaudio", ignore_error=True)
        if not portaudio_ok:
            print("📦 需要安装portaudio: brew install portaudio")
            run_command("brew install portaudio")
    
    return True

def show_menu():
    """显示安装选项菜单"""
    print("\n🚀 NexusMind 安装选项:")
    print("1. 🏃 快速开始 (core) - 基础API功能，支持文本对话")
    print("2. 🎯 基础功能 (basic) - 包含语音识别、OCR、客户端工具")  
    print("3. 🤖 AI完整版 (ai-full) - 包含Whisper语音、PyTorch等AI功能")
    print("4. 🌟 完整安装 (all) - 所有功能 (需要较长安装时间)")
    print("5. 🔧 自定义安装 - 选择特定功能模块")
    print("6. 📚 显示各模块说明")
    print("0. 退出")
    
    choice = input("\n请选择安装方式 (0-6): ").strip()
    return choice

def show_modules():
    """显示各模块说明"""
    print("\n📚 NexusMind 功能模块说明:")
    print("├── core: 基础功能 (FastAPI服务、文本对话)")
    print("├── client: 客户端工具 (rich界面、pyaudio录音)")
    print("├── speech: 语音识别 (SpeechRecognition)")
    print("├── ocr: 光学字符识别 (pytesseract)")
    print("├── pytorch: PyTorch框架 (深度学习基础)")
    print("├── whisper: Whisper语音AI (需要PyTorch)")
    print("├── basic: 基础功能合集 (不含AI)")
    print("├── ai-full: AI完整功能 (含PyTorch+Whisper)")
    print("└── all: 全部功能")

def install_with_options(extras):
    """根据选择安装功能"""
    print(f"\n🔄 开始安装 NexusMind {extras}...")
    
    # 更新锁文件
    print("📝 更新依赖锁定文件...")
    success, _ = run_command("poetry lock")
    if not success:
        print("❌ 锁文件更新失败")
        return False
    
    # 安装依赖
    if extras:
        cmd = f"poetry install --extras \"{extras}\""
    else:
        cmd = "poetry install"
    
    print(f"📦 安装依赖: {cmd}")
    success, output = run_command(cmd)
    
    if success:
        print("✅ 安装成功!")
        return True
    else:
        print("❌ 安装失败")
        # 如果是torch相关问题，提供替代方案
        if "torch" in output or "triton" in output:
            print("\n💡 检测到PyTorch安装问题，这可能是由于:")
            print("   1. 网络问题 - 可以尝试使用国内镜像")
            print("   2. 架构兼容性 - 某些版本可能不支持您的系统")
            print("   3. 可以先安装基础功能，稍后手动安装PyTorch")
            
            retry = input("\n是否尝试安装基础功能 (不含PyTorch)? (y/n): ")
            if retry.lower() == 'y':
                return install_with_options("basic")
        
        return False

def start_services():
    """启动Docker服务"""
    print("\n🐳 检查Docker服务...")
    if not check_docker():
        print("❌ Docker未运行，请先启动Docker")
        return False
    
    print("🔄 启动基础服务 (Redis, RabbitMQ, ChromaDB)...")
    os.chdir("infrastructure")
    success, _ = run_command("docker-compose up -d")
    os.chdir("..")
    
    if success:
        print("✅ 基础服务启动成功!")
        return True
    else:
        print("❌ 基础服务启动失败")
        return False

def test_installation():
    """测试安装结果"""
    print("\n🧪 测试安装结果...")
    
    # 测试导入
    test_cmd = """poetry run python -c "
import sys
print('Python版本:', sys.version)

try:
    from backend.core.config import settings
    print('✅ 配置加载成功')
except Exception as e:
    print('❌ 配置加载失败:', e)

try:
    import redis
    print('✅ Redis库可用')
except Exception as e:
    print('❌ Redis库不可用:', e)

try:
    import rich
    print('✅ Rich库可用')
except Exception as e:
    print('⚠️  Rich库不可用:', e)

try:
    import pyaudio
    print('✅ PyAudio可用')
except Exception as e:
    print('⚠️  PyAudio不可用:', e)

try:
    import torch
    print('✅ PyTorch可用, 版本:', torch.__version__)
except Exception as e:
    print('⚠️  PyTorch不可用:', e)

try:
    import whisper
    print('✅ Whisper可用')
except Exception as e:
    print('⚠️  Whisper不可用:', e)
"
"""
    
    success, output = run_command(test_cmd)
    print(output)
    
    # 提供启动命令
    print("\n🚀 NexusMind 启动命令:")
    print("poetry run uvicorn backend.api.main:app --host 0.0.0.0 --port 8090 --reload")

def main():
    print("🎉 欢迎使用 NexusMind 智能安装程序!")
    print("="*50)
    
    # 检查基础环境
    print("🔍 检查安装环境...")
    
    if not check_poetry():
        print("❌ Poetry未安装，请先安装Poetry:")
        print("curl -sSL https://install.python-poetry.org | python3 -")
        return 1
    
    print("✅ Poetry已安装")
    
    # 检查系统依赖
    check_system_deps()
    
    while True:
        choice = show_menu()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            if install_with_options("core"):
                test_installation()
            break
        elif choice == "2":
            if install_with_options("basic"):
                test_installation() 
            break
        elif choice == "3":
            if install_with_options("ai-full"):
                test_installation()
            break
        elif choice == "4":
            if install_with_options("all"):
                test_installation()
            break
        elif choice == "5":
            show_modules()
            extras = input("\n请输入要安装的模块 (用空格分隔): ").strip()
            if extras:
                if install_with_options(extras):
                    test_installation()
            break
        elif choice == "6":
            show_modules()
        else:
            print("❌ 无效选择，请重新输入")
    
    # 询问是否启动服务
    if input("\n是否现在启动Docker基础服务? (y/n): ").lower() == 'y':
        start_services()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 