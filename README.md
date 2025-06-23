# NexusMind - 联邦多模态智能体协作平台

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Docker](https://img.shields.io/badge/Docker-latest-blue.svg)

## 🎯 项目简介

NexusMind 是一个基于**语音和视觉**的联邦多智能体协作平台，支持实时多模态交互。系统采用A2A（Agent-to-Agent）协议，通过智能协调器统一管理语音识别、图像分析、任务调度等核心功能。

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端客户端    │────│   FastAPI网关   │────│   智能协调器    │
│   (WebSocket)   │    │   (REST/WS)     │    │  (Orchestrator) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    A2A消息总线 (RabbitMQ)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                   ┌────────────┼────────────┐
                   ▼            ▼            ▼
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │  语音智能体  │ │  视觉智能体  │ │  更多智能体  │
        │ (录音/识别) │ │ (拍照/分析) │ │  (可扩展)   │
        └─────────────┘ └─────────────┘ └─────────────┘

      ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
      │    Redis    │ │  ChromaDB   │ │   本地AI    │
      │  (状态缓存) │ │ (长期记忆)  │ │ (Whisper等) │
      └─────────────┘ └─────────────┘ └─────────────┘
```

## 🚀 快速启动

### 前置要求

- **Poetry** (推荐) 或 **Python 3.9+** + pip
- **Docker & Docker Compose** (必须)
- **摄像头和麦克风** (可选，用于多模态功能)

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/NexusMind.git
cd NexusMind
```

### 2. 启动基础服务 (🔥重要!)

```bash
# 启动 Redis、RabbitMQ、ChromaDB
cd infrastructure
docker-compose up -d

# 检查服务状态
docker-compose ps
```

**服务验证：**
- Redis: `redis-cli -p 6379 ping` → PONG
- RabbitMQ管理界面: http://localhost:15672 (nexusmind/nexusmind123)
- ChromaDB: http://localhost:8000

### 3. 安装Python依赖

#### 方式1: Poetry (推荐)
```bash
cd ..

# 安装Poetry (如未安装)
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

# 安装项目依赖
poetry install --extras "core"  # 核心功能 (推荐)
# 或 poetry install --extras "all"  # 完整功能 (需要编译pyaudio)
# 或 poetry install --extras "client"  # 仅客户端
# 或 poetry install  # 最小安装
```

#### 方式2: pip (兼容方式)
```bash
# 从pyproject.toml生成requirements
poetry export -f requirements.txt --output requirements.txt --extras all

# 传统pip安装
python3.9 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 根据需要修改 .env 文件中的配置
```

### 5. 启动NexusMind服务

#### Poetry方式 (推荐)
```bash
# 方式1: 直接使用uvicorn (推荐)
poetry run uvicorn backend.api.main:app --host 0.0.0.0 --port 8090 --reload

# 方式2: 使用启动脚本
poetry run python run_server.py

# 方式3: 先激活环境
poetry shell
uvicorn backend.api.main:app --host 0.0.0.0 --port 8090 --reload
```

#### pip方式
```bash
source venv/bin/activate  # 确保在虚拟环境中
python run_server.py
```

**成功启动标志：**
```
🚀 启动 NexusMind Orchestrator v1.0.0
📡 API地址: http://0.0.0.0:8090
📚 API文档: http://0.0.0.0:8090/docs
INFO:     Application startup complete.
```

## 🧪 功能测试

### API接口测试

```bash
# 健康检查
curl http://localhost:8090/health

# 系统状态
curl http://localhost:8090/api/v1/status

# 智能对话 (支持语音+图像)
curl -X POST http://localhost:8090/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下自己"}'
```

### WebSocket实时交互

打开浏览器访问: http://localhost:8090/docs

在FastAPI文档页面测试WebSocket连接：`/ws/chat`

### 多模态功能演示

#### 方式1: 基础聊天客户端 (推荐)
```bash
# 启动基础客户端 (无需额外依赖)
python nexusmind_simple_chat_basic.py

# 对话示例
"你好，请介绍一下自己"
"录音5秒"              # 录制语音
"语音识别"             # 语音转文字
"拍照"                # 摄像头拍照
"看看这是什么"         # 图像分析
"我手上拿的是什么"     # 自动拍照+分析
"帮我分析一下这张图片"  # 多模态理解
```

#### 方式2: 完整版客户端 (需要安装rich、pyaudio)
```bash
# Poetry方式 (推荐)
poetry install --extras "client"
poetry run python nexusmind_simple_chat.py

# pip方式
pip install rich pyaudio
python nexusmind_simple_chat.py
```

#### 方式3: 直接API调用
```bash
# 语音功能
"录音5秒"              # 录制语音
"语音识别"             # 语音转文字

# 视觉功能  
"拍照"                # 摄像头拍照
"看看这是什么"         # 图像分析
"我手上拿的是什么"     # 自动拍照+分析

# 智能对话
"帮我分析一下这张图片"  # 多模态理解
```

## 📚 核心功能

### 🧠 智能协调器 (LLM Function Calling)
- **意图理解**: 基于大语言模型的智能意图分析
- **工具调用**: 自动选择合适的智能体执行任务  
- **实时响应**: WebSocket实时状态更新
- **错误恢复**: 智能错误处理和任务重试

### 🎤 语音智能体
- **语音录制**: 高质量音频采集
- **语音识别**: Whisper本地/云端识别
- **多语言支持**: 中英文等多语言
- **设备管理**: 自动检测麦克风设备

### 📷 视觉智能体
- **图像捕获**: 高清摄像头拍照
- **图像分析**: AI驱动的场景理解
- **物体检测**: 实时物体识别
- **人脸检测**: OpenCV人脸识别

### 🔄 A2A协议支持
- **异步消息**: RabbitMQ消息队列
- **智能体注册**: 动态智能体发现和注册
- **负载均衡**: 自动任务分发
- **故障转移**: 智能体故障自动恢复

## 🛠️ 开发指南

### 项目结构

```
NexusMind/
├── 📁 backend/              # 后端核心代码
│   ├── 📁 api/              # FastAPI路由
│   ├── 📁 core/             # 核心组件
│   │   ├── orchestrator.py  # 智能协调器
│   │   ├── agent_manager.py # 智能体管理
│   │   └── agents/          # 内置智能体
│   ├── 📁 models/           # 数据模型
│   └── 📁 utils/            # 工具函数
├── 📁 infrastructure/       # 基础设施
│   └── docker-compose.yml  # Docker服务配置
├── 📁 tests/               # 测试代码
├── 📄 requirements.txt     # Python依赖
├── 📄 .env.example        # 环境变量模板
└── 📄 run_server.py       # 服务启动脚本
```

### 环境变量配置

关键配置项：

```bash
# LLM配置
LLM_PROVIDER=deepseek
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com

# 基础服务 (Docker启动后无需修改)
REDIS_HOST=localhost
REDIS_PORT=6379
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672

# 多模态模型
WHISPER_MODEL_SIZE=base
MULTIMODAL_MODEL=Qwen/Qwen-VL-Chat
USE_LOCAL_MODELS=true
```

### 添加新智能体

1. 在 `backend/core/agents/` 创建新智能体类
2. 继承 `BaseAgent` 并实现必要方法
3. 在 `agent_manager.py` 中注册新智能体
4. 更新协调器的工具注册表

## 🔧 故障排除

### 常见问题

**1. 服务启动失败**
```bash
# 检查Docker服务
docker-compose -f infrastructure/docker-compose.yml ps

# 重启基础服务
docker-compose -f infrastructure/docker-compose.yml restart
```

**2. Redis连接失败**
```bash
# 测试Redis连接
redis-cli -p 6379 ping

# 检查端口占用
lsof -i :6379
```

**3. RabbitMQ连接失败**
```bash
# 检查RabbitMQ状态
curl -u nexusmind:nexusmind123 http://localhost:15672/api/overview

# 重置RabbitMQ
docker-compose -f infrastructure/docker-compose.yml restart rabbitmq
```

**4. 端口冲突**
```bash
# 检查端口占用
lsof -i :8090

# 修改端口 (在.env中设置PORT=8091)
```

### 日志调试

```bash
# 查看应用日志
tail -f logs/nexusmind.log

# 查看Docker服务日志
docker-compose -f infrastructure/docker-compose.yml logs -f
```

## 📊 性能监控

### 系统监控端点

- **健康检查**: http://localhost:8090/health
- **系统状态**: http://localhost:8090/api/v1/status
- **智能体列表**: http://localhost:8090/api/v1/agents
- **RabbitMQ管理**: http://localhost:15672

### 性能指标

- **响应时间**: < 2秒 (普通任务)
- **并发处理**: 支持100个并发任务
- **内存使用**: < 2GB (包含AI模型)
- **磁盘空间**: < 10GB (包含模型缓存)

## 🔮 版本规划

### ✅ v1.0.0 (当前版本)
- [x] 基础架构搭建
- [x] 语音智能体 (录音/识别)
- [x] 视觉智能体 (拍照/分析)  
- [x] 智能协调器 (LLM Function Calling)
- [x] A2A消息协议
- [x] Docker化部署

### 🔄 v1.1.0 (开发中)
- [ ] 语音合成 (TTS)
- [ ] 视频处理智能体
- [ ] 多轮对话记忆
- [ ] 性能优化

### 📅 v2.0.0 (规划中)
- [ ] 移动端应用 (React Native)
- [ ] 多租户支持
- [ ] 智能体市场
- [ ] 云端部署方案

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交变更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 技术支持

- **文档**: [项目Wiki](https://github.com/yourusername/NexusMind/wiki)
- **问题反馈**: [GitHub Issues](https://github.com/yourusername/NexusMind/issues)
- **讨论交流**: [GitHub Discussions](https://github.com/yourusername/NexusMind/discussions)

---

## 📋 TODOLIST

### ✅ 已完成修复
- [x] 修复Docker服务启动文档缺失问题
- [x] 修复配置文件multimodal_model字段缺失
- [x] 添加正确的项目启动流程
- [x] 修复requirements.txt中redis版本缺失
- [x] 创建基础聊天客户端（无需额外依赖）
- [x] 添加客户端使用说明
- [x] **迁移到Poetry依赖管理** ⭐
- [x] 删除requirements.txt，统一使用pyproject.toml
- [x] 创建Poetry使用指南
- [x] **解决Poetry依赖安装问题** ⭐
- [x] 移除problematic的pyaudio依赖，避免编译问题
- [x] 验证服务器正常启动和API接口工作

### 🔥 当前优先级
- [ ] 修复pyaudio编译问题，恢复音频功能
- [ ] 添加torch/whisper可选安装支持

### 📈 功能改进
- [ ] 添加智能体性能监控
- [ ] 优化错误处理和恢复机制
- [ ] 添加配置验证和健康检查
- [ ] 完善API文档和示例

### 🧪 测试完善
- [ ] 添加单元测试覆盖
- [ ] 添加集成测试
- [ ] 添加性能测试
- [ ] 添加Docker环境测试

### 🚀 部署优化
- [ ] 添加生产环境Docker配置
- [ ] 添加CI/CD流水线
- [ ] 添加监控和告警
- [ ] 添加备份和恢复方案

---

*最后更新: 2025-06-23*
