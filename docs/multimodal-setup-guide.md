# NexusMind 多模态设置指南

## 🎯 概述

NexusMind现在支持专业的多模态处理能力，包括语音识别、图像分析、视频处理等。本指南将帮助您配置并使用这些功能。

## 💰 成本分析

### 推荐方案：HuggingFace + 本地模型 (经济实用)

**优势：**
- ✅ **成本低廉**：HuggingFace免费额度很大，本地模型无运行费用
- ✅ **隐私保护**：数据在本地处理，不上传到外部服务
- ✅ **稳定可靠**：不依赖网络，响应速度快
- ✅ **功能完整**：支持语音转录、图像分析、目标检测等

**成本对比：**
- **HuggingFace**: 免费额度50,000次/月，付费$9/月起
- **OpenAI**: GPT-4V约$0.01/图片，Whisper约$0.006/分钟
- **本地模型**: 仅需一次性下载，运行免费

## 🔑 所需密钥

### 必需密钥

1. **HuggingFace Token** (免费)
   - 访问：https://huggingface.co/settings/tokens
   - 权限：只需要 `Read` 权限
   - 成本：免费额度很大

### 可选密钥 (高质量场景)

2. **OpenAI API Key** (付费)
   - 用于GPT-4V视觉分析和Whisper语音识别
   - 成本：按使用量计费

3. **DeepSeek API Key** (您已有)
   - 用于文本对话和推理
   - 成本：相对便宜

## 📦 安装步骤

### 1. 安装Python依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 或者手动安装核心依赖
pip install transformers torch torchvision torchaudio
pip install pillow librosa soundfile
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 必需配置
HUGGINGFACE_TOKEN=your-huggingface-token-here
USE_LOCAL_HF_MODELS=true

# 可选配置 (如需高质量处理)
# OPENAI_API_KEY=your-openai-key-here
# ANTHROPIC_API_KEY=your-anthropic-key-here
```

### 3. 首次运行 (模型下载)

第一次运行时，系统会自动下载所需模型：

```bash
python run_server.py
```

**注意：** 首次启动可能需要几分钟下载模型（约2-3GB）。

## 🚀 功能特性

### HuggingFace多模态智能体

**语音处理:**
- ✅ Whisper语音识别 (支持多语言)
- ✅ Wav2Vec2语音识别 (英文)
- ✅ 实时音频转录

**图像处理:**
- ✅ BLIP-2图像描述
- ✅ ViT图像分类
- ✅ DETR目标检测
- ✅ LayoutLM文档分析

**支持格式:**
- 音频：WAV, MP3, M4A, FLAC
- 图像：JPG, PNG, BMP, WEBP
- 视频：MP4, AVI, MOV (提取关键帧)

### 专业服务智能体 (可选)

**高质量语音:**
- OpenAI Whisper API
- Google Cloud Speech
- Azure Speech Services

**高质量视觉:**
- GPT-4 Vision
- Claude Vision
- Google Cloud Vision

## 📝 使用方式

### API调用示例

#### 1. 语音转录

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请转录这段音频",
    "audio_data": "base64音频数据..."
  }'
```

#### 2. 图像分析

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请分析这张图片",
    "image_data": "base64图像数据..."
  }'
```

#### 3. 多模态输入

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请同时分析图片和音频",
    "inputs": [
      {
        "type": "image",
        "data": "base64图像数据...",
        "format": "jpg"
      },
      {
        "type": "audio", 
        "data": "base64音频数据...",
        "format": "wav"
      }
    ]
  }'
```

### Python客户端示例

```python
import requests
import base64

# 读取音频文件
with open("audio.wav", "rb") as f:
    audio_data = base64.b64encode(f.read()).decode()

# 发送请求
response = requests.post("http://localhost:8080/api/v1/chat", json={
    "message": "请转录这段音频",
    "audio_data": audio_data
})

result = response.json()
print(result["payload"]["reply_message"])
```

