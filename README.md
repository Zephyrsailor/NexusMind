# NexusMind - 开放式智能体联邦平台

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange.svg)

## 🎯 项目愿景

NexusMind 致力于构建一个**开放式的智能体联邦生态**，而非封闭的单一应用。我们的核心理念是创建一个能够与无数专业智能体无缝协作的统一平台，为用户提供前所未有的智能交互体验。

## 🏗️ 架构设计

### 核心设计原则

1. **联邦优先，而非集成** - 新功能以独立智能体微服务形式构建
2. **异步事件驱动** - 所有交互都是异步的，确保极致用户体验
3. **标准化通信** - 基于A2A思想的标准化消息协议
4. **用户体验至上** - 架构复杂性服务于前端简洁性

### 系统架构

```
┌─────────────────────────────┐
│  移动应用 (React Native)      │
│  - UI/VUI/Camera           │
│  - 状态/结果实时渲染        │
└─────────────┬───────────────┘
              │ WebSocket
┌─────────────┴───────────────┐
│   核心服务网关 (FastAPI)      │
└─────────────┬───────────────┘
              │
┌─────────────┴───────────────┐
│ 核心协调Agent (Orchestrator) │
│ - LangGraph驱动的决策流     │
│ - 异步任务追踪 (Redis)      │
│ - 记忆模块 (ChromaDB)       │
└─────────────┬───────────────┘
              │ A2A Protocol
┌─────────────┴───────────────┐
│ 智能体通信总线 (RabbitMQ)    │
└─────────────┬───────────────┘
        ┌─────┼─────┐
   ┌────┴──┐ ┌┴────┐ ┌──┴────┐
   │视觉Agent│ │搜索Agent│ │天气Agent│
   │(微服务) │ │(微服务)│ │(微服务) │
   └───────┘ └─────┘ └───────┘
```

## 🛠️ 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| **核心编排** | LangGraph | 强大的决策流和状态管理 |
| **API服务** | FastAPI | 高性能异步Web框架 |
| **LLM引擎** | OpenAI/DeepSeek | 语言理解和推理 |
| **消息队列** | RabbitMQ | 智能体间异步通信 |
| **内存存储** | ChromaDB | 长期记忆和向量检索 |
| **状态追踪** | Redis | 任务状态实时管理 |
| **前端** | React Native | 跨平台移动应用 |

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/your-repo/NexusMind.git
cd NexusMind

# 安装Python依赖
pip install -r requirements.txt

# 复制环境配置
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，设置必要的配置：

```bash
# 设置LLM API密钥（必需）
LLM_API_KEY="your-openai-api-key"

# 其他配置保持默认即可
```

### 3. 启动基础设施服务

```bash
# 启动 RabbitMQ、Redis、ChromaDB
cd infrastructure
docker-compose up -d
```

### 4. 运行系统测试

```bash
# 测试核心功能
python test_system.py
```

### 5. 启动服务器

```bash
# 启动NexusMind核心服务
python run_server.py
```

服务启动后，可以访问：
- API文档: http://localhost:8080/docs
- 健康检查: http://localhost:8080/health
- WebSocket测试: ws://localhost:8080/ws/test-client

## 📋 当前功能

### ✅ 已实现（第一周目标）

- [x] 核心协调器 (LangGraph驱动)
- [x] 本地计算器工具
- [x] 本地文本解析工具
- [x] FastAPI Web服务
- [x] WebSocket实时通信
- [x] 智能决策流程
- [x] 异步任务处理

### 🔄 开发中（第二周目标）

- [ ] RabbitMQ消息总线集成
- [ ] A2A协议实现
- [ ] 天气智能体微服务
- [ ] 外部智能体通信

### 📅 计划中（第三、四周）

- [ ] 搜索智能体微服务
- [ ] 视觉识别智能体
- [ ] ChromaDB记忆系统
- [ ] React Native移动应用
- [ ] 智能体注册与发现

## 🧪 测试功能

### API测试

```bash
# 健康检查
curl http://localhost:8080/health

# 测试处理请求
curl -X POST "http://localhost:8080/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{"message": "计算 2 + 3 * 4"}'

# 测试本地工具
curl -X POST "http://localhost:8080/api/v1/tools/test"
```

### WebSocket测试

使用WebSocket客户端连接到 `ws://localhost:8080/ws/test-client`

发送消息格式：
```json
{
  "type": "user_request",
  "payload": {
    "message": "你好，请帮我计算 10 + 20"
  }
}
```

## 🎯 使用场景

1. **数学计算**: "请计算 2 + 3 * 4"
2. **文本分析**: "请分析这段文本的情感和关键词"
3. **混合任务**: "分析文本'计算5+7'并执行其中的数学计算"

## 🔧 开发指南

### 添加新的本地工具

1. 在 `backend/core/tools.py` 中创建新工具类
2. 继承 `BaseTool` 并实现 `_run` 方法
3. 在 `NexusMindOrchestrator._initialize_tools()` 中注册

### 扩展决策逻辑

编辑 `backend/core/orchestrator.py` 中的LangGraph节点：
- `_analyze_request`: 请求分析
- `_plan_execution`: 执行规划
- `_execute_local_tools`: 工具执行
- `_format_response`: 响应格式化

## 📚 项目结构

```
NexusMind/
├── backend/                 # 后端核心代码
│   ├── api/                # FastAPI路由
│   ├── core/               # 核心逻辑
│   ├── models/             # 数据模型
│   └── utils/              # 工具函数
├── agents/                 # 智能体微服务
├── frontend/               # React Native应用
├── infrastructure/         # Docker配置
├── docs/                   # 项目文档
├── requirements.txt        # Python依赖
├── run_server.py          # 服务启动脚本
└── test_system.py         # 系统测试脚本
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🔗 相关链接

- [架构设计文档](docs/architect.md)
- [API文档](http://localhost:8080/docs)
- [LangGraph官方文档](https://langchain-ai.github.io/langgraph/)
- [FastAPI官方文档](https://fastapi.tiangolo.com/)

---

**🌟 如果这个项目对你有帮助，请给我们一个Star！**
