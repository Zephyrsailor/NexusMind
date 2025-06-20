"""
数据验证模块的单元测试
"""
import pytest
from backend.utils.validation import (
    DataValidator,
    ValidationError,
    validate_audio_data,
    validate_image_data
)


class TestDataValidator:
    """DataValidator类的测试"""
    
    def test_validate_required_success(self):
        """测试必需字段验证 - 成功"""
        data = {"field1": "value1", "field2": "value2"}
        DataValidator.validate_required(data, ["field1", "field2"])
        # 不应抛出异常
        
    def test_validate_required_missing_field(self):
        """测试必需字段验证 - 缺少字段"""
        data = {"field1": "value1"}
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_required(data, ["field1", "field2"])
        assert "field2" in str(exc_info.value)
        
    def test_validate_type_success(self):
        """测试类型验证 - 成功"""
        DataValidator.validate_type("test", "field", str)
        DataValidator.validate_type(123, "field", int)
        DataValidator.validate_type(123, "field", (int, float))
        
    def test_validate_type_failure(self):
        """测试类型验证 - 失败"""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_type("test", "field", int)
        assert "Expected int" in str(exc_info.value)
        
    def test_validate_string_length(self):
        """测试字符串长度验证"""
        # 成功情况
        DataValidator.validate_string_length("test", "field", min_length=2, max_length=10)
        
        # 太短
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_string_length("t", "field", min_length=2)
        assert "less than minimum" in str(exc_info.value)
        
        # 太长
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_string_length("test" * 10, "field", max_length=5)
        assert "exceeds maximum" in str(exc_info.value)
        
    def test_validate_email(self):
        """测试邮箱验证"""
        # 有效邮箱
        DataValidator.validate_email("test@example.com")
        DataValidator.validate_email("user.name+tag@example.co.uk")
        
        # 无效邮箱
        invalid_emails = [
            "invalid",
            "@example.com",
            "test@",
            "test@.com",
            "test@example"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                DataValidator.validate_email(email)
                
    def test_validate_url(self):
        """测试URL验证"""
        # 有效URL
        DataValidator.validate_url("http://example.com")
        DataValidator.validate_url("https://example.com/path")
        DataValidator.validate_url("HTTP://EXAMPLE.COM")
        
        # 无效URL
        invalid_urls = [
            "example.com",
            "ftp://example.com",
            "not a url"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                DataValidator.validate_url(url)
                
    def test_validate_base64(self):
        """测试Base64验证"""
        import base64
        
        # 有效Base64
        valid_data = base64.b64encode(b"test data").decode()
        decoded, mime_type = DataValidator.validate_base64(valid_data, "field")
        assert decoded == b"test data"
        
        # Data URL格式
        data_url = "data:text/plain;base64," + valid_data
        decoded, mime_type = DataValidator.validate_base64(data_url, "field")
        assert decoded == b"test data"
        assert mime_type == "text/plain"
        
        # 无效Base64
        with pytest.raises(ValidationError):
            DataValidator.validate_base64("not base64!", "field")
            
    def test_validate_enum(self):
        """测试枚举值验证"""
        # 成功
        DataValidator.validate_enum("option1", "field", ["option1", "option2", "option3"])
        
        # 失败
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_enum("option4", "field", ["option1", "option2", "option3"])
        assert "not in allowed values" in str(exc_info.value)
        
    def test_validate_number_range(self):
        """测试数字范围验证"""
        # 成功
        DataValidator.validate_number_range(5, "field", min_value=0, max_value=10)
        DataValidator.validate_number_range(0, "field", min_value=0)
        DataValidator.validate_number_range(10, "field", max_value=10)
        
        # 太小
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_number_range(-1, "field", min_value=0)
        assert "less than minimum" in str(exc_info.value)
        
        # 太大
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_number_range(11, "field", max_value=10)
        assert "exceeds maximum" in str(exc_info.value)
        
    def test_validate_list_length(self):
        """测试列表长度验证"""
        # 成功
        DataValidator.validate_list_length([1, 2, 3], "field", min_length=2, max_length=5)
        
        # 太短
        with pytest.raises(ValidationError):
            DataValidator.validate_list_length([1], "field", min_length=2)
            
        # 太长
        with pytest.raises(ValidationError):
            DataValidator.validate_list_length([1, 2, 3, 4, 5, 6], "field", max_length=5)


class TestSpecializedValidators:
    """特殊验证函数的测试"""
    
    def test_validate_audio_data(self):
        """测试音频数据验证"""
        import base64
        
        # 有效音频数据
        audio_bytes = b"fake audio data"
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        result = validate_audio_data(audio_base64, "wav")
        assert result == audio_bytes
        
        # 无效格式
        with pytest.raises(ValidationError):
            validate_audio_data(audio_base64, "invalid_format")
            
    def test_validate_image_data(self):
        """测试图像数据验证"""
        import base64
        
        # 有效图像数据
        image_bytes = b"fake image data"
        image_base64 = base64.b64encode(image_bytes).decode()
        
        result = validate_image_data(image_base64, "jpg")
        assert result == image_bytes
        
        # 无效格式
        with pytest.raises(ValidationError):
            validate_image_data(image_base64, "invalid_format")