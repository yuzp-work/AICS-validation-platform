"""
Configuration Management Module

Handles loading configuration from environment variables
with support for default values.

Requirements:
- 8.1: THE Lambda_Handler SHALL 从环境变量或配置文件读取 Knowledge_Base ID
- 8.2: THE Lambda_Handler SHALL 从环境变量或配置文件读取系统提示词
- 8.3: THE Lambda_Handler SHALL 从环境变量或配置文件读取模型ID和参数
- 8.4: WHEN 配置参数缺失 THEN Lambda_Handler SHALL 使用预定义的默认值
"""

import os
from dataclasses import dataclass
from typing import Optional


# Default values for configuration parameters
# These are used when environment variables are not set
DEFAULT_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_SYSTEM_PROMPT = """你是一个专业的客服助手。请根据提供的知识库内容回答用户的问题。
如果知识库中没有相关信息，请诚实地告知用户你无法回答该问题。
回答时请保持专业、友好的语气。"""
DEFAULT_AWS_REGION = "us-west-2"
DEFAULT_DYNAMODB_TABLE_NAME = "qa-validation-sessions"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.3


@dataclass
class Config:
    """
    系统配置
    
    Attributes:
        knowledge_base_id: Bedrock Knowledge Base ID (required)
        model_id: Bedrock 模型 ID
        system_prompt: 系统提示词
        aws_region: AWS 区域
        dynamodb_table_name: DynamoDB 表名
        max_tokens: 最大输出 token 数
        temperature: 温度参数 (0.0-1.0)
    """
    knowledge_base_id: str
    model_id: str
    system_prompt: str
    aws_region: str
    dynamodb_table_name: str
    max_tokens: int
    temperature: float
    
    @classmethod
    def from_environment(cls) -> "Config":
        """
        从环境变量加载配置
        
        Environment Variables:
            KNOWLEDGE_BASE_ID: Bedrock Knowledge Base ID (required, but defaults to empty string if not set)
            MODEL_ID: Bedrock 模型 ID (default: anthropic.claude-3-sonnet-20240229-v1:0)
            SYSTEM_PROMPT: 系统提示词 (default: 预定义的客服助手提示词)
            AWS_REGION: AWS 区域 (default: us-west-2)
            DYNAMODB_TABLE_NAME: DynamoDB 表名 (default: qa-validation-sessions)
            MAX_TOKENS: 最大输出 token 数 (default: 4096)
            TEMPERATURE: 温度参数 (default: 0.3)
        
        Returns:
            Config: 配置对象
            
        Note:
            当配置参数缺失时，使用预定义的默认值 (需求 8.4)
        """
        return cls(
            knowledge_base_id=os.environ.get("KNOWLEDGE_BASE_ID", ""),
            model_id=os.environ.get("MODEL_ID", DEFAULT_MODEL_ID),
            system_prompt=os.environ.get("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            aws_region=os.environ.get("AWS_REGION", DEFAULT_AWS_REGION),
            dynamodb_table_name=os.environ.get("DYNAMODB_TABLE_NAME", DEFAULT_DYNAMODB_TABLE_NAME),
            max_tokens=_parse_int(os.environ.get("MAX_TOKENS"), DEFAULT_MAX_TOKENS),
            temperature=_parse_float(os.environ.get("TEMPERATURE"), DEFAULT_TEMPERATURE),
        )
    
    def validate(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        # knowledge_base_id is required for actual operation
        if not self.knowledge_base_id:
            return False
        
        # Validate temperature is in valid range
        if not (0.0 <= self.temperature <= 1.0):
            return False
        
        # Validate max_tokens is positive
        if self.max_tokens <= 0:
            return False
        
        return True


def _parse_int(value: Optional[str], default: int) -> int:
    """
    安全解析整数值
    
    Args:
        value: 字符串值
        default: 默认值
        
    Returns:
        int: 解析后的整数或默认值
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_float(value: Optional[str], default: float) -> float:
    """
    安全解析浮点数值
    
    Args:
        value: 字符串值
        default: 默认值
        
    Returns:
        float: 解析后的浮点数或默认值
    """
    if value is None:
        return default
    try:
        import math
        parsed = float(value)
        # Handle NaN and infinity - use default value
        if math.isnan(parsed) or math.isinf(parsed):
            return default
        # Clamp temperature to valid range [0.0, 1.0]
        if parsed < 0.0:
            return 0.0
        if parsed > 1.0:
            return 1.0
        return parsed
    except (ValueError, TypeError):
        return default
