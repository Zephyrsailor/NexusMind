# NexusMind 多模态处理指南

本指南详细介绍如何使用 NexusMind 的专业多模态处理功能，包括语音、图像、视频等多种输入类型的处理。

## 🌟 核心特性

### 专业级语音处理
- **多提供者支持**: OpenAI Whisper API、Google Speech、Azure Speech、本地Whisper
- **智能回退机制**: 自动选择最佳可用服务
- **高质量转录**: 支持多语言、实时转录、说话人分离
- **专业功能**: 会议记录、语音命令识别、情感分析

### 专业级视觉处理
- **多模型集成**: GPT-4V、Claude Vision、Google Vision、Azure Vision
- **全面分析能力**: 场景理解、物体检测、OCR、人脸分析
- **专业场景**: 文档分析、艺术分析、技术分析、医学图像
- **共识决策**: 多提供者结果融合，提高准确性

### 统一多模态框架
- **智能路由**: 根据输入类型和质量自动选择最佳处理方案
- **质量评估**: 实时评估输入质量并提供改进建议
- **格式兼容**: 支持多种音频、图像、视频格式
- **性能优化**: 并行处理、缓存机制、资源管理

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制并修改）
cp .env.example .env
```

### 2. 配置API密钥

编辑 `.env` 文件，添加您的API密钥：

```env
# OpenAI服务 (推荐)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic Claude服务
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Google Cloud服务 (可选)
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# Azure服务 (可选)
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=your-region
AZURE_VISION_KEY=your-azure-vision-key
```

### 3. 启动服务

```bash
# 启动NexusMind服务
python run_server.py

# 或使用uvicorn
uvicorn backend.api.main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. 运行演示

```bash
# 运行完整多模态演示
python examples/multimodal_demo.py

# 快速演示模式
python examples/multimodal_demo.py --quick

# 指定服务地址
python examples/multimodal_demo.py --url http://localhost:8080
```

## 📝 API 使用指南

### 基础API调用

```python
import httpx
import base64

# 创建客户端
client = httpx.AsyncClient()

# 文本请求
response = await client.post("http://localhost:8080/api/v1/chat", json={
    "message": "你好，请介绍你的多模态能力"
})

# 图像分析请求
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

response = await client.post("http://localhost:8080/api/v1/chat", json={
    "message": "请分析这张图片",
    "image_data": image_data
})

# 语音转录请求
with open("audio.wav", "rb") as f:
    audio_data = base64.b64encode(f.read()).decode()

response = await client.post("http://localhost:8080/api/v1/chat", json={
    "message": "请转录这段音频",
    "audio_data": audio_data
})
```

### 多模态输入（推荐）

使用新的 `inputs` 格式可以同时传递多种类型的媒体：

```python
response = await client.post("http://localhost:8080/api/v1/chat", json={
    "message": "请同时分析这张图片和音频",
    "inputs": [
        {
            "type": "image",
            "data": image_base64,
            "format": "jpg"
        },
        {
            "type": "audio",
            "data": audio_base64,
            "format": "wav",
            "duration": 10.5
        }
    ]
})
```

### 专业功能参数

```python
# 高质量图像分析
response = await client.post("http://localhost:8080/api/v1/chat", json={
    "message": "请进行专业级图像分析",
    "image_data": image_data,
    "metadata": {
        "quality_mode": "high",
        "analysis_type": "comprehensive",
        "preferred_provider": "gpt4_vision"
    }
})

# 专业语音转录
response = await client.post("http://localhost:8080/api/v1/chat", json={
    "message": "请进行专业语音转录",
    "audio_data": audio_data,
    "metadata": {
        "transcription_quality": "high",
        "language": "zh-CN",
        "enable_speaker_diarization": True
    }
})
```

## 🔧 服务配置

### 语音服务配置

```env
# 本地Whisper配置
WHISPER_MODEL_SIZE=base  # tiny, base, small, medium, large
ENABLE_LOCAL_WHISPER=true

# 服务质量配置
HIGH_QUALITY_THRESHOLD=0.8
ENABLE_FALLBACK_PROVIDERS=true
MAX_PROCESSING_TIME_SECONDS=60
```

### 文件大小限制

```env
# 媒体文件限制
MAX_IMAGE_SIZE_MB=10
MAX_AUDIO_DURATION_SECONDS=300
MAX_VIDEO_DURATION_SECONDS=600
```

### 性能优化

```env
# 并发和超时配置
MAX_CONCURRENT_TASKS=100
TASK_TIMEOUT_SECONDS=300

# 临时文件目录
TEMP_DIR=/tmp/nexusmind
```

## 💡 使用场景示例

### 1. 会议记录系统

