import asyncio
import cv2
import numpy as np
from PIL import Image
import base64
import io
import tempfile
import os
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CameraAgent:
    """摄像头处理智能体"""
    
    def __init__(self):
        self.camera = None
        self.camera_index = 0
        self.is_capturing = False
        self.frame_width = 640
        self.frame_height = 480
        
    async def initialize(self, camera_index: int = 0) -> bool:
        """初始化摄像头"""
        try:
            self.camera_index = camera_index
            
            # 尝试打开摄像头
            self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                logger.error(f"无法打开摄像头 {camera_index}")
                return False
            
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # 测试拍照
            ret, frame = self.camera.read()
            if not ret:
                logger.error("摄像头无法捕获图像")
                self.camera.release()
                return False
            
            logger.info(f"摄像头 {camera_index} 初始化成功，分辨率: {self.frame_width}x{self.frame_height}")
            return True
            
        except Exception as e:
            logger.error(f"摄像头初始化失败: {e}")
            return False
    
    async def capture_image(self, save_path: Optional[str] = None, format: str = "jpg") -> Dict[str, Any]:
        """拍摄单张照片"""
        if not self.camera or not self.camera.isOpened():
            await self.initialize()
            
        try:
            # 捕获帧
            ret, frame = self.camera.read()
            
            if not ret:
                return {
                    "success": False,
                    "error": "无法从摄像头读取图像",
                    "message": "请检查摄像头连接"
                }
            
            # 转换颜色空间 (BGR -> RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为PIL图像
            pil_image = Image.fromarray(frame_rgb)
            
            # 保存图像
            if save_path:
                file_path = save_path
            else:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as temp_file:
                    file_path = temp_file.name
            
            pil_image.save(file_path, format=format.upper())
            
            # 转换为base64（用于传输）
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format=format.upper())
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            result = {
                "success": True,
                "file_path": file_path,
                "format": format,
                "size": pil_image.size,
                "base64": img_base64,
                "message": f"图像捕获成功，尺寸: {pil_image.size[0]}x{pil_image.size[1]}"
            }
            
            logger.info(f"图像捕获成功: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"图像捕获失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "图像捕获过程中发生错误"
            }
    
    async def capture_multiple(self, count: int = 3, interval: float = 1.0) -> Dict[str, Any]:
        """连续拍摄多张照片"""
        try:
            images = []
            
            for i in range(count):
                result = await self.capture_image()
                
                if result.get("success"):
                    images.append({
                        "index": i + 1,
                        "file_path": result["file_path"],
                        "size": result["size"],
                        "base64": result["base64"]
                    })
                    logger.info(f"捕获第 {i+1}/{count} 张图像")
                else:
                    logger.warning(f"第 {i+1} 张图像捕获失败: {result.get('error')}")
                
                if i < count - 1:
                    await asyncio.sleep(interval)
            
            return {
                "success": len(images) > 0,
                "total_captured": len(images),
                "requested_count": count,
                "images": images,
                "message": f"成功捕获 {len(images)}/{count} 张图像"
            }
            
        except Exception as e:
            logger.error(f"连续拍摄失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "连续拍摄过程中发生错误"
            }
    
    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """分析图像内容（基础版本）"""
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "success": False,
                    "error": "无法读取图像文件",
                    "message": "请检查文件路径是否正确"
                }
            
            # 基础图像分析
            height, width, channels = image.shape
            
            # 计算图像统计信息
            mean_color = np.mean(image, axis=(0, 1))
            std_color = np.std(image, axis=(0, 1))
            
            # 亮度分析
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # 边缘检测
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (width * height)
            
            # 颜色直方图
            hist_b = cv2.calcHist([image], [0], None, [256], [0, 256])
            hist_g = cv2.calcHist([image], [1], None, [256], [0, 256])
            hist_r = cv2.calcHist([image], [2], None, [256], [0, 256])
            
            # 主色调分析（简化）
            dominant_color = [int(mean_color[2]), int(mean_color[1]), int(mean_color[0])]  # BGR -> RGB
            
            result = {
                "success": True,
                "image_info": {
                    "width": width,
                    "height": height,
                    "channels": channels,
                    "total_pixels": width * height
                },
                "color_analysis": {
                    "dominant_color_rgb": dominant_color,
                    "mean_color_bgr": mean_color.tolist(),
                    "std_color_bgr": std_color.tolist()
                },
                "quality_metrics": {
                    "brightness": float(brightness),
                    "contrast": float(contrast),
                    "edge_density": float(edge_density),
                    "sharpness_score": float(np.var(cv2.Laplacian(gray, cv2.CV_64F)))
                },
                "message": f"图像分析完成: {width}x{height}, 亮度={brightness:.1f}, 对比度={contrast:.1f}"
            }
            
            logger.info(f"图像分析完成: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"图像分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "图像分析过程中发生错误"
            }
    
    async def detect_faces(self, image_path: str) -> Dict[str, Any]:
        """人脸检测（基础版本）"""
        try:
            # 加载人脸检测器
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "success": False,
                    "error": "无法读取图像文件",
                    "message": "请检查文件路径是否正确"
                }
            
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 检测人脸
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            face_list = []
            for (x, y, w, h) in faces:
                face_list.append({
                    "x": int(x),
                    "y": int(y), 
                    "width": int(w),
                    "height": int(h),
                    "center": [int(x + w/2), int(y + h/2)]
                })
            
            result = {
                "success": True,
                "face_count": len(faces),
                "faces": face_list,
                "message": f"检测到 {len(faces)} 个人脸"
            }
            
            logger.info(f"人脸检测完成: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"人脸检测失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "人脸检测过程中发生错误"
            }
    
    async def capture_and_analyze(self) -> Dict[str, Any]:
        """拍照并分析（一键操作）"""
        # 先拍照
        capture_result = await self.capture_image()
        
        if not capture_result.get("success"):
            return capture_result
        
        # 分析图像
        analysis_result = await self.analyze_image(capture_result["file_path"])
        
        # 人脸检测
        face_result = await self.detect_faces(capture_result["file_path"])
        
        # 合并结果
        result = {
            "success": True,
            "image_info": capture_result,
            "analysis": analysis_result.get("quality_metrics", {}),
            "color_info": analysis_result.get("color_analysis", {}),
            "faces": face_result.get("faces", []),
            "face_count": face_result.get("face_count", 0),
            "message": f"拍照并分析完成: {face_result.get('face_count', 0)} 个人脸"
        }
        
        return result
    
    async def get_status(self) -> Dict[str, Any]:
        """获取摄像头Agent状态"""
        camera_available = self.camera is not None and self.camera.isOpened()
        
        if not camera_available:
            camera_available = await self.initialize()
        
        # 检测可用摄像头数量
        available_cameras = []
        for i in range(5):  # 检测前5个摄像头
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
        
        return {
            "agent_type": "camera",
            "status": "ready" if camera_available else "error",
            "camera_available": camera_available,
            "current_camera_index": self.camera_index,
            "available_cameras": available_cameras,
            "resolution": f"{self.frame_width}x{self.frame_height}",
            "supported_actions": [
                "capture_image",
                "capture_multiple",
                "analyze_image",
                "detect_faces",
                "capture_and_analyze"
            ]
        }
    
    def __del__(self):
        """清理资源"""
        if self.camera:
            self.camera.release()