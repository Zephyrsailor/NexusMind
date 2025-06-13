
---

### **NexusMind——开放式移动智能体平台**

#### **1. 最终愿景 (The Vision)**

我们致力于构建一个**开放式的智能体联邦生态 (Agent Federation Ecosystem)**，而非一个封闭的单一应用。我们的移动端产品，是这个生态的**第一个公民和旗舰级入口**，它将为用户提供一个前所未有的、能够与无数个专业智能体无缝协作的统一交互界面。我们的成功标准，是未来第三方开发者能够轻松地将其开发的智能体“接入”我们的联邦，从而不断丰富整个生态的能力。

#### **2. 核心设计原则 (Core Principles)**

所有技术选型和架构决策都必须遵循以下四大原则：

1.  **联邦优先，而非集成 (Federation over Integration)**: 新功能应优先以独立的“专业智能体微服务”形式构建，通过通信总线接入，而不是在核心协调Agent中堆砌代码。
2.  **异步事件驱动 (Asynchronous & Event-Driven)**: 系统的核心交互必须是异步的。绝不允许出现阻塞式的等待，所有耗时操作都通过带有任务ID的事件流进行追踪和反馈，以保证极致的用户体验。
3.  **标准化通信 (Standardized Communication)**: 所有智能体间的通信都必须遵循我们定义的、基于A2A思想的**标准化消息协议**。这确保了生态内部的互操作性。
4.  **用户体验至上 (User Experience is Paramount)**: 架构的复杂性必须服务于前端的简洁性。用户应该感受到的是流畅的对话、透明的过程和智能的响应，而不是后台的技术细节。

#### **3. 系统架构蓝图 (System Architecture Blueprint)**

我们采用基于**“消息总线”的分布式微服务架构**。

```
+--------------------------+
|  移动应用 (React Native)   |
| - UI/VUI/Camera          |
| - 状态/结果实时渲染       |
+-----------+--------------+
            | (WebSocket - Real-time)
+-----------v--------------+
|   核心服务网关 (FastAPI)   |
+-----------+--------------+
            | (Internal Call)
+-----------v--------------+
| 核心协调Agent (Orchestrator)|
| - LangGraph驱动的决策流   |
| - 异步任务追踪 (Redis)    |
| - 记忆模块 (Memory I/O)    |
+-----------+--------------+
            | (Publish/Subscribe)
+-----------v--------------+
| 智能体通信总线 (RabbitMQ)  |
| - A2A消息协议路由         |
+--------------------------+
      |          |          | (A2A Protocol Messages)
+-----v---+  +---v----+  +---v----+
| 视觉Agent |  | 搜索Agent |  | 天气Agent |
| (独立微服务)|  | (独立微服务)|  |(独立微服务)|
+---------+  +--------+  +--------+
```

#### **4. 关键技术选型 (Key Technology Stack)**

| 类别 | 技术选型 | 核心理由 |
| :--- | :--- | :--- |
| **移动端** | React Native | 跨平台，生态成熟，原生能力调用便捷。 |
| **核心服务网关** | FastAPI | 异步高性能，完美支撑WebSocket和大量I/O。 |
| **核心Agent编排** | LangGraph | 强大的内部逻辑、循环和状态管理能力。 |
| **LLM引擎** | DeepSeek | 顶尖的语言理解、推理和函数调用能力。 |
| **Agent间通信** | RabbitMQ | 工业级消息队列，实现系统解耦、异步通信和可靠路由。 |
| **A2A通信协议** | 自定义JSON Schema | 遵循A2A思想，轻量、灵活、可控。 |
| **长期记忆** | LangChain Memory + ChromaDB | 成熟的持久化记忆方案，实现个性化和上下文感知。 |
| **任务状态追踪**| Redis | 高性能键值存储，用于追踪所有异步任务的实时状态。 |

#### **5. 核心用户体验流程 (Core User Experience Flow)**

**场景: 用户对着手机说：“帮我看看这个车牌是什么，然后查一下它的归属地。”**