```python
# 开始会议记录
response = await client.post("/api/v1/chat", json={
    "message": "开始会议记录",
    "metadata": {"session_type": "meeting"}
})

# 处理会议音频片段
for audio_chunk in meeting_audio_chunks:
    response = await client.post("/api/v1/chat", json={
        "message": "转录会议内容",
        "audio_data": audio_chunk,
        "metadata": {
            "session_id": meeting_id,
            "chunk_index": i,
            "speaker_diarization": True
        }
    })
```

### 2. 文档数字化

```python
# 文档图像OCR
response = await client.post("/api/v1/chat", json={
    "message": "提取文档中的文字内容",
    "image_data": document_image,
    "metadata": {
        "analysis_type": "document_ocr",
        "language": "zh-CN",
        "preserve_layout": True
    }
})
```

### 3. 多媒体内容分析

```python
# 综合媒体分析
response = await client.post("/api/v1/chat", json={
    "message": "分析这个多媒体内容",
    "inputs": [
        {"type": "image", "data": thumbnail_image},
        {"type": "audio", "data": audio_track},
        {"type": "text", "data": description_text}
    ],
    "metadata": {
        "analysis_depth": "comprehensive",
        "generate_summary": True
    }
})
```

### 4. 实时音视频处理

```python
# 实时语音转文字
async def process_real_time_audio():
    async for audio_chunk in audio_stream:
        response = await client.post("/api/v1/chat", json={
            "message": "实时转录",
            "audio_data": audio_chunk,
            "metadata": {
                "real_time": True,
                "partial_results": True
            }
        })
        
        # 处理部分结果
        if response.json().get("status") == "processing":
            partial_text = response.json().get("payload", {}).get("partial_text")
            print(f"部分转录: {partial_text}")
```

## 🔍 监控和调试

### 获取系统状态

```python
# 检查服务状态
status = await client.get("/api/v1/status")
print(status.json())

# 获取可用智能体
agents = await client.get("/api/v1/agents")
print(agents.json())

# 查看任务状态
task_status = await client.get(f"/api/v1/tasks/{task_id}")
print(task_status.json())
```

### 性能监控

```python
# 获取处理统计
from backend.core.multimodal_processor import get_multimodal_processor

processor = await get_multimodal_processor()
stats = processor.get_processing_stats()
print(f"总处理数: {stats['total_processed']}")
print(f"平均处理时间: {stats['average_processing_time']:.2f}秒")
```

## 🛠️ 故障排除

### 常见问题

1. **API密钥配置问题**
   ```bash
   # 检查环境变量
   python -c "from backend.core.config import settings; print(settings.openai_api_key)"
   ```

2. **依赖库缺失**
   ```bash
   # 安装音频处理库
   pip install librosa soundfile
   
   # 安装视频处理库
   pip install moviepy
   
   # 安装Whisper
   pip install openai-whisper
   ```

3. **内存不足**
   ```env
   # 调整处理限制
   MAX_IMAGE_SIZE_MB=5
   MAX_CONCURRENT_TASKS=50
   ```

4. **服务连接问题**
   ```python
   # 测试连接
   response = await client.get("http://localhost:8080/health")
   assert response.status_code == 200
   ```

### 调试模式

```env
# 启用调试模式
DEBUG=true
LOG_LEVEL=DEBUG
```

### 性能优化建议

1. **使用适当的模型大小**
   - 对于实时应用，使用 `whisper_model_size=tiny` 或 `base`
   - 对于高质量转录，使用 `medium` 或 `large`

2. **启用缓存机制**
   - 重复的输入会被缓存，提高响应速度

3. **合理设置并发限制**
   - 根据硬件资源调整 `MAX_CONCURRENT_TASKS`

4. **使用合适的服务提供者**
   - 本地Whisper适合隐私敏感场景
   - 云服务适合高质量要求

## 📊 性能基准

### 处理速度参考

| 输入类型 | 大小 | 本地处理 | 云服务 |
|---------|------|----------|--------|
| 图像 | 1MB | 1-3秒 | 2-5秒 |
| 音频 | 1分钟 | 5-15秒 | 3-8秒 |
| 视频 | 1分钟 | 30-60秒 | 20-40秒 |

### 质量评估标准

- **语音转录准确率**: >95% (清晰语音)
- **图像识别准确率**: >90% (标准场景)
- **OCR准确率**: >98% (清晰文档)

## 🔄 版本更新

### 最新功能 (v1.0.0)

- ✅ 专业语音处理智能体
- ✅ 专业视觉处理智能体
- ✅ 多模态统一处理框架
- ✅ 智能回退机制
- ✅ 质量评估系统
- ✅ 多提供者集成

### 规划中功能

- 🔄 实时流式处理
- 🔄 视频内容分析
- 🔄 3D模型处理
- 🔄 多语言界面
- 🔄 插件系统

---

更多详细信息请参考：
- [API文档](./api-reference.md)
- [架构设计](./architect.md)
- [部署指南](./deployment.md)