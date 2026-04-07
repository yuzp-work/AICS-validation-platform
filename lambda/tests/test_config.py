"""
Unit Tests for Configuration Management Module

Tests the Config class and from_environment method.
Validates Requirements 8.1, 8.2, 8.3, 8.4
"""

import os
import pytest
from config import (
    Config,
    DEFAULT_MODEL_ID,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_AWS_REGION,
    DEFAULT_DYNAMODB_TABLE_NAME,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    _parse_int,
    _parse_float,
)


class TestConfigFromEnvironment:
    """Tests for Config.from_environment method"""
    
    def test_loads_knowledge_base_id_from_env(self, monkeypatch):
        """Test that knowledge_base_id is loaded from KNOWLEDGE_BASE_ID env var (Req 8.1)"""
        monkeypatch.setenv("KNOWLEDGE_BASE_ID", "my-kb-123")
        config = Config.from_environment()
        assert config.knowledge_base_id == "my-kb-123"
    
    def test_loads_system_prompt_from_env(self, monkeypatch):
        """Test that system_prompt is loaded from SYSTEM_PROMPT env var (Req 8.2)"""
        monkeypatch.setenv("SYSTEM_PROMPT", "Custom prompt")
        config = Config.from_environment()
        assert config.system_prompt == "Custom prompt"
    
    def test_loads_model_id_from_env(self, monkeypatch):
        """Test that model_id is loaded from MODEL_ID env var (Req 8.3)"""
        monkeypatch.setenv("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        config = Config.from_environment()
        assert config.model_id == "anthropic.claude-3-haiku-20240307-v1:0"
    
    def test_loads_max_tokens_from_env(self, monkeypatch):
        """Test that max_tokens is loaded from MAX_TOKENS env var (Req 8.3)"""
        monkeypatch.setenv("MAX_TOKENS", "2048")
        config = Config.from_environment()
        assert config.max_tokens == 2048
    
    def test_loads_temperature_from_env(self, monkeypatch):
        """Test that temperature is loaded from TEMPERATURE env var (Req 8.3)"""
        monkeypatch.setenv("TEMPERATURE", "0.7")
        config = Config.from_environment()
        assert config.temperature == 0.7
    
    def test_loads_aws_region_from_env(self, monkeypatch):
        """Test that aws_region is loaded from AWS_REGION env var"""
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        config = Config.from_environment()
        assert config.aws_region == "eu-west-1"
    
    def test_loads_dynamodb_table_name_from_env(self, monkeypatch):
        """Test that dynamodb_table_name is loaded from DYNAMODB_TABLE_NAME env var"""
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "custom-table")
        config = Config.from_environment()
        assert config.dynamodb_table_name == "custom-table"


class TestConfigDefaultValues:
    """Tests for default values when environment variables are missing (Req 8.4)"""
    
    def test_default_model_id(self, monkeypatch):
        """Test default model_id when MODEL_ID is not set"""
        monkeypatch.delenv("MODEL_ID", raising=False)
        config = Config.from_environment()
        assert config.model_id == DEFAULT_MODEL_ID
    
    def test_default_system_prompt(self, monkeypatch):
        """Test default system_prompt when SYSTEM_PROMPT is not set"""
        monkeypatch.delenv("SYSTEM_PROMPT", raising=False)
        config = Config.from_environment()
        assert config.system_prompt == DEFAULT_SYSTEM_PROMPT
    
    def test_default_aws_region(self, monkeypatch):
        """Test default aws_region when AWS_REGION is not set"""
        monkeypatch.delenv("AWS_REGION", raising=False)
        config = Config.from_environment()
        assert config.aws_region == DEFAULT_AWS_REGION
    
    def test_default_dynamodb_table_name(self, monkeypatch):
        """Test default dynamodb_table_name when DYNAMODB_TABLE_NAME is not set"""
        monkeypatch.delenv("DYNAMODB_TABLE_NAME", raising=False)
        config = Config.from_environment()
        assert config.dynamodb_table_name == DEFAULT_DYNAMODB_TABLE_NAME
    
    def test_default_max_tokens(self, monkeypatch):
        """Test default max_tokens when MAX_TOKENS is not set"""
        monkeypatch.delenv("MAX_TOKENS", raising=False)
        config = Config.from_environment()
        assert config.max_tokens == DEFAULT_MAX_TOKENS
    
    def test_default_temperature(self, monkeypatch):
        """Test default temperature when TEMPERATURE is not set"""
        monkeypatch.delenv("TEMPERATURE", raising=False)
        config = Config.from_environment()
        assert config.temperature == DEFAULT_TEMPERATURE
    
    def test_default_knowledge_base_id_is_empty(self, monkeypatch):
        """Test that knowledge_base_id defaults to empty string when not set"""
        monkeypatch.delenv("KNOWLEDGE_BASE_ID", raising=False)
        config = Config.from_environment()
        assert config.knowledge_base_id == ""


