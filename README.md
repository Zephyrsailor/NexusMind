# NexusMind - 智能体语音摄像头平台

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-latest-red.svg)

## 🎯 项目介绍

NexusMind 是一个基于**语音和视觉**的智能体协调平台，提供实时的多模态交互体验。系统通过智能协调器统一管理语音录制、语音识别、图像捕获、图像分析等核心功能。

## ✨ 核心功能

### 🎤 语音智能体
- **录音功能**: 支持指定时长的高质量录音
- **语音识别**: 实时语音转文字（支持中英文）
- **智能识别**: 一键录音并自动识别为文字
- **设备检测**: 自动检测可用麦克风设备

### 📷 摄像头智能体  
- **图像捕获**: 高清拍照功能
- **连续拍摄**: 支持多张连拍
- **图像分析**: 自动分析亮度、对比度、色彩等
- **人脸检测**: 基于OpenCV的实时人脸识别
- **设备管理**: 多摄像头设备支持

### 🧠 智能协调器
- **意图理解**: 智能分析用户指令
- **任务调度**: 自动选择合适的Agent执行任务
- **实时反馈**: WebSocket实时状态更新
- **错误处理**: 优雅的错误处理和恢复

## 🚀 快速开始

### 一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/your-repo/NexusMind.git
cd NexusMind

# 运行快速启动脚本
python quick_start.py
```

快速启动脚本会自动：
- ✅ 检查Python环境
- ✅ 安装所有依赖
- ✅ 配置环境变量
- ✅ 运行系统测试
- ✅ 启动服务器并打开测试页面

### 手动安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env

# 3. 测试系统
python test_system.py

# 4. 启动服务器
python run_server.py
```

## 🎯 功能演示

### 语音功能测试
```bash
# 通过WebSocket测试客户端或API发送：

"录音5秒"           # 录制5秒音频
"录音并识别"        # 录音并转换为文字
"语音转文字"        # 语音识别功能
```

### 摄像头功能测试
```bash
"拍照"             # 单张拍照
"拍照并分析"        # 拍照并分析图像质量
"拍3张照片"         # 连续拍摄3张
"人脸检测"          # 拍照并检测人脸
```

### 系统查询
```bash
"设备状态"          # 查看语音和摄像头设备状态
"帮助"             # 获取功能说明
"功能"             # 查看所有可用功能
```

## 🌐 测试方式

### 1. WebSocket测试客户端
打开 `test_client.html` 进行交互式测试：
- 🔌 连接到WebSocket服务器
- 💬 发送语音/摄像头指令
- 📊 实时查看处理结果

### 2. API接口测试
```bash
# 健康检查
curl http://localhost:8080/health

# 系统状态
curl http://localhost:8080/api/v1/status

# 录音接口
curl -X POST http://localhost:8080/api/v1/audio/record

# 拍照接口  
curl -X POST http://localhost:8080/api/v1/camera/capture
```

### 3. 系统测试脚本
```bash
python test_system.py
```

## �️ 技术架构

```
用户界面 (WebSocket/HTTP)
        ↓
   智能协调器 (SimpleOrchestrator)
        ↓
    意图分析 & 任务调度
        ↓
  ┌─────────┴─────────┐
  ↓                   ↓
🎤 语音Agent          📷 摄像头Agent
• 录音录制            • 图像捕获  
• 语音识别            • 图像分析
• 设备管理            • 人脸检测
```

## 📚 核心组件

| 组件 | 功能 | 技术栈 |
|------|------|--------|
| **智能协调器** | 意图分析、任务调度 | Python异步编程 |
| **语音Agent** | 录音、语音识别 | SpeechRecognition, PyAudio |
| **摄像头Agent** | 拍照、图像分析 | OpenCV, PIL |
| **API服务** | REST & WebSocket | FastAPI, Uvicorn |
| **数据模型** | 类型安全 | Pydantic |

## 🔧 系统要求

- **Python**: 3.8+
- **操作系统**: Windows/Linux/macOS
- **硬件**: 
  - 麦克风（语音功能）
  - 摄像头（图像功能）
- **权限**: 摄像头和麦克风访问权限

## 📊 当前状态

### ✅ 已完成功能
- [x] 语音录制与识别
- [x] 摄像头拍照与分析
- [x] 智能意图理解
- [x] 实时WebSocket通信
- [x] REST API接口
- [x] 人脸检测
- [x] 设备状态管理
- [x] 错误处理与恢复

### 🔄 开发中功能
- [ ] 语音合成(TTS)
- [ ] 高级图像识别
- [ ] 多语言支持优化
- [ ] 移动端应用

### 📅 未来计划  
- [ ] RabbitMQ消息总线集成
- [ ] A2A协议外部智能体接入
- [ ] 长期记忆系统(ChromaDB)
- [ ] React Native移动应用

## 🎮 使用场景

1. **语音助手**: "录音5秒并识别内容"
2. **图像分析**: "拍照分析图像质量和色彩"
3. **人脸识别**: "拍照检测画面中的人脸"
4. **设备管理**: "查看摄像头和麦克风状态"
5. **多模态交互**: 语音指令 + 视觉反馈

## 🔍 故障排除

### 常见问题

**Q: 麦克风不可用？**
A: 检查系统麦克风权限，确保设备未被其他应用占用

**Q: 摄像头无法使用？**  
A: 检查摄像头连接，确认系统摄像头权限

**Q: 语音识别失败？**
A: 确保网络连接正常（使用Google Speech Recognition）

**Q: 依赖安装失败？**
A: 使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/`

## 🤝 开发指南

### 添加新功能
1. 在相应Agent中实现核心逻辑
2. 在协调器中添加意图识别
3. 更新API接口和文档
4. 添加测试用例

### 扩展Agent能力
```python
# 在audio_agent.py或camera_agent.py中添加新方法
async def new_feature(self, params):
    # 实现新功能
    return result
```

## 📄 许可证

本项目基于 MIT 许可证开源。

## 🔗 相关链接

- [API文档](http://localhost:8080/docs) (启动服务器后访问)
- [测试客户端](test_client.html)
- [架构设计](docs/architect.md)

---

**🌟 体验前沿的多模态智能体交互！语音+视觉，让AI真正理解你的世界。**
