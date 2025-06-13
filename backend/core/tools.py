import re
import json
import math
from typing import Dict, Any, Union
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class CalculatorInput(BaseModel):
    """计算器工具输入模型"""
    expression: str = Field(..., description="要计算的数学表达式")


class LocalCalculatorTool(BaseTool):
    """本地计算器工具"""
    name = "local_calculator"
    description = "执行基本数学计算，支持四则运算、幂运算、三角函数等"
    args_schema = CalculatorInput
    
    def _run(self, expression: str) -> str:
        """执行数学计算"""
        try:
            # 清理表达式，只保留安全的数学操作
            safe_expression = self._sanitize_expression(expression)
            
            # 支持的数学函数
            allowed_names = {
                "abs": abs,
                "min": min,
                "max": max,
                "round": round,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e
            }
            
            # 安全执行计算
            result = eval(safe_expression, {"__builtins__": {}}, allowed_names)
            
            return f"计算结果: {result}"
            
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    def _sanitize_expression(self, expression: str) -> str:
        """清理和验证数学表达式"""
        # 移除空格
        expression = expression.replace(" ", "")
        
        # 只允许数字、运算符和函数名
        allowed_pattern = r'^[0-9+\-*/().a-z_,]+$'
        if not re.match(allowed_pattern, expression.lower()):
            raise ValueError("表达式包含不允许的字符")
        
        return expression


class TextParserInput(BaseModel):
    """文本解析工具输入模型"""
    text: str = Field(..., description="要解析的文本")
    parse_type: str = Field(default="general", description="解析类型: general, entities, sentiment, keywords")


class LocalTextParserTool(BaseTool):
    """本地文本解析工具"""
    name = "local_text_parser"
    description = "解析文本内容，提取实体、情感、关键词等信息"
    args_schema = TextParserInput
    
    def _run(self, text: str, parse_type: str = "general") -> str:
        """执行文本解析"""
        try:
            result = {}
            
            if parse_type == "general" or parse_type == "entities":
                # 基本实体提取
                entities = self._extract_entities(text)
                result["entities"] = entities
            
            if parse_type == "general" or parse_type == "sentiment":
                # 简单情感分析
                sentiment = self._analyze_sentiment(text)
                result["sentiment"] = sentiment
            
            if parse_type == "general" or parse_type == "keywords":
                # 关键词提取
                keywords = self._extract_keywords(text)
                result["keywords"] = keywords
            
            if parse_type == "general":
                # 基本统计信息
                stats = self._get_text_stats(text)
                result["statistics"] = stats
            
            return f"文本解析结果: {json.dumps(result, ensure_ascii=False, indent=2)}"
            
        except Exception as e:
            return f"解析错误: {str(e)}"
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """提取基本实体"""
        entities = {
            "emails": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text),
            "urls": re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text),
            "phones": re.findall(r'\b\d{3}-\d{3}-\d{4}\b|\b\d{10,11}\b', text),
            "numbers": re.findall(r'\b\d+\.?\d*\b', text)
        }
        return entities
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """简单情感分析"""
        positive_words = ["好", "棒", "优秀", "喜欢", "开心", "满意", "great", "good", "excellent", "love", "happy"]
        negative_words = ["差", "坏", "糟糕", "讨厌", "不满", "生气", "bad", "terrible", "hate", "angry", "sad"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "positive_score": positive_count,
            "negative_score": negative_count
        }
    
    def _extract_keywords(self, text: str) -> list:
        """提取关键词"""
        # 简单的关键词提取：去除常见停用词后的高频词汇
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should"
        }
        
        # 简单分词（按空格和标点分割）
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 过滤停用词和短词
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # 计算词频并返回前10个
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]
    
    def _get_text_stats(self, text: str) -> Dict[str, Any]:
        """获取文本统计信息"""
        return {
            "character_count": len(text),
            "word_count": len(text.split()),
            "sentence_count": len(re.findall(r'[.!?]+', text)),
            "paragraph_count": len([p for p in text.split('\n') if p.strip()])
        }