class TestConfigValidation:
    """Tests for Config.validate method"""
    
    def test_valid_config(self):
        """Test that a valid config passes validation"""
        config = Config(
            knowledge_base_id="kb-123",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            system_prompt="Test prompt",
            aws_region="us-west-2",
            dynamodb_table_name="test-table",
            max_tokens=4096,
            temperature=0.5,
        )
        assert config.validate() is True
    
    def test_invalid_empty_knowledge_base_id(self):
        """Test that empty knowledge_base_id fails validation"""
        config = Config(
            knowledge_base_id="",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            system_prompt="Test prompt",
            aws_region="us-west-2",
            dynamodb_table_name="test-table",
            max_tokens=4096,
            temperature=0.5,
        )
        assert config.validate() is False
    
    def test_invalid_temperature_below_zero(self):
        """Test that temperature below 0 fails validation"""
        config = Config(
            knowledge_base_id="kb-123",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            system_prompt="Test prompt",
            aws_region="us-west-2",
            dynamodb_table_name="test-table",
            max_tokens=4096,
            temperature=-0.1,
        )
        assert config.validate() is False
    
    def test_invalid_temperature_above_one(self):
        """Test that temperature above 1 fails validation"""
        config = Config(
            knowledge_base_id="kb-123",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            system_prompt="Test prompt",
            aws_region="us-west-2",
            dynamodb_table_name="test-table",
            max_tokens=4096,
            temperature=1.5,
        )
        assert config.validate() is False
    
    def test_invalid_max_tokens_zero(self):
        """Test that max_tokens of 0 fails validation"""
        config = Config(
            knowledge_base_id="kb-123",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            system_prompt="Test prompt",
            aws_region="us-west-2",
            dynamodb_table_name="test-table",
            max_tokens=0,
            temperature=0.5,
        )
        assert config.validate() is False
    
    def test_invalid_max_tokens_negative(self):
        """Test that negative max_tokens fails validation"""
        config = Config(
            knowledge_base_id="kb-123",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            system_prompt="Test prompt",
            aws_region="us-west-2",
            dynamodb_table_name="test-table",
            max_tokens=-100,
            temperature=0.5,
        )
        assert config.validate() is False


class TestParseHelpers:
    """Tests for _parse_int and _parse_float helper functions"""
    
    def test_parse_int_valid(self):
        """Test parsing valid integer string"""
        assert _parse_int("123", 0) == 123
    
    def test_parse_int_none(self):
        """Test parsing None returns default"""
        assert _parse_int(None, 42) == 42
    
    def test_parse_int_invalid(self):
        """Test parsing invalid string returns default"""
        assert _parse_int("not_a_number", 42) == 42
    
    def test_parse_int_empty(self):
        """Test parsing empty string returns default"""
        assert _parse_int("", 42) == 42
    
    def test_parse_float_valid(self):
        """Test parsing valid float string"""
        assert _parse_float("0.5", 0.0) == 0.5
    
    def test_parse_float_none(self):
        """Test parsing None returns default"""
        assert _parse_float(None, 0.3) == 0.3
    
    def test_parse_float_invalid(self):
        """Test parsing invalid string returns default"""
        assert _parse_float("not_a_number", 0.3) == 0.3
    
    def test_parse_float_clamps_below_zero(self):
        """Test that values below 0 are clamped to 0"""
        assert _parse_float("-0.5", 0.3) == 0.0
    
    def test_parse_float_clamps_above_one(self):
        """Test that values above 1 are clamped to 1"""
        assert _parse_float("1.5", 0.3) == 1.0
    
    def test_parse_float_boundary_zero(self):
        """Test that 0.0 is valid"""
        assert _parse_float("0.0", 0.3) == 0.0
    
    def test_parse_float_boundary_one(self):
        """Test that 1.0 is valid"""
        assert _parse_float("1.0", 0.3) == 1.0


class TestDefaultValuesAreValid:
    """Tests to ensure default values are valid (Property 12)"""
    
    def test_default_model_id_is_valid_bedrock_model(self):
        """Test that default model_id is a valid Bedrock model ID format"""
        # Valid Bedrock model IDs follow the pattern: provider.model-name-version
        assert "." in DEFAULT_MODEL_ID
        assert "anthropic" in DEFAULT_MODEL_ID or "amazon" in DEFAULT_MODEL_ID
    
    def test_default_temperature_in_valid_range(self):
        """Test that default temperature is in valid range [0.0, 1.0]"""
        assert 0.0 <= DEFAULT_TEMPERATURE <= 1.0
    
    def test_default_max_tokens_is_positive(self):
        """Test that default max_tokens is positive"""
        assert DEFAULT_MAX_TOKENS > 0
    
    def test_default_system_prompt_is_not_empty(self):
        """Test that default system_prompt is not empty"""
        assert len(DEFAULT_SYSTEM_PROMPT) > 0
    
    def test_default_aws_region_is_valid(self):
        """Test that default AWS region is a valid region format"""
        # AWS regions follow the pattern: region-direction-number
        parts = DEFAULT_AWS_REGION.split("-")
        assert len(parts) >= 2
    
    def test_default_dynamodb_table_name_is_not_empty(self):
        """Test that default DynamoDB table name is not empty"""
        assert len(DEFAULT_DYNAMODB_TABLE_NAME) > 0
