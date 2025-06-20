"""
数据验证工具模块
提供通用的数据验证功能
"""
import re
import base64
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import mimetypes
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """验证失败时抛出的异常"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class DataValidator:
    """数据验证器类"""
    
    @staticmethod
    def validate_required(
        data: Dict[str, Any],
        required_fields: List[str]
    ) -> None:
        """
        验证必需字段
        
        Args:
            data: 要验证的数据字典
            required_fields: 必需字段列表
            
        Raises:
            ValidationError: 缺少必需字段时
        """
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
                
        if missing_fields:
            raise ValidationError(
                "required_fields",
                f"Missing required fields: {', '.join(missing_fields)}"
            )
    
    @staticmethod
    def validate_type(
        value: Any,
        field_name: str,
        expected_type: Union[type, Tuple[type, ...]]
    ) -> None:
        """
        验证字段类型
        
        Args:
            value: 要验证的值
            field_name: 字段名称
            expected_type: 期望的类型
            
        Raises:
            ValidationError: 类型不匹配时
        """
        if not isinstance(value, expected_type):
            actual_type = type(value).__name__
            expected = (
                expected_type.__name__
                if isinstance(expected_type, type)
                else " or ".join(t.__name__ for t in expected_type)
            )
            raise ValidationError(
                field_name,
                f"Expected {expected}, got {actual_type}"
            )
    
    @staticmethod
    def validate_string_length(
        value: str,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> None:
        """
        验证字符串长度
        
        Args:
            value: 要验证的字符串
            field_name: 字段名称
            min_length: 最小长度
            max_length: 最大长度
            
        Raises:
            ValidationError: 长度不符合要求时
        """
        if min_length is not None and len(value) < min_length:
            raise ValidationError(
                field_name,
                f"String length {len(value)} is less than minimum {min_length}"
            )
            
        if max_length is not None and len(value) > max_length:
            raise ValidationError(
                field_name,
                f"String length {len(value)} exceeds maximum {max_length}"
            )
    
    @staticmethod
    def validate_email(email: str, field_name: str = "email") -> None:
        """
        验证邮箱格式
        
        Args:
            email: 要验证的邮箱
            field_name: 字段名称
            
        Raises:
            ValidationError: 邮箱格式无效时
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError(field_name, "Invalid email format")
    
    @staticmethod
    def validate_url(url: str, field_name: str = "url") -> None:
        """
        验证URL格式
        
        Args:
            url: 要验证的URL
            field_name: 字段名称
            
        Raises:
            ValidationError: URL格式无效时
        """
        pattern = r'^https?://'
        if not re.match(pattern, url, re.IGNORECASE):
            raise ValidationError(field_name, "Invalid URL format")
    
    @staticmethod
    def validate_base64(
        data: str,
        field_name: str,
        expected_mime_types: Optional[List[str]] = None
    ) -> Tuple[bytes, str]:
        """
        验证Base64编码的数据
        
        Args:
            data: Base64编码的字符串
            field_name: 字段名称
            expected_mime_types: 期望的MIME类型列表
            
        Returns:
            Tuple[bytes, str]: 解码后的数据和MIME类型
            
        Raises:
            ValidationError: Base64格式无效或MIME类型不匹配时
        """
        try:
            # 处理Data URL格式
            if data.startswith('data:'):
                header, encoded = data.split(',', 1)
                mime_type = header.split(':')[1].split(';')[0]
                decoded = base64.b64decode(encoded)
            else:
                # 纯Base64数据
                decoded = base64.b64decode(data)
                # 尝试猜测MIME类型
                mime_type = "application/octet-stream"
                
        except Exception as e:
            raise ValidationError(field_name, f"Invalid base64 format: {str(e)}")
        
        # 验证MIME类型
        if expected_mime_types and mime_type not in expected_mime_types:
            raise ValidationError(
                field_name,
                f"Unexpected MIME type {mime_type}, expected one of {expected_mime_types}"
            )
            
        return decoded, mime_type
    
    @staticmethod
    def validate_enum(
        value: Any,
        field_name: str,
        allowed_values: List[Any]
    ) -> None:
        """
        验证枚举值
        
        Args:
            value: 要验证的值
            field_name: 字段名称
            allowed_values: 允许的值列表
            
        Raises:
            ValidationError: 值不在允许列表中时
        """
        if value not in allowed_values:
            raise ValidationError(
                field_name,
                f"Value '{value}' not in allowed values: {allowed_values}"
            )
    
    @staticmethod
    def validate_number_range(
        value: Union[int, float],
        field_name: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> None:
        """
        验证数字范围
        
        Args:
            value: 要验证的数字
            field_name: 字段名称
            min_value: 最小值
            max_value: 最大值
            
        Raises:
            ValidationError: 数字超出范围时
        """
        if min_value is not None and value < min_value:
            raise ValidationError(
                field_name,
                f"Value {value} is less than minimum {min_value}"
            )
            
        if max_value is not None and value > max_value:
            raise ValidationError(
                field_name,
                f"Value {value} exceeds maximum {max_value}"
            )
    
    @staticmethod
    def validate_datetime(
        value: str,
        field_name: str,
        format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> datetime:
        """
        验证日期时间格式
        
        Args:
            value: 要验证的日期时间字符串
            field_name: 字段名称
            format_str: 日期时间格式
            
        Returns:
            datetime: 解析后的日期时间对象
            
        Raises:
            ValidationError: 日期时间格式无效时
        """
        try:
            return datetime.strptime(value, format_str)
        except ValueError as e:
            raise ValidationError(
                field_name,
                f"Invalid datetime format. Expected {format_str}: {str(e)}"
            )
    
    @staticmethod
    def validate_list_length(
        value: List[Any],
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> None:
        """
        验证列表长度
        
        Args:
            value: 要验证的列表
            field_name: 字段名称
            min_length: 最小长度
            max_length: 最大长度
            
        Raises:
            ValidationError: 长度不符合要求时
        """
        if min_length is not None and len(value) < min_length:
            raise ValidationError(
                field_name,
                f"List length {len(value)} is less than minimum {min_length}"
            )
            
        if max_length is not None and len(value) > max_length:
            raise ValidationError(
                field_name,
                f"List length {len(value)} exceeds maximum {max_length}"
            )


def validate_audio_data(audio_data: str, audio_format: str) -> bytes:
    """
    验证音频数据
    
    Args:
        audio_data: Base64编码的音频数据
        audio_format: 音频格式
        
    Returns:
        bytes: 解码后的音频数据
        
    Raises:
        ValidationError: 验证失败时
    """
    validator = DataValidator()
    
    # 验证格式
    validator.validate_enum(
        audio_format,
        "audio_format",
        ["wav", "mp3", "m4a", "flac", "ogg", "webm"]
    )
    
    # 验证Base64数据
    mime_types = [
        f"audio/{audio_format}",
        "audio/wave",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp4",
        "audio/flac",
        "audio/ogg",
        "audio/webm"
    ]
    
    decoded_data, _ = validator.validate_base64(
        audio_data,
        "audio_data",
        mime_types
    )
    
    return decoded_data


def validate_image_data(image_data: str, image_format: str) -> bytes:
    """
    验证图像数据
    
    Args:
        image_data: Base64编码的图像数据
        image_format: 图像格式
        
    Returns:
        bytes: 解码后的图像数据
        
    Raises:
        ValidationError: 验证失败时
    """
    validator = DataValidator()
    
    # 验证格式
    validator.validate_enum(
        image_format,
        "image_format",
        ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"]
    )
    
    # 验证Base64数据
    mime_types = [
        f"image/{image_format}",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/webp",
        "image/tiff"
    ]
    
    decoded_data, _ = validator.validate_base64(
        image_data,
        "image_data",
        mime_types
    )
    
    return decoded_data