*   **[T+0.0s]**: 用户说完。App通过设备ASR转为文本，连同一帧摄像头画面，通过WebSocket发送给核心服务网关。
*   **[T+0.5s]**: 核心协调Agent接收请求，立刻创建任务ID `task-plate-123`，存入Redis，并立即通过WebSocket回复App：`{status: "PROCESSING", message: "好的，正在识别车牌..."}`。App播放语音并显示处理动画。
*   **[T+1.0s]**: Orchestrator判断需要“视觉识别”能力，构造A2A消息`{target: "vision_ocr", payload: {image_data}}`，发布到RabbitMQ。
*   **[T+3.0s]**: 独立的视觉Agent收到任务，处理后将结果`{plate_number: "沪A·88888"}`通过总线发回。
*   **[T+3.2s]**: Orchestrator收到车牌号。它**不会立刻返回给用户**，因为任务还没结束。它在Redis中更新任务状态，并决策下一步需要“信息查询”能力。
*   **[T+3.5s]**: Orchestrator再次向App推送中间状态：`{status: "PROCESSING", message: "车牌是沪A·88888，正在为您查询归属地..."}`。用户听到连贯的反馈。
*   **[T+3.6s]**: Orchestrator构造新的A2A消息`{target: "info_search", payload: {query: "车牌沪A归属地"}}`，发布到RabbitMQ。
*   **[T+5.5s]**: 独立的搜索Agent收到任务，执行搜索后将结果`{location: "上海市"}`通过总线发回。
*   **[T+5.7s]**: Orchestrator收到最终结果，将任务在Redis中标记为`COMPLETED`。
*   **[T+6.0s]**: Orchestrator将完整的、最终的成功消息推送给App：`{status: "SUCCESS", payload: {plate: "沪A·88888", location: "上海市"}}`。App用TTS清晰地播报最终结果，并可能展示一张包含所有信息的卡片。

#### **6. 实施路线图 (Implementation Roadmap)**

*   第一周：构建并验证“中枢神经系统”
目标: 构建一个本地的、自洽的、由LangGraph驱动的智能核心。
任务:
初始化FastAPI项目。
集成LangChain和LangGraph。
开发两个真实的、本地的Python函数作为“内置工具”（例如，一个local_calculator_tool和一个local_text_parser_tool）。它们不是“伪”的，而是Orchestrator未来会永久拥有的内部基础能力。
构建LangGraph图，让其能根据用户输入，智能地决策并调用这两个真实的本地工具。
周日成果: 你拥有了一个真正能运行、能决策、能调用自身工具的智能核心。它是我们系统的“大脑”，并且已经具备了独立的思考能力。
第二周：连接“第一条神经”——建立对外通信
目标: 将“大脑”连接到“身体”的神经总线上，并成功与第一个外部“器官”对话。
任务:
使用Docker启动RabbitMQ和Redis。
定义V1版的A2A JSON Schema。
开发第一个独立的专业Agent微服务（weather_agent_service），让它具备连接RabbitMQ并处理一个真实天气API调用的能力。
在Orchestrator中，添加一个名为agent_bus_tool的真实工具。这个工具的唯一职责就是将任务打包成A2A消息发送到RabbitMQ。
修改LangGraph的决策逻辑：当LLM判断需要天气信息时，它应该调用agent_bus_tool。
周日成果: 你拥有了一个包含两个独立服务（Orchestrator + Weather Agent）的、真正的分布式系统。数据通过RabbitMQ这条“神经”在它们之间真实地流动。
第三周：扩展“神经网络”——验证联邦的可扩展性
目标: 证明我们的系统架构可以轻松地“长出”新的器官，而无需对大脑进行大手术。
任务:
开发第二个独立的专业Agent微服务（search_agent_service），封装一个真实的搜索引擎API。
几乎无需修改Orchestrator的代码，只需在初始化时告诉LangGraph的LLM：“你的工具箱里现在多了一项名为‘search’的外部能力。”
测试并验证Orchestrator现在可以根据任务，智能地将工作委派给天气或搜索Agent。
周日成果: 你拥有了一个初具规模的智能体联邦。你亲手验证了它的核心优势——可扩展性。
第四周：赋予“长期记忆”与“灵魂”
目标: 为系统装上记忆，使其从一个聪明的工具变为一个有上下文感知能力的伙伴。
任务:
在Orchestrator中，集成ChromaDB和LangChain的Memory模块。
修改LangGraph的初始节点，使其在处理任何任务前，都先从ChromaDB中检索相关记忆，并将记忆注入到提示词中。
通过连续对话来测试记忆功能，例如：“我最喜欢的城市是巴黎。” -> “那个城市的天气怎么样？”
周日成果: 你的智能体联邦拥有了记忆，交互体验实现了质的飞跃。

*   **阶段四：生态扩展与优化 (持续)**
    *   [ ] 不断开发新的独立专业Agent。
    *   [ ] 优化A2A协议，增加更丰富的元数据和能力。
    *   [ ] 优化UI/UX，提供更丰富的可视化效果。

---