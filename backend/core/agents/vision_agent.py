"""
视频/摄像头捕获智能体
处理图像识别、OCR、人脸识别、场景分析等功能
"""
import asyncio
import base64
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import io
from PIL import Image
import cv2
import numpy as np
import pytesseract

from .base_agent import BaseAgent
from ...models.schemas import A2AMessage, A2AResponse, MediaInput, InputType
from ..multimodal_processor import get_multimodal_processor
from ..tools import safe_base64_decode, clean_base64_data

logger = logging.getLogger(__name__)


class VisionAgent(BaseAgent):
    """视频/摄像头捕获智能体"""
    
    def __init__(self):
        super().__init__(
            agent_id="vision_capture_agent",
            name="视觉捕获智能体",
            description="处理图像识别、OCR、人脸识别和场景分析"
        )
        self.face_cascade = None
        self.eye_cascade = None
        self.video_sessions = {}  # 存储视频会话
        
    async def initialize(self):
        """初始化智能体"""
        await super().initialize()
        
        # 加载OpenCV级联分类器
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
            logger.info("OpenCV classifiers loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load OpenCV classifiers: {e}")
            
    def get_capabilities(self) -> List[str]:
        """返回智能体能力列表"""
        return [
            "object_detection",      # 物体检测
            "face_recognition",      # 人脸识别
            "ocr",                   # 文字识别
            "scene_analysis",        # 场景分析
            "qr_code_scan",         # 二维码扫描
            "color_detection",       # 颜色检测
            "motion_detection",      # 运动检测
            "start_video_capture",   # 开始视频捕获
            "stop_video_capture",    # 停止视频捕获
            "capture_frame"          # 捕获单帧
        ]
        
    def get_input_schema(self) -> Dict[str, Any]:
        """返回输入参数模式"""
        return {
            "action": {
                "type": "string",
                "enum": self.get_capabilities(),
                "description": "要执行的动作"
            },
            "image_data": {
                "type": "string",
                "description": "Base64编码的图像数据"
            },
            "image_format": {
                "type": "string",
                "enum": ["jpg", "png", "bmp", "webp"],
                "default": "jpg",
                "description": "图像格式"
            },
            "session_id": {
                "type": "string",
                "description": "视频会话ID"
            },
            "options": {
                "type": "object",
                "description": "额外选项",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "OCR语言（chi_sim, eng等）"
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "description": "置信度阈值"
                    }
                }
            }
        }
        
    def get_output_schema(self) -> Dict[str, Any]:
        """返回输出结果模式"""
        return {
            "detections": {
                "type": "array",
                "description": "检测到的对象列表"
            },
            "text": {
                "type": "string",
                "description": "OCR识别的文本"
            },
            "faces": {
                "type": "array",
                "description": "检测到的人脸"
            },
            "scene": {
                "type": "object",
                "description": "场景分析结果"
            },
            "session_id": {
                "type": "string",
                "description": "视频会话ID"
            },
            "frame_count": {
                "type": "integer",
                "description": "帧数"
            },
            "metadata": {
                "type": "object",
                "description": "额外元数据"
            }
        }
        
    async def process_request(self, message: A2AMessage) -> A2AResponse:
        """处理视觉请求"""
        logger.info(f"\n[VISION_AGENT] {'='*60}")
        logger.info(f"[VISION_AGENT] 收到A2A消息")
        logger.info(f"[VISION_AGENT] Message ID: {message.message_id}")
        logger.info(f"[VISION_AGENT] Sender: {message.sender}")
        logger.info(f"[VISION_AGENT] Action: {message.action}")
        
        try:
            # action可能在message.action或payload.action中
            action = message.action or message.payload.get("action", "scene_analysis")
            task_id = message.payload.get("task_id", message.message_id)
            
            logger.info(f"[VISION_AGENT] 处理动作: {action}")
            logger.info(f"[VISION_AGENT] Task ID: {task_id}")
            
            # 记录活动
            logger.info(f"[VISION_AGENT] 记录活动: request_received")
            await self.log_activity("request_received", {
                "action": action,
                "task_id": task_id
            })
            
            logger.info(f"[VISION_AGENT] 路由到具体处理函数")
            if action == "object_detection":
                result = await self._handle_object_detection(message.payload, task_id)
            elif action == "face_recognition":
                result = await self._handle_face_recognition(message.payload, task_id)
            elif action == "ocr":
                result = await self._handle_ocr(message.payload, task_id)
            elif action == "scene_analysis":
                result = await self._handle_scene_analysis(message.payload, task_id)
            elif action == "qr_code_scan":
                result = await self._handle_qr_code(message.payload, task_id)
            elif action == "color_detection":
                result = await self._handle_color_detection(message.payload, task_id)
            elif action == "motion_detection":
                result = await self._handle_motion_detection(message.payload, task_id)
            elif action == "start_video_capture":
                result = await self._handle_start_video(message.payload, task_id)
            elif action == "stop_video_capture":
                result = await self._handle_stop_video(message.payload, task_id)
            elif action == "capture_frame":
                result = await self._handle_capture_frame(message.payload, task_id)
            else:
                logger.warning(f"[VISION_AGENT] 未知action: {action}")
                raise ValueError(f"Unknown action: {action}")
                
            response = A2AResponse(
                correlation_id=message.message_id,
                sender=self.agent_id,
                status="success",
                data=result
            )
            
            logger.info(f"[VISION_AGENT] 处理成功")
            logger.info(f"[VISION_AGENT] 返回结果类型: {type(result)}")
            if isinstance(result, dict):
                logger.info(f"[VISION_AGENT] 结果字段: {list(result.keys())}")
            logger.info(f"[VISION_AGENT] {'='*60}\n")
            
            return response
            
        except Exception as e:
            logger.error(f"[VISION_AGENT] 处理失败: {e}")
            
            # 提供有用的错误信息
            error_message = str(e)
            helpful_message = f"图像分析失败：{error_message}"
            
            response = A2AResponse(
                correlation_id=message.message_id,
                sender=self.agent_id,
                status="failed",
                error=helpful_message
            )
            
            logger.info(f"[VISION_AGENT] 返回错误响应")
            logger.info(f"[VISION_AGENT] {'='*60}\n")
            
            return response
            
    async def _handle_object_detection(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理物体检测"""
        logger.info(f"[VISION_AGENT] 开始物体检测")
        
        image_data = payload.get("image_data")
        if not image_data:
            raise ValueError("No image data provided")
            
        logger.info(f"[VISION_AGENT] 图像数据大小: {len(image_data)} bytes")
        
        # 检查数据长度是否合理
        if len(image_data) < 100:
            error_msg = f"图像数据太短 ({len(image_data)} 字符)，可能不是有效的base64图像数据"
            logger.error(f"[VISION_AGENT] {error_msg}")
            raise ValueError(error_msg)

        # 首先尝试使用多模态处理器进行 AI 物体检测
        try:
            logger.info(f"[VISION_AGENT] 使用多模态处理器进行物体检测")
            
            # 创建 MediaInput 对象
            media_input = MediaInput(
                type=InputType.IMAGE,
                data=image_data,
                format="jpg",  # 默认格式
                metadata={}
            )
            
            # 获取多模态处理器
            processor = await get_multimodal_processor()
            
            # 分析媒体
            analysis = await processor._analyze_media(media_input)
            
            # 预处理
            processed = await processor._preprocess_media(media_input, analysis)
            
            if processed.success and processed.processed_data:
                # 执行 AI 分析，专门针对物体检测
                ai_result = await processor._perform_ai_analysis(media_input, processed.processed_data)
                
                if ai_result and ai_result.get("type") == "image_analysis":
                    description = ai_result.get("description", "")
                    
                    # 检查是否真的成功
                    if description and description != "图像分析失败":
                        logger.info(f"[VISION_AGENT] AI 物体检测成功: {description[:100]}...")
                        
                        # 共享检测结果
                        await self.share_context(task_id, {
                            "ai_object_detection": description,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        return {
                            "detections": [{"description": description, "type": "ai_analysis"}],
                            "count": 1,
                            "analysis_type": "ai_generated",
                            "metadata": {
                                "model": ai_result.get("model", "unknown"),
                                "task_id": task_id
                            }
                        }
                    else:
                        # AI 返回了失败信息
                        error_detail = ai_result.get("error", "未知错误")
                        logger.error(f"[VISION_AGENT] AI 物体检测失败: {error_detail}")
                        raise Exception(f"AI 分析返回失败: {error_detail}")
                else:
                    logger.error(f"[VISION_AGENT] AI 返回结果格式错误: {ai_result}")
                    raise Exception("AI 物体检测返回格式错误")
            else:
                raise Exception(f"预处理失败: {processed.error}")
                
        except Exception as e:
            logger.warning(f"[VISION_AGENT] 多模态处理器失败: {e}，使用备用物体检测")
            
            # 使用原有的简单物体检测作为后备
            image = self._decode_image(image_data)
        detections = await self._detect_objects(image)
        
        # 共享检测结果
        await self.share_context(task_id, {
            "object_detections": detections,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "detections": detections,
            "count": len(detections),
                "analysis_type": "basic_detection",
            "metadata": {
                "image_size": image.shape[:2],
                "task_id": task_id
            }
        }
        
    async def _handle_face_recognition(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理人脸识别"""
        image_data = payload.get("image_data")
        if not image_data:
            raise ValueError("No image data provided")
            
        # 解码图像
        image = self._decode_image(image_data)
        
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        face_results = []
        for (x, y, w, h) in faces:
            # 检测眼睛（验证是否真的是人脸）
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            
            face_results.append({
                "bbox": [int(x), int(y), int(w), int(h)],
                "confidence": 0.85 if len(eyes) >= 2 else 0.65,
                "has_eyes": bool(len(eyes) >= 2)
            })
            
        # 共享人脸检测结果
        await self.share_context(task_id, {
            "face_detections": face_results,
            "face_count": len(face_results),
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "faces": face_results,
            "count": len(face_results),
            "metadata": {
                "detector": "haarcascade",
                "task_id": task_id
            }
        }
        
    async def _handle_ocr(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理OCR文字识别"""
        image_data = payload.get("image_data")
        options = payload.get("options", {})
        language = options.get("language", "eng")  # 默认英文
        
        if not image_data:
            raise ValueError("No image data provided")
            
        # 解码图像
        image = self._decode_image(image_data)
        
        # 图像预处理以提高OCR准确率
        processed = self._preprocess_for_ocr(image)
        
        # 执行OCR
        try:
            text = pytesseract.image_to_string(
                processed,
                lang=language,
                config='--psm 3'  # 自动页面分割
            )
            
            # 获取详细信息
            data = pytesseract.image_to_data(
                processed,
                lang=language,
                output_type=pytesseract.Output.DICT
            )
            
            # 计算平均置信度
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
        except Exception as e:
            logger.error(f"OCR error: {e}")
            text = ""
            avg_confidence = 0
            
        # 共享OCR结果
        await self.share_context(task_id, {
            "ocr_text": text,
            "ocr_confidence": avg_confidence / 100,
            "language": language,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "text": text.strip(),
            "confidence": avg_confidence / 100,
            "language": language,
            "word_count": len(text.split()),
            "metadata": {
                "engine": "tesseract",
                "task_id": task_id
            }
        }
        
    async def _handle_scene_analysis(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理场景分析"""
        logger.info(f"[VISION_AGENT] 开始场景分析")
        
        image_data = payload.get("image_data")
        if not image_data:
            raise ValueError("No image data provided")
            
        logger.info(f"[VISION_AGENT] 图像数据大小: {len(image_data)} bytes")
        
        # 检查数据长度是否合理（真实的图像base64数据通常至少几百字符）
        if len(image_data) < 100:
            error_msg = f"图像数据太短 ({len(image_data)} 字符)，可能不是有效的base64图像数据"
            logger.error(f"[VISION_AGENT] {error_msg}")
            raise ValueError(error_msg)
        
        # 解码图像数据（使用清理后的数据）
        try:
            image_bytes, success = safe_base64_decode(image_data)
            if not success:
                raise ValueError("Base64 解码失败")
        except Exception as e:
            logger.error(f"[VISION_AGENT] Base64解码失败: {e}")
            # 如果直接解码失败，使用 _decode_image 方法作为后备
            image = self._decode_image(image_data)
            scene_info = await self._analyze_scene(image)
            scene_info["analysis_type"] = "basic_analysis"
            
            # 共享场景分析结果
            await self.share_context(task_id, {
                "scene_analysis": scene_info,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "scene": scene_info,
                "metadata": {
                    "task_id": task_id
                }
            }
        
        # 使用多模态处理器
        try:
            logger.info(f"[VISION_AGENT] 使用多模态处理器进行图像分析")
            
            # 创建 MediaInput 对象
            media_input = MediaInput(
                type=InputType.IMAGE,
                data=image_data,
                format="jpg",  # 默认格式
                metadata={}
            )
            
            # 获取多模态处理器
            processor = await get_multimodal_processor()
            
            # 分析媒体
            analysis = await processor._analyze_media(media_input)
            
            # 预处理
            processed = await processor._preprocess_media(media_input, analysis)
            
            if processed.success and processed.processed_data:
                # 执行 AI 分析
                ai_result = await processor._perform_ai_analysis(media_input, processed.processed_data)
                
                if ai_result and ai_result.get("type") == "image_analysis":
                    description = ai_result.get("description", "")
                    
                    # 检查是否真的成功
                    if description and description != "图像分析失败":
                        logger.info(f"[VISION_AGENT] AI 图像分析成功: {description[:100]}...")
                        scene_info = {
                            "description": description,
                            "model": ai_result.get("model", "unknown"),
                            "analysis_type": "ai_generated"
                        }
                    else:
                        # AI 返回了失败信息
                        error_detail = ai_result.get("error", "未知错误")
                        logger.error(f"[VISION_AGENT] AI 图像分析失败: {error_detail}")
                        raise Exception(f"AI 分析返回失败: {error_detail}")
                else:
                    logger.error(f"[VISION_AGENT] AI 返回结果格式错误: {ai_result}")
                    raise Exception("AI 图像分析返回格式错误")
            else:
                raise Exception(f"预处理失败: {processed.error}")
                
        except Exception as e:
            logger.warning(f"[VISION_AGENT] 多模态处理器失败: {e}，使用备用方案")
            
            # 使用原有的简单分析
            image = self._decode_image(image_data)
            scene_info = await self._analyze_scene(image)
            scene_info["analysis_type"] = "basic_analysis"
        
        logger.info(f"[VISION_AGENT] 场景分析完成")
        
        # 共享场景分析结果
        logger.info(f"[VISION_AGENT] 共享分析结果到上下文")
        await self.share_context(task_id, {
            "scene_analysis": scene_info,
            "timestamp": datetime.now().isoformat()
        })
        
        result = {
            "scene": scene_info,
            "metadata": {
                "task_id": task_id
            }
        }
        
        return result
        
    async def _handle_qr_code(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理二维码扫描"""
        image_data = payload.get("image_data")
        if not image_data:
            raise ValueError("No image data provided")
            
        # 解码图像
        image = self._decode_image(image_data)
        
        # 检测二维码
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(image)
        
        result = {
            "found": bool(data),
            "data": data if data else None,
            "type": "qr_code"
        }
        
        # 共享二维码结果
        if data:
            await self.share_context(task_id, {
                "qr_code_data": data,
                "timestamp": datetime.now().isoformat()
            })
            
        return result
        
    async def _handle_color_detection(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理颜色检测"""
        image_data = payload.get("image_data")
        if not image_data:
            raise ValueError("No image data provided")
            
        # 解码图像
        image = self._decode_image(image_data)
        
        # 分析主要颜色
        dominant_colors = self._detect_dominant_colors(image)
        
        return {
            "colors": dominant_colors,
            "metadata": {
                "task_id": task_id
            }
        }
        
    async def _handle_motion_detection(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """处理运动检测"""
        # 这需要比较多帧，简化处理
        return {
            "motion_detected": False,
            "message": "Motion detection requires video stream",
            "metadata": {
                "task_id": task_id
            }
        }
        
    async def _handle_start_video(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """开始视频捕获"""
        session_id = payload.get("session_id") or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建视频会话
        self.video_sessions[session_id] = {
            "session_id": session_id,
            "start_time": datetime.now(),
            "frame_count": 0,
            "task_id": task_id
        }
        
        logger.info(f"Started video capture: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "capturing",
            "start_time": datetime.now().isoformat()
        }
        
    async def _handle_stop_video(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """停止视频捕获"""
        session_id = payload.get("session_id")
        
        if not session_id or session_id not in self.video_sessions:
            raise ValueError(f"Video session not found: {session_id}")
            
        session = self.video_sessions[session_id]
        duration = (datetime.now() - session["start_time"]).total_seconds()
        
        # 清理会话
        del self.video_sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": "stopped",
            "duration": duration,
            "frame_count": session["frame_count"]
        }
        
    async def _handle_capture_frame(self, payload: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """捕获单帧"""
        session_id = payload.get("session_id")
        
        if session_id and session_id in self.video_sessions:
            self.video_sessions[session_id]["frame_count"] += 1
            frame_number = self.video_sessions[session_id]["frame_count"]
        else:
            frame_number = 1
            
        return {
            "captured": True,
            "frame_number": frame_number,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "task_id": task_id
            }
        }
        
    def _decode_image(self, image_data: str) -> np.ndarray:
        """解码Base64图像数据"""
        logger.info(f"[VISION_AGENT] 解码图像数据")
        
        # 检查数据长度是否合理（真实的图像base64数据通常至少几百字符）
        if len(image_data) < 100:
            error_msg = f"图像数据太短 ({len(image_data)} 字符)，可能不是有效的base64图像数据"
            logger.error(f"[VISION_AGENT] {error_msg}")
            raise ValueError(error_msg)
        
        try:
            # 使用工具函数安全解码
            image_bytes, success = safe_base64_decode(image_data)
            
            if not success:
                raise ValueError("Base64 解码失败")
            
            logger.info(f"[VISION_AGENT] Base64 解码成功，数据长度: {len(image_bytes)} bytes")
            
            # 检查数据是否为空
            if len(image_bytes) == 0:
                raise ValueError("解码后的图像数据为空")
        
            # 转换为numpy数组
            nparr = np.frombuffer(image_bytes, np.uint8)
            logger.info(f"[VISION_AGENT] 创建numpy数组，长度: {len(nparr)}")
            
            # 检查numpy数组是否为空
            if len(nparr) == 0:
                raise ValueError("numpy数组为空")
        
            # 解码图像
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
            if image is None:
                    # 尝试其他解码方式
                    logger.warning("[VISION_AGENT] OpenCV解码失败，尝试使用PIL")
                    try:
                        from PIL import Image as PILImage
                        import io
                        
                        pil_image = PILImage.open(io.BytesIO(image_bytes))
                        # 转换为OpenCV格式
                        image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                        logger.info("[VISION_AGENT] PIL解码成功")
                    except Exception as pil_error:
                        logger.error(f"[VISION_AGENT] PIL解码也失败: {pil_error}")
                        raise ValueError("图像解码失败：OpenCV和PIL都无法解码")
                
                    if image is None:
                        raise ValueError("图像解码失败：结果为None")
                
            logger.info(f"[VISION_AGENT] 图像解码成功: {image.shape}")
            return image
            
        except Exception as e:
            logger.error(f"[VISION_AGENT] 图像解码失败: {e}")
            logger.error(f"[VISION_AGENT] 原始数据长度: {len(image_data)}")
            logger.error(f"[VISION_AGENT] 数据前100字符: {image_data[:100]}")
            
            # 尝试分析数据内容
            try:
                cleaned_data = clean_base64_data(image_data)
                logger.error(f"[VISION_AGENT] 清理后数据长度: {len(cleaned_data)}")
                logger.error(f"[VISION_AGENT] 清理后前100字符: {cleaned_data[:100]}")
            except Exception as clean_error:
                logger.error(f"[VISION_AGENT] 数据清理失败: {clean_error}")
            
            raise ValueError(f"图像解码失败: {str(e)}")
        
    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """预处理图像以提高OCR准确率"""
        # 转换为灰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 去噪
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 二值化
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
        
    async def _detect_objects(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """简化的物体检测"""
        # 这里应该使用真实的物体检测模型（如YOLO）
        # 为演示目的，使用简单的轮廓检测
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for i, contour in enumerate(contours[:10]):  # 最多10个物体
            x, y, w, h = cv2.boundingRect(contour)
            if w > 20 and h > 20:  # 过滤小物体
                objects.append({
                    "class": "unknown_object",
                    "confidence": 0.5,
                    "bbox": [int(x), int(y), int(w), int(h)]
                })
                
        return objects
        
    async def _analyze_scene(self, image: np.ndarray) -> Dict[str, Any]:
        """分析场景特征 - 备用基础分析"""
        height, width = image.shape[:2]
        
        # 计算基本统计信息
        brightness = np.mean(image)
        contrast = np.std(image)
        
        # 检测主要颜色
        try:
            dominant_colors = self._detect_dominant_colors(image)
        except Exception as e:
            logger.warning(f"[VISION_AGENT] 主要颜色检测失败: {e}")
            dominant_colors = []
        
        # 边缘密度（复杂度指标）
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (width * height)
        
        # 生成简单描述
        description = f"这是一张{width}x{height}的图片"
        
        if dominant_colors:
            color_name = self._get_color_name(dominant_colors[0]['rgb'])
            description += f"，主要颜色为{color_name}"
        
        if brightness < 85:
            description += "，画面较暗"
        elif brightness > 170:
            description += "，画面较亮"
        
        if edge_density > 0.2:
            description += "，内容较为复杂"
        elif edge_density < 0.05:
            description += "，内容较为简单"
        
        return {
            "description": description,
            "brightness": float(brightness / 255),
            "contrast": float(contrast / 255),
            "complexity": float(edge_density),
            "dominant_colors": dominant_colors[:3],
            "dimensions": {
                "width": int(width),
                "height": int(height)
            }
        }
    
    def _get_color_name(self, rgb: List[int]) -> str:
        """获取颜色名称"""
        r, g, b = rgb
        
        if r > 200 and g < 100 and b < 100:
            return "红色"
        elif r < 100 and g > 200 and b < 100:
            return "绿色"
        elif r < 100 and g < 100 and b > 200:
            return "蓝色"
        elif r > 200 and g > 200 and b < 100:
            return "黄色"
        elif r < 100 and g > 150 and b > 150:
            return "青色"
        elif r > 150 and g < 100 and b > 150:
            return "紫色"
        elif r > 200 and g > 200 and b > 200:
            return "白色"
        elif r < 50 and g < 50 and b < 50:
            return "黑色"
        elif r > 100 and g > 100 and b > 100:
            return "灰色"
        else:
            return "混合色"
        
    def _detect_dominant_colors(self, image: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """检测主要颜色"""
        try:
            # 重塑图像为像素列表
            pixels = image.reshape(-1, 3)
            
            # 使用K-means聚类找到主要颜色
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # 获取每个聚类的大小
            labels = kmeans.labels_
            label_counts = np.bincount(labels)
            
            # 排序并返回主要颜色
            colors = []
            for i in np.argsort(label_counts)[::-1]:
                color = kmeans.cluster_centers_[i]
                percentage = label_counts[i] / len(pixels)
                
                colors.append({
                    "rgb": [int(c) for c in color],
                    "hex": '#{:02x}{:02x}{:02x}'.format(
                        int(color[2]), int(color[1]), int(color[0])
                    ),
                    "percentage": float(percentage)
                })
                
            return colors
            
        except ImportError:
            logger.warning("[VISION_AGENT] sklearn未安装，使用简化颜色检测")
            # 简化版本：只返回平均颜色
            mean_color = np.mean(image.reshape(-1, 3), axis=0)
            return [{
                "rgb": [int(c) for c in mean_color],
                "hex": '#{:02x}{:02x}{:02x}'.format(
                    int(mean_color[2]), int(mean_color[1]), int(mean_color[0])
                ),
                "percentage": 1.0
            }]
        except Exception as e:
            logger.error(f"[VISION_AGENT] 颜色检测错误: {e}")
            # 返回默认颜色
            return [{
                "rgb": [128, 128, 128],
                "hex": "#808080",
                "percentage": 1.0
            }]