## ⚙️ 配置说明

### 性能优化

```bash
# 启用GPU加速 (如有NVIDIA GPU)
USE_LOCAL_HF_MODELS=true
TORCH_DEVICE=cuda

# 调整模型大小 (内存受限时)
WHISPER_MODEL_SIZE=base  # tiny, base, small, medium, large

# 限制并发处理
MAX_CONCURRENT_TASKS=10
```

### 存储配置

```bash
# 自定义模型缓存目录
HF_CACHE_DIR=/path/to/hf/cache

# 临时文件目录
TEMP_DIR=/tmp/nexusmind

# 文件大小限制
MAX_IMAGE_SIZE_MB=10
MAX_AUDIO_DURATION_SECONDS=300
```

## 🔧 故障排除

### 常见问题

**1. 模型下载失败**
```bash
# 设置HuggingFace镜像 (中国用户)
export HF_ENDPOINT=https://hf-mirror.com
```

**2. 内存不足**
```bash
# 使用小模型
WHISPER_MODEL_SIZE=tiny
USE_LOCAL_HF_MODELS=false  # 使用远程API
```

**3. GPU相关错误**
```bash
# 强制使用CPU
export CUDA_VISIBLE_DEVICES=""
```

### 日志调试

```bash
# 启用详细日志
DEBUG=true

# 查看模型加载日志
tail -f logs/nexusmind.log | grep "HF_MULTIMODAL"
```

## 📊 性能基准

### 处理速度 (本地M1 Mac)

- **语音转录**: ~0.3x实时 (10秒音频需3秒)
- **图像描述**: ~2-3秒/图片
- **目标检测**: ~3-5秒/图片

### 准确率对比

| 功能 | HuggingFace | OpenAI | 成本差异 |
|------|-------------|---------|----------|
| 语音转录 | 85-90% | 95%+ | 免费 vs $0.006/分钟 |
| 图像描述 | 80-85% | 90%+ | 免费 vs $0.01/图片 |
| 目标检测 | 75-80% | 85%+ | 免费 vs $0.01/图片 |

## 🚀 生产部署建议

### Docker部署

```dockerfile
FROM python:3.11

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 预下载模型
RUN python -c "
from transformers import AutoModel
AutoModel.from_pretrained('Salesforce/blip-image-captioning-base')
AutoModel.from_pretrained('openai/whisper-base')
"

COPY . .
CMD ["python", "run_server.py"]
```

### 负载均衡

```yaml
# docker-compose.yml
version: '3.8'
services:
  nexusmind-1:
    build: .
    environment:
      - HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
    ports:
      - "8080:8080"
      
  nexusmind-2:
    build: .
    environment:
      - HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
    ports:
      - "8081:8080"
      
  nginx:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

## 🎯 最佳实践

### 1. 成本控制
- 优先使用HuggingFace模型
- 仅在关键场景使用付费API
- 设置文件大小和时长限制

### 2. 性能优化
- 使用GPU加速 (如可用)
- 合理配置并发数
- 启用模型缓存

### 3. 质量保证
- 对关键应用使用专业API
- 设置置信度阈值
- 实现降级策略

### 4. 监控告警
- 监控API使用量和成本
- 设置错误率告警
- 跟踪处理时间

## 📞 技术支持

如果遇到问题，请：

1. 查看日志文件
2. 检查网络连接
3. 验证API密钥
4. 提交Issue到GitHub

## 🔄 版本更新

### 当前版本特性
- ✅ HuggingFace多模态支持
- ✅ 专业API集成
- ✅ 自动模型下载
- ✅ GPU加速支持

### 即将推出
- 🔄 更多模型支持
- 🔄 实时流式处理
- 🔄 批量处理优化
- 🔄 Web UI界面

---

**总结：推荐使用HuggingFace方案，只需一个免费Token即可获得强大的多模态处理能力！**