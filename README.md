# NexusMind - 多模态AI聊天系统

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2.63-orange.svg)

NexusMind 是一个具有环境感知能力的多模态AI聊天系统，通过集成语音识别和视觉分析功能，扩展了传统大语言模型的交互能力。

## 🌟 核心特性

- **多智能体协作**: 通过标准化 A2A 协议连接多个专业智能体
- **智能路由**: 基于 LLM Function Calling 的意图理解和自动调度
- **统一接口**: 单一 API 入口处理文本、语音、图像等多模态输入
- **异步处理**: 所有操作异步执行，返回标准化任务响应
- **可扩展架构**: 轻松添加新智能体，无需修改核心代码

## 🚀 快速开始

### 环境要求

- Python 3.11 或 3.12（推荐，3.13可能有兼容性问题）
- macOS/Linux/Windows
- 摄像头和麦克风权限

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/NexusMind.git
cd NexusMind
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐使用Python 3.11）
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装Python依赖
pip install --upgrade pip
pip install -r requirements.txt

# macOS音频支持
brew install portaudio
pip install pyaudio

# Linux音频支持
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

### 3. 配置环境

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑.env文件，添加你的API密钥
# LLM_API_KEY=your-deepseek-api-key
```

### 4. 启动系统

```bash
# 1. 启动基础设施（Docker容器）
make infrastructure

# 2. 新终端 - 启动后端服务（自动包含所有内置智能体）
make start

# 3. 新终端 - 启动聊天界面
python nexusmind_simple_chat.py
```

**注意**：Voice Agent 和 Vision Agent 现在作为内置服务自动启动，无需单独运行。

## 💬 使用示例

### 文字对话
```
You: 你好
NexusMind: 你好！我是NexusMind智能助手，有什么可以帮助您的吗？
```

### 语音输入
```
You: v
🎤 录音中... 说完后按Enter停止
[按 Enter]
✓ 录音完成
识别内容: 今天天气怎么样
NexusMind: 抱歉，我目前无法获取实时天气信息...
```

### 视觉分析
```
You: 看看我周围有什么
NexusMind: 我需要查看您的周围环境。请使用 'p' 命令拍照。

You: p
📷 拍照中... (3秒后自动捕获)
✓ 拍照成功
请描述你想了解什么: 分析这张图片

NexusMind: 场景分析结果：
- 环境：室内办公室
- 亮度：明亮
- 检测到的物体：电脑、键盘、鼠标、杯子
- 主要颜色：白色、灰色、黑色
```

### 退出程序
```
You: quit
👋 再见！
```

## 🏗️ 系统架构

```
用户请求（文本/语音/图像）
         │
         ▼
┌─────────────────────────────┐
│     API Gateway             │
│   POST /api/v1/chat         │  ← 统一入口
└─────────────┬───────────────┘
              │
┌─────────────▼───────────────┐
│   Orchestrator (LangGraph)  │
│   - LLM 理解用户意图        │  ← 智能决策
│   - Function Calling 调度   │
└─────────────┬───────────────┘
              │ A2A Protocol
    ┌─────────┼─────────┐
┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│ Voice │ │Vision │ │Search │  ← 专业智能体
│ Agent │ │ Agent │ │ Agent │
└───┬───┘ └───┬───┘ └───┬───┘
    │         │         │
    └─────────┼─────────┘
              │
         统一响应格式
```

## 🛠️ 常用命令

```bash
# 系统管理
make install          # 安装所有依赖
make infrastructure   # 启动Docker容器（RabbitMQ, Redis, ChromaDB）
make start           # 启动后端服务
make stop            # 停止所有服务
make status          # 查看服务状态
make logs            # 查看日志

# 开发相关
make test            # 运行测试
make format          # 格式化代码
make lint            # 代码检查
make clean           # 清理临时文件
```

## 📋 已实现功能

### ✅ 核心功能
- 基于LangGraph的智能调度器（Orchestrator V2）
- FastAPI后端服务与WebSocket实时通信
- Voice Agent - 语音识别（Google Speech API/Whisper）
- Vision Agent - 图像分析（场景、物体、文字、人脸）
- Context Manager - 跨Agent上下文共享
- 简洁的终端聊天界面

### ✅ 基础设施
- Docker Compose配置（RabbitMQ、Redis、ChromaDB）
- 完整的测试套件
- Makefile自动化命令
- Agent自动发现与注册机制

### 🚧 开发中
- React Native移动应用
- 更多专业Agent（搜索、天气、翻译等）
- 高级调度策略（并行执行、条件路由）
- 生产部署配置

## 🔧 故障排除

### 1. macOS权限问题
```
系统偏好设置 → 隐私与安全 → 麦克风/摄像头 → 允许终端访问
```

### 2. Python依赖安装失败
```bash
# 确保使用正确的Python版本
python --version  # 应该是3.11.x或3.12.x

# 如果是pip版本问题
pip install --upgrade pip setuptools wheel

# 如果是特定包的问题，单独安装
pip install numpy==1.26.4
pip install pyaudio --no-cache-dir
```

### 3. Docker服务启动失败
```bash
# 检查Docker是否运行
docker info

# 检查端口占用
lsof -i :8080  # API服务
lsof -i :5672  # RabbitMQ
lsof -i :6379  # Redis

# 清理并重启
make stop
docker system prune -f
make infrastructure
```

### 4. 语音识别不工作
```bash
# macOS
brew reinstall portaudio
pip uninstall pyaudio
pip install pyaudio --no-cache-dir

# Linux
sudo apt-get update
sudo apt-get install portaudio19-dev
pip install pyaudio
```

### 5. LLM API错误
确保.env文件中的API密钥正确：
```bash
LLM_API_KEY=your-actual-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 6. 重要：Python 3.13 兼容性
如果遇到 `aioredis` 相关错误，请使用 Python 3.11 或 3.12：
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📱 移动应用（开发中）

移动端应用基于React Native开发，目前处于开发阶段。详见 [mobile/README.md](mobile/README.md)

## 📚 项目文档

- [CLAUDE.md](CLAUDE.md) - 项目开发指南和架构详情
- [API文档](http://localhost:8080/docs) - 启动服务后访问
- [架构设计](docs/architect.md) - 系统架构详细说明

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- [LangChain](https://langchain.com/) - AI应用开发框架
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Web框架
- [DeepSeek](https://deepseek.com/) - LLM API提供商