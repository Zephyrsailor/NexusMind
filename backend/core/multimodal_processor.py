"""
多模态处理器
统一处理文本、语音、图像、视频等多种输入模态
提供智能路由、格式转换、质量评估等功能
"""
import asyncio
import base64
import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
import io
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path

# 媒体处理
from PIL import Image
import cv2
import numpy as np

# 音频处理
try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False

# 视频处理
try:
    import moviepy.editor as mp
    VIDEO_PROCESSING_AVAILABLE = True
except ImportError:
    VIDEO_PROCESSING_AVAILABLE = False

from ..models.schemas import UserRequest, MediaInput, InputType, A2AMessage
from ..core.config import settings
from .tools import safe_base64_decode

logger = logging.getLogger(__name__)


def safe_decode_media_data(data: str) -> bytes:
    """安全解码媒体数据"""
    if not data:
        return b''
    
    decoded_bytes, success = safe_base64_decode(data)
    if not success:
        raise ValueError("Base64 解码失败")
    return decoded_bytes


class ProcessingQuality(Enum):
    """处理质量级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class MediaFormat(Enum):
    """媒体格式"""
    # 图像格式
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"
    
    # 音频格式
    WAV = "wav"
    MP3 = "mp3"
    AAC = "aac"
    FLAC = "flac"
    OGG = "ogg"
    
    # 视频格式
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    WEBM = "webm"
    
    # 文档格式
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    processed_data: Optional[bytes] = None
    metadata: Dict[str, Any] = None
    quality_score: float = 0.0
    processing_time: float = 0.0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MediaAnalysis:
    """媒体分析结果"""
    media_type: InputType
    format: str
    duration: Optional[float] = None
    dimensions: Optional[Tuple[int, int]] = None
    file_size: int = 0
    quality_metrics: Dict[str, float] = None
    encoding_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.quality_metrics is None:
            self.quality_metrics = {}
        if self.encoding_info is None:
            self.encoding_info = {}


class MultimodalProcessor:
    """多模态处理器"""
    
    def __init__(self):
        self.processing_stats = {
            "total_processed": 0,
            "by_type": {},
            "average_processing_time": 0.0
        }
        self.cache = {}
        self.max_cache_size = 100
        self.whisper_model = None  # OpenAI Whisper
        self.mllm_model = None  # 多模态大模型
        self.mllm_processor = None
        self.use_ollama = True  # 默认启用Ollama进行图像分析
        
    async def initialize(self):
        """初始化处理器"""
        logger.info("初始化多模态处理器")
        
        # 检查依赖库
        self._check_dependencies()
        
        # 初始化临时目录
        self.temp_dir = Path(tempfile.gettempdir()) / "nexusmind_multimodal"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 初始化 Whisper
        await self._init_whisper()
        
        # 初始化多模态大模型
        await self._init_multimodal_llm()
        
        logger.info(f"多模态处理器初始化完成，临时目录: {self.temp_dir}")
    
    def _check_dependencies(self):
        """检查依赖库"""
        deps = {
            "音频处理": AUDIO_PROCESSING_AVAILABLE,
            "视频处理": VIDEO_PROCESSING_AVAILABLE
        }
        
        for name, available in deps.items():
            if available:
                logger.info(f"✓ {name} 支持已启用")
            else:
                logger.warning(f"✗ {name} 支持未启用，部分功能可能不可用")
    
    async def process_request(self, request: UserRequest) -> Dict[str, Any]:
        """处理多模态请求"""
        logger.info(f"\n[MULTIMODAL_PROCESSOR] {'='*60}")
        logger.info(f"[MULTIMODAL_PROCESSOR] 开始处理多模态请求")
        logger.info(f"[MULTIMODAL_PROCESSOR] 输入数量: {len(request.inputs)}")
        
        start_time = datetime.now()
        results = {
            "processing_summary": {
                "total_inputs": len(request.inputs),
                "processed_inputs": 0,
                "failed_inputs": 0,
                "processing_time": 0.0
            },
            "processed_media": [],
            "routing_decisions": [],
            "quality_assessments": [],
            "recommendations": []
        }
        
        try:
            # 处理每个媒体输入
            for i, media_input in enumerate(request.inputs):
                logger.info(f"[MULTIMODAL_PROCESSOR] 处理输入 {i+1}/{len(request.inputs)}: {media_input.type}")
                
                try:
                    # 分析媒体
                    analysis = await self._analyze_media(media_input)
                    
                    # 预处理
                    processed = await self._preprocess_media(media_input, analysis)
                    
                    # 质量评估
                    quality = await self._assess_quality(media_input, analysis)
                    
                    # 路由决策
                    routing = await self._make_routing_decision(media_input, analysis, quality)
                    
                    # 如果有 HF 处理器，尝试进行 AI 分析
                    ai_analysis = None
                    if self.hf_processor and processed.success:
                        ai_analysis = await self._perform_ai_analysis(media_input, processed.processed_data)
                    
                    results["processed_media"].append({
                        "index": i,
                        "type": media_input.type,
                        "analysis": analysis.__dict__,
                        "processed": processed.__dict__,
                        "quality": quality,
                        "routing": routing,
                        "ai_analysis": ai_analysis
                    })
                    
                    results["quality_assessments"].append(quality)
                    results["routing_decisions"].append(routing)
                    results["processing_summary"]["processed_inputs"] += 1
                    
                except Exception as e:
                    logger.error(f"[MULTIMODAL_PROCESSOR] 处理输入 {i+1} 失败: {e}")
                    results["processing_summary"]["failed_inputs"] += 1
                    results["processed_media"].append({
                        "index": i,
                        "type": media_input.type,
                        "error": str(e)
                    })
            
            # 生成整体建议
            results["recommendations"] = await self._generate_recommendations(results)
            
            # 更新统计
            processing_time = (datetime.now() - start_time).total_seconds()
            results["processing_summary"]["processing_time"] = processing_time
            self._update_stats(request.inputs, processing_time)
            
            logger.info(f"[MULTIMODAL_PROCESSOR] 处理完成，耗时: {processing_time:.2f}秒")
            logger.info(f"[MULTIMODAL_PROCESSOR] {'='*60}\n")
            
            return results
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 处理失败: {e}", exc_info=True)
            raise
    
    async def _analyze_media(self, media_input: MediaInput) -> MediaAnalysis:
        """分析媒体输入"""
        logger.info(f"[MULTIMODAL_PROCESSOR] 分析媒体: {media_input.type}")
        
        if media_input.data:
            # 从Base64数据分析 - 使用安全解码
            media_bytes, success = safe_base64_decode(media_input.data)
            if not success:
                raise ValueError("Base64 解码失败")
            return await self._analyze_bytes(media_bytes, media_input.type, media_input.format)
        elif media_input.url:
            # 从URL分析
            return await self._analyze_url(media_input.url, media_input.type)
        else:
            raise ValueError("No data or URL provided")
    
    async def _analyze_bytes(self, data: bytes, media_type: InputType, format_hint: str = None) -> MediaAnalysis:
        """分析字节数据"""
        analysis = MediaAnalysis(
            media_type=media_type,
            format=format_hint or "unknown",
            file_size=len(data)
        )
        
        try:
            if media_type == InputType.IMAGE:
                analysis = await self._analyze_image_bytes(data, analysis)
            elif media_type == InputType.AUDIO:
                analysis = await self._analyze_audio_bytes(data, analysis)
            elif media_type == InputType.VIDEO:
                analysis = await self._analyze_video_bytes(data, analysis)
            else:
                logger.warning(f"[MULTIMODAL_PROCESSOR] 未知媒体类型: {media_type}")
        
        except Exception as e:
            logger.warning(f"[MULTIMODAL_PROCESSOR] 媒体分析失败: {e}")
        
        return analysis
    
    async def _analyze_image_bytes(self, data: bytes, analysis: MediaAnalysis) -> MediaAnalysis:
        """分析图像字节数据"""
        try:
            # 使用PIL分析图像
            image = Image.open(io.BytesIO(data))
            
            analysis.format = image.format.lower() if image.format else "unknown"
            analysis.dimensions = (image.width, image.height)
            
            # 计算质量指标
            analysis.quality_metrics = {
                "resolution": image.width * image.height,
                "aspect_ratio": image.width / image.height,
                "bit_depth": self._get_bit_depth(image),
                "compression_ratio": len(data) / (image.width * image.height * 3)
            }
            
            # 编码信息
            analysis.encoding_info = {
                "mode": image.mode,
                "has_transparency": image.mode in ('RGBA', 'LA') or 'transparency' in image.info,
                "animated": getattr(image, 'is_animated', False)
            }
            
            logger.info(f"[MULTIMODAL_PROCESSOR] 图像分析: {analysis.dimensions}, 格式: {analysis.format}")
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 图像分析失败: {e}")
        
        return analysis
    
    async def _analyze_audio_bytes(self, data: bytes, analysis: MediaAnalysis) -> MediaAnalysis:
        """分析音频字节数据"""
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.warning("[MULTIMODAL_PROCESSOR] 音频处理库不可用")
            return analysis
        
        try:
            # 保存到临时文件进行分析
            temp_file = self.temp_dir / f"temp_audio_{datetime.now().timestamp()}.wav"
            with open(temp_file, 'wb') as f:
                f.write(data)
            
            # 使用librosa分析
            y, sr = librosa.load(str(temp_file))
            
            analysis.duration = len(y) / sr
            analysis.quality_metrics = {
                "sample_rate": sr,
                "channels": 1,  # librosa默认单声道
                "bit_rate": len(data) * 8 / analysis.duration,
                "rms_energy": float(np.sqrt(np.mean(y**2))),
                "zero_crossing_rate": float(np.mean(librosa.feature.zero_crossing_rate(y)))
            }
            
            analysis.encoding_info = {
                "duration_seconds": analysis.duration,
                "samples": len(y)
            }
            
            # 清理临时文件
            temp_file.unlink(missing_ok=True)
            
            logger.info(f"[MULTIMODAL_PROCESSOR] 音频分析: 时长 {analysis.duration:.2f}秒, 采样率 {sr}Hz")
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 音频分析失败: {e}")
        
        return analysis
    
    async def _analyze_video_bytes(self, data: bytes, analysis: MediaAnalysis) -> MediaAnalysis:
        """分析视频字节数据"""
        if not VIDEO_PROCESSING_AVAILABLE:
            logger.warning("[MULTIMODAL_PROCESSOR] 视频处理库不可用")
            return analysis
        
        try:
            # 保存到临时文件
            temp_file = self.temp_dir / f"temp_video_{datetime.now().timestamp()}.mp4"
            with open(temp_file, 'wb') as f:
                f.write(data)
            
            # 使用moviepy分析
            clip = mp.VideoFileClip(str(temp_file))
            
            analysis.duration = clip.duration
            analysis.dimensions = (int(clip.w), int(clip.h))
            analysis.quality_metrics = {
                "fps": clip.fps,
                "frame_count": int(clip.fps * clip.duration),
                "bit_rate": len(data) * 8 / analysis.duration,
                "resolution": clip.w * clip.h
            }
            
            analysis.encoding_info = {
                "has_audio": clip.audio is not None,
                "duration_seconds": analysis.duration
            }
            
            # 清理
            clip.close()
            temp_file.unlink(missing_ok=True)
            
            logger.info(f"[MULTIMODAL_PROCESSOR] 视频分析: {analysis.dimensions}, 时长 {analysis.duration:.2f}秒")
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 视频分析失败: {e}")
        
        return analysis
    
    async def _analyze_url(self, url: str, media_type: InputType) -> MediaAnalysis:
        """从URL分析媒体"""
        # 简化实现：从URL推断信息
        analysis = MediaAnalysis(
            media_type=media_type,
            format=self._extract_format_from_url(url)
        )
        
        logger.info(f"[MULTIMODAL_PROCESSOR] URL分析: {url}")
        return analysis
    
    def _extract_format_from_url(self, url: str) -> str:
        """从URL提取格式"""
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path
            return path.split('.')[-1].lower() if '.' in path else "unknown"
        except:
            return "unknown"
    
    def _get_bit_depth(self, image: Image.Image) -> int:
        """获取图像位深度"""
        mode_depths = {
            '1': 1, 'L': 8, 'P': 8, 'RGB': 24, 'RGBA': 32,
            'CMYK': 32, 'YCbCr': 24, 'LAB': 24, 'HSV': 24
        }
        return mode_depths.get(image.mode, 8)
    
    async def _preprocess_media(self, media_input: MediaInput, analysis: MediaAnalysis) -> ProcessingResult:
        """预处理媒体"""
        logger.info(f"[MULTIMODAL_PROCESSOR] 预处理媒体: {media_input.type}")
        
        start_time = datetime.now()
        
        try:
            if media_input.type == InputType.IMAGE:
                result = await self._preprocess_image(media_input, analysis)
            elif media_input.type == InputType.AUDIO:
                result = await self._preprocess_audio(media_input, analysis)
            elif media_input.type == InputType.VIDEO:
                result = await self._preprocess_video(media_input, analysis)
            else:
                # 默认不处理
                result = ProcessingResult(
                    success=True,
                    processed_data=safe_decode_media_data(media_input.data) if media_input.data else None,
                    metadata={"preprocessing": "none"}
                )
            
            result.processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[MULTIMODAL_PROCESSOR] 预处理完成，耗时: {result.processing_time:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 预处理失败: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def _preprocess_image(self, media_input: MediaInput, analysis: MediaAnalysis) -> ProcessingResult:
        """预处理图像"""
        if not media_input.data:
            return ProcessingResult(success=False, error="No image data")
        
        try:
            # 解码图像
            image_bytes = safe_decode_media_data(media_input.data)
            image = Image.open(io.BytesIO(image_bytes))
            
            processed_image = image
            metadata = {"original_format": analysis.format}
            
            # 根据需要进行处理
            if analysis.dimensions and (analysis.dimensions[0] > 4096 or analysis.dimensions[1] > 4096):
                # 缩放大图像
                max_size = (4096, 4096)
                processed_image.thumbnail(max_size, Image.Resampling.LANCZOS)
                metadata["resized"] = True
                metadata["new_size"] = processed_image.size
            
            # 标准化格式
            if processed_image.mode != 'RGB' and analysis.format.lower() in ['jpg', 'jpeg']:
                processed_image = processed_image.convert('RGB')
                metadata["mode_converted"] = True
            
            # 保存处理后的图像
            output_buffer = io.BytesIO()
            output_format = 'JPEG' if analysis.format.lower() in ['jpg', 'jpeg'] else 'PNG'
            processed_image.save(output_buffer, format=output_format, quality=95)
            processed_bytes = output_buffer.getvalue()
            
            return ProcessingResult(
                success=True,
                processed_data=processed_bytes,
                metadata=metadata,
                quality_score=0.9
            )
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 图像预处理失败: {e}")
            return ProcessingResult(success=False, error=str(e))
    
    async def _preprocess_audio(self, media_input: MediaInput, analysis: MediaAnalysis) -> ProcessingResult:
        """预处理音频"""
        if not AUDIO_PROCESSING_AVAILABLE:
            return ProcessingResult(
                success=True,
                processed_data=safe_decode_media_data(media_input.data) if media_input.data else None,
                metadata={"preprocessing": "skipped_no_library"}
            )
        
        if not media_input.data:
            return ProcessingResult(success=False, error="No audio data")
        
        try:
            # 基本的音频预处理
            audio_bytes = safe_decode_media_data(media_input.data)
            
            # 简化处理：直接返回原始数据
            # 在实际应用中，这里可以添加降噪、标准化等处理
            
            return ProcessingResult(
                success=True,
                processed_data=audio_bytes,
                metadata={"preprocessing": "basic"},
                quality_score=0.8
            )
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 音频预处理失败: {e}")
            return ProcessingResult(success=False, error=str(e))
    
    async def _preprocess_video(self, media_input: MediaInput, analysis: MediaAnalysis) -> ProcessingResult:
        """预处理视频"""
        if not VIDEO_PROCESSING_AVAILABLE:
            return ProcessingResult(
                success=True,
                processed_data=safe_decode_media_data(media_input.data) if media_input.data else None,
                metadata={"preprocessing": "skipped_no_library"}
            )
        
        if not media_input.data:
            return ProcessingResult(success=False, error="No video data")
        
        try:
            # 基本的视频预处理
            video_bytes = safe_decode_media_data(media_input.data)
            
            # 简化处理：直接返回原始数据
            # 在实际应用中，这里可以添加压缩、格式转换等处理
            
            return ProcessingResult(
                success=True,
                processed_data=video_bytes,
                metadata={"preprocessing": "basic"},
                quality_score=0.7
            )
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 视频预处理失败: {e}")
            return ProcessingResult(success=False, error=str(e))
    
    async def _assess_quality(self, media_input: MediaInput, analysis: MediaAnalysis) -> Dict[str, Any]:
        """评估媒体质量"""
        logger.info(f"[MULTIMODAL_PROCESSOR] 评估质量: {media_input.type}")
        
        quality_assessment = {
            "overall_score": 0.0,
            "factors": {},
            "recommendations": []
        }
        
        try:
            if media_input.type == InputType.IMAGE:
                quality_assessment = self._assess_image_quality(analysis)
            elif media_input.type == InputType.AUDIO:
                quality_assessment = self._assess_audio_quality(analysis)
            elif media_input.type == InputType.VIDEO:
                quality_assessment = self._assess_video_quality(analysis)
            
            logger.info(f"[MULTIMODAL_PROCESSOR] 质量评分: {quality_assessment['overall_score']:.2f}")
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 质量评估失败: {e}")
            quality_assessment["error"] = str(e)
        
        return quality_assessment
    
    def _assess_image_quality(self, analysis: MediaAnalysis) -> Dict[str, Any]:
        """评估图像质量"""
        factors = {}
        score = 0.0
        recommendations = []
        
        # 分辨率评估
        if analysis.dimensions:
            resolution = analysis.dimensions[0] * analysis.dimensions[1]
            if resolution >= 1920 * 1080:
                resolution_score = 1.0
            elif resolution >= 1280 * 720:
                resolution_score = 0.8
            elif resolution >= 640 * 480:
                resolution_score = 0.6
            else:
                resolution_score = 0.4
                recommendations.append("建议使用更高分辨率的图像")
            
            factors["resolution"] = resolution_score
            score += resolution_score * 0.4
        
        # 压缩比评估
        if "compression_ratio" in analysis.quality_metrics:
            compression_ratio = analysis.quality_metrics["compression_ratio"]
            if compression_ratio > 0.3:
                compression_score = 1.0
            elif compression_ratio > 0.1:
                compression_score = 0.8
            else:
                compression_score = 0.6
                recommendations.append("图像压缩程度较高，可能影响质量")
            
            factors["compression"] = compression_score
            score += compression_score * 0.3
        
        # 文件大小评估
        if analysis.file_size:
            if analysis.file_size > 10 * 1024 * 1024:  # >10MB
                recommendations.append("文件较大，建议优化大小")
            elif analysis.file_size < 50 * 1024:  # <50KB
                recommendations.append("文件较小，可能质量不足")
            
            size_score = min(1.0, analysis.file_size / (2 * 1024 * 1024))  # 2MB为满分
            factors["file_size"] = size_score
            score += size_score * 0.3
        
        return {
            "overall_score": min(score, 1.0),
            "factors": factors,
            "recommendations": recommendations
        }
    
    def _assess_audio_quality(self, analysis: MediaAnalysis) -> Dict[str, Any]:
        """评估音频质量"""
        factors = {}
        score = 0.0
        recommendations = []
        
        # 采样率评估
        if "sample_rate" in analysis.quality_metrics:
            sample_rate = analysis.quality_metrics["sample_rate"]
            if sample_rate >= 44100:
                sr_score = 1.0
            elif sample_rate >= 22050:
                sr_score = 0.8
            else:
                sr_score = 0.6
                recommendations.append("建议使用更高的采样率")
            
            factors["sample_rate"] = sr_score
            score += sr_score * 0.4
        
        # 时长评估
        if analysis.duration:
            if analysis.duration > 300:  # >5分钟
                recommendations.append("音频较长，处理时间可能较久")
            elif analysis.duration < 1:  # <1秒
                recommendations.append("音频过短，可能影响识别效果")
            
            duration_score = min(1.0, analysis.duration / 60)  # 1分钟为满分
            factors["duration"] = duration_score
            score += duration_score * 0.3
        
        # 能量评估
        if "rms_energy" in analysis.quality_metrics:
            rms_energy = analysis.quality_metrics["rms_energy"]
            if rms_energy > 0.1:
                energy_score = 1.0
            elif rms_energy > 0.05:
                energy_score = 0.8
            else:
                energy_score = 0.6
                recommendations.append("音频信号较弱，建议提高音量")
            
            factors["energy"] = energy_score
            score += energy_score * 0.3
        
        return {
            "overall_score": min(score, 1.0),
            "factors": factors,
            "recommendations": recommendations
        }
    
    def _assess_video_quality(self, analysis: MediaAnalysis) -> Dict[str, Any]:
        """评估视频质量"""
        factors = {}
        score = 0.0
        recommendations = []
        
        # 分辨率评估
        if analysis.dimensions:
            resolution = analysis.dimensions[0] * analysis.dimensions[1]
            if resolution >= 1920 * 1080:
                resolution_score = 1.0
            elif resolution >= 1280 * 720:
                resolution_score = 0.8
            else:
                resolution_score = 0.6
                recommendations.append("建议使用更高分辨率的视频")
            
            factors["resolution"] = resolution_score
            score += resolution_score * 0.4
        
        # 帧率评估
        if "fps" in analysis.quality_metrics:
            fps = analysis.quality_metrics["fps"]
            if fps >= 30:
                fps_score = 1.0
            elif fps >= 24:
                fps_score = 0.8
            else:
                fps_score = 0.6
                recommendations.append("帧率较低，可能影响流畅度")
            
            factors["fps"] = fps_score
            score += fps_score * 0.3
        
        # 时长评估
        if analysis.duration:
            if analysis.duration > 600:  # >10分钟
                recommendations.append("视频较长，处理时间可能很久")
            
            duration_score = min(1.0, analysis.duration / 300)  # 5分钟为满分
            factors["duration"] = duration_score
            score += duration_score * 0.3
        
        return {
            "overall_score": min(score, 1.0),
            "factors": factors,
            "recommendations": recommendations
        }
    
    async def _make_routing_decision(
        self, 
        media_input: MediaInput, 
        analysis: MediaAnalysis, 
        quality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """做出路由决策"""
        logger.info(f"[MULTIMODAL_PROCESSOR] 路由决策: {media_input.type}")
        
        routing = {
            "recommended_agents": [],
            "processing_priority": "normal",
            "quality_requirements": "medium",
            "estimated_processing_time": 0.0,
            "resource_requirements": {},
            "fallback_options": []
        }
        
        try:
            # 根据媒体类型和质量决定路由
            if media_input.type == InputType.IMAGE:
                routing = self._route_image(analysis, quality)
            elif media_input.type == InputType.AUDIO:
                routing = self._route_audio(analysis, quality)
            elif media_input.type == InputType.VIDEO:
                routing = self._route_video(analysis, quality)
            elif media_input.type == InputType.TEXT:
                routing = self._route_text(analysis, quality)
            
            logger.info(f"[MULTIMODAL_PROCESSOR] 推荐代理: {routing['recommended_agents']}")
            
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] 路由决策失败: {e}")
            routing["error"] = str(e)
        
        return routing
    
    def _route_image(self, analysis: MediaAnalysis, quality: Dict[str, Any]) -> Dict[str, Any]:
        """图像路由决策"""
        agents = []
        priority = "normal"
        quality_req = "medium"
        
        # 根据图像质量选择代理
        overall_score = quality.get("overall_score", 0.5)
        
        if overall_score >= 0.8:
            agents.append("vision_capture_agent")
            quality_req = "high"
        else:
            agents.append("vision_capture_agent")
        
        # 根据图像大小估算处理时间
        if analysis.dimensions:
            pixels = analysis.dimensions[0] * analysis.dimensions[1]
            estimated_time = max(1.0, pixels / 1000000)  # 每百万像素1秒
        else:
            estimated_time = 2.0
        
        return {
            "recommended_agents": agents,
            "processing_priority": priority,
            "quality_requirements": quality_req,
            "estimated_processing_time": estimated_time,
            "resource_requirements": {
                "memory_mb": max(100, analysis.file_size // (1024 * 1024) * 2),
                "cpu_intensive": True
            },
            "fallback_options": ["vision_capture_agent"] if agents[0] != "vision_capture_agent" else []
        }
    
    def _route_audio(self, analysis: MediaAnalysis, quality: Dict[str, Any]) -> Dict[str, Any]:
        """音频路由决策"""
        agents = []
        priority = "normal"
        quality_req = "medium"
        
        # 根据音频质量选择代理
        overall_score = quality.get("overall_score", 0.5)
        
        if overall_score >= 0.8:
            agents.append("voice_interaction_agent")
            quality_req = "high"
        else:
            agents.append("voice_interaction_agent")
        
        # 根据音频时长估算处理时间
        estimated_time = max(2.0, (analysis.duration or 10) * 0.3)  # 音频时长的30%
        
        return {
            "recommended_agents": agents,
            "processing_priority": priority,
            "quality_requirements": quality_req,
            "estimated_processing_time": estimated_time,
            "resource_requirements": {
                "memory_mb": max(50, int((analysis.duration or 10) * 10)),
                "network_required": True  # 可能需要调用外部API
            },
            "fallback_options": ["voice_interaction_agent"] if agents[0] != "voice_interaction_agent" else []
        }
    
    def _route_video(self, analysis: MediaAnalysis, quality: Dict[str, Any]) -> Dict[str, Any]:
        """视频路由决策"""
        agents = ["vision_capture_agent"]  # 视频处理使用视觉代理
        priority = "low"  # 视频处理通常耗时较长
        quality_req = "high"
        
        # 估算处理时间（视频处理通常较慢）
        estimated_time = max(10.0, (analysis.duration or 30) * 2)  # 视频时长的2倍
        
        return {
            "recommended_agents": agents,
            "processing_priority": priority,
            "quality_requirements": quality_req,
            "estimated_processing_time": estimated_time,
            "resource_requirements": {
                "memory_mb": max(500, int((analysis.duration or 30) * 50)),
                "cpu_intensive": True,
                "disk_space_mb": analysis.file_size // (1024 * 1024) * 3  # 3倍文件大小用于临时处理
            },
            "fallback_options": []
        }
    
    def _route_text(self, analysis: MediaAnalysis, quality: Dict[str, Any]) -> Dict[str, Any]:
        """文本路由决策"""
        return {
            "recommended_agents": ["orchestrator"],  # 文本直接由协调器处理
            "processing_priority": "high",
            "quality_requirements": "low",
            "estimated_processing_time": 0.5,
            "resource_requirements": {
                "memory_mb": 10,
                "cpu_intensive": False
            },
            "fallback_options": []
        }
    
    async def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """生成整体建议"""
        recommendations = []
        
        # 分析处理结果
        processed_count = results["processing_summary"]["processed_inputs"]
        failed_count = results["processing_summary"]["failed_inputs"]
        total_count = results["processing_summary"]["total_inputs"]
        
        if failed_count > 0:
            recommendations.append(f"有 {failed_count}/{total_count} 个输入处理失败，请检查输入格式和质量")
        
        # 分析质量评估
        quality_scores = [q.get("overall_score", 0) for q in results["quality_assessments"] if isinstance(q, dict)]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            if avg_quality < 0.6:
                recommendations.append("输入媒体质量偏低，建议提高媒体质量以获得更好的处理效果")
        
        # 分析处理时间
        processing_time = results["processing_summary"]["processing_time"]
        if processing_time > 30:
            recommendations.append("处理时间较长，建议考虑分批处理或降低媒体质量")
        
        return recommendations
    
    async def _init_whisper(self):
        """初始化 OpenAI Whisper"""
        try:
            import whisper
            
            model_size = settings.whisper_model_size  # base, small, medium, large
            logger.info(f"加载 Whisper {model_size} 模型...")
            self.whisper_model = whisper.load_model(model_size)
            logger.info("✅ Whisper 初始化成功")
            
        except ImportError:
            logger.warning("⚠️  未安装 whisper，请运行: pip install openai-whisper")
        except Exception as e:
            logger.error(f"❌ Whisper 初始化失败: {e}")
    
    async def _init_multimodal_llm(self):
        """初始化多模态大模型"""
        try:
            # 检查 Ollama 是否可用
            import subprocess
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Ollama 已安装")
                
                # 检查模型是否已下载
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
                if "qwen2.5vl" in result.stdout:
                    logger.info("✅ Qwen2.5-VL 模型已就绪")
                else:
                    logger.info("📥 首次运行需要下载模型 (6GB)，请运行: ollama pull qwen2.5vl")
                
                self.use_ollama = True
            else:
                logger.warning("⚠️  Ollama 未安装，请先安装: https://ollama.com")
                self.use_ollama = False
                
        except Exception as e:
            logger.error(f"❌ 检查 Ollama 失败: {e}")
            self.use_ollama = False
    
    async def _perform_ai_analysis(self, media_input: MediaInput, processed_data: bytes) -> Dict[str, Any]:
        """使用 AI 模型进行深度分析"""
        try:
            if media_input.type == InputType.AUDIO and self.whisper_model:
                # 使用 Whisper 进行语音识别
                logger.info("[MULTIMODAL_PROCESSOR] 使用 Whisper 进行语音识别")
                
                # 保存到临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(processed_data)
                    tmp_path = tmp.name
                
                # 识别 - 使用配置中的默认语言或从元数据获取
                language = media_input.metadata.get("language", settings.whisper_language if hasattr(settings, 'whisper_language') else "zh")
                result = self.whisper_model.transcribe(tmp_path, language=language)
                
                # 删除临时文件
                Path(tmp_path).unlink()
                
                return {
                    "type": "speech_recognition",
                    "text": result["text"],
                    "language": result.get("language", "zh"),
                    "model": "whisper"
                }
                
            elif media_input.type == InputType.IMAGE and hasattr(self, 'use_ollama') and self.use_ollama:
                # 使用 Ollama + Qwen2.5-VL 分析图像
                logger.info("[MULTIMODAL_PROCESSOR] 使用 Ollama Qwen2.5-VL 分析图像")
                
                # 优化图像大小以提高性能
                import base64
                from PIL import Image
                import io
                
                # 加载图像并调整大小
                image = Image.open(io.BytesIO(processed_data))
                logger.info(f"[MULTIMODAL_PROCESSOR] 原始图像大小: {image.size}")
                
                # 如果图像太大，调整到合理大小
                max_size = settings.ollama_max_image_size if hasattr(settings, 'ollama_max_image_size') else 768
                if image.width > max_size or image.height > max_size:
                    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    logger.info(f"[MULTIMODAL_PROCESSOR] 调整后图像大小: {image.size}")
                
                # 转换为 JPEG 格式（如果不是）并压缩
                buffer = io.BytesIO()
                if image.mode in ('RGBA', 'P'):
                    image = image.convert('RGB')
                image.save(buffer, format='JPEG', quality=85, optimize=True)
                processed_image_data = buffer.getvalue()
                
                # 转换为 base64
                base64_image = base64.b64encode(processed_image_data).decode('utf-8')
                
                logger.info(f"[MULTIMODAL_PROCESSOR] 优化后 Base64 大小: {len(base64_image)} 字符")
                
                # 调用 Ollama API
                import requests
                
                # 先检查模型是否可用
                try:
                    models_response = requests.get("http://localhost:11434/api/tags", timeout=5)
                    if models_response.status_code == 200:
                        available_models = [m['name'] for m in models_response.json().get('models', [])]
                        logger.info(f"[MULTIMODAL_PROCESSOR] 可用的 Ollama 模型: {available_models}")
                        
                        # 检查视觉模型
                        preferred_model = settings.ollama_vision_model if hasattr(settings, 'ollama_vision_model') else 'qwen2.5vl:2b'
                        vision_models = [preferred_model, 'qwen2.5vl:2b', 'qwen2.5vl', 'llava', 'bakllava']
                        model_to_use = None
                        for model in vision_models:
                            if any(model in m for m in available_models):
                                model_to_use = model
                                break
                        
                        if not model_to_use:
                            logger.error("[MULTIMODAL_PROCESSOR] 没有找到可用的视觉模型")
                            return {
                                "type": "image_analysis",
                                "description": "图像分析失败",
                                "error": "没有安装视觉模型，请运行: ollama pull qwen2.5vl",
                                "model": "ollama"
                            }
                    else:
                        logger.warning("[MULTIMODAL_PROCESSOR] 无法获取 Ollama 模型列表")
                        model_to_use = "qwen2.5vl"  # 尝试默认模型
                except Exception as e:
                    logger.error(f"[MULTIMODAL_PROCESSOR] Ollama 服务可能未启动: {e}")
                    return {
                        "type": "image_analysis",
                        "description": "图像分析失败",
                        "error": "Ollama 服务未启动，请先启动 Ollama",
                        "model": "ollama"
                    }
                
                logger.info(f"[MULTIMODAL_PROCESSOR] 使用模型: {model_to_use}")
                
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model_to_use,
                        "prompt": "请详细描述这张图片的内容",
                        "images": [base64_image],  # 使用 base64 编码的图像
                        "stream": False
                    },
                    timeout=settings.ollama_vision_timeout if hasattr(settings, 'ollama_vision_timeout') else 120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    description = result.get("response", "")
                    
                    if description:
                        return {
                            "type": "image_analysis",
                            "description": description,
                            "model": "ollama/qwen2.5vl"
                        }
                    else:
                        logger.error(f"[MULTIMODAL_PROCESSOR] Ollama返回空结果: {result}")
                        return {
                            "type": "image_analysis",
                            "description": "图像分析失败",
                            "error": "Ollama返回空结果",
                            "model": "ollama/qwen2.5vl"
                        }
                else:
                    error_msg = f"Ollama API错误: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    logger.error(f"[MULTIMODAL_PROCESSOR] {error_msg}")
                    return {
                        "type": "image_analysis",
                        "description": "图像分析失败",
                        "error": error_msg,
                        "model": "ollama/qwen2.5vl"
                    }
                
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] Ollama图像分析异常: {e}", exc_info=True)
            return {
                "type": "image_analysis",
                "description": "图像分析失败",
                "error": f"Ollama分析异常: {str(e)}",
                "model": "ollama/qwen2.5vl"
            }
            
        try:
            if media_input.type == InputType.AUDIO:
                # 语音识别
                logger.info("[MULTIMODAL_PROCESSOR] 执行 AI 语音识别")
                result = await self.hf_processor.process_audio(
                    processed_data,
                    language=media_input.metadata.get("language", "auto") if media_input.metadata else "auto"
                )
                
                if result.get("success"):
                    return {
                        "type": "speech_recognition",
                        "text": result.get("text", ""),
                        "confidence": result.get("confidence", 0),
                        "model": result.get("model", "unknown")
                    }
                    
            elif media_input.type == InputType.IMAGE:
                # 图像分析
                logger.info("[MULTIMODAL_PROCESSOR] 执行 AI 图像分析")
                result = await self.hf_processor.process_image(
                    processed_data,
                    task="describe"
                )
                
                if result.get("success"):
                    return {
                        "type": "image_analysis",
                        "description": result.get("description", ""),
                        "model": result.get("model", "unknown")
                    }
                    
            elif media_input.type == InputType.VIDEO:
                # 视频分析（提取关键帧进行分析）
                logger.info("[MULTIMODAL_PROCESSOR] 视频 AI 分析暂不支持")
                return {
                    "type": "video_analysis",
                    "message": "视频分析功能正在开发中"
                }
                
        except Exception as e:
            logger.error(f"[MULTIMODAL_PROCESSOR] AI 分析失败: {e}")
            
        return None
    
    def _update_stats(self, inputs: List[MediaInput], processing_time: float):
        """更新处理统计"""
        self.processing_stats["total_processed"] += len(inputs)
        
        # 更新各类型统计
        for input_item in inputs:
            type_key = input_item.type.value
            if type_key not in self.processing_stats["by_type"]:
                self.processing_stats["by_type"][type_key] = 0
            self.processing_stats["by_type"][type_key] += 1
        
        # 更新平均处理时间
        current_avg = self.processing_stats["average_processing_time"]
        total_processed = self.processing_stats["total_processed"]
        self.processing_stats["average_processing_time"] = (
            (current_avg * (total_processed - len(inputs)) + processing_time) / total_processed
        )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return self.processing_stats.copy()
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理多模态处理器资源")
        
        # 清理缓存
        self.cache.clear()
        
        # 清理临时文件
        if hasattr(self, 'temp_dir') and self.temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"已清理临时目录: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")


# 全局多模态处理器实例
_processor_instance = None

async def get_multimodal_processor() -> MultimodalProcessor:
    """获取多模态处理器实例"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = MultimodalProcessor()
        await _processor_instance.initialize()
    return _processor_instance