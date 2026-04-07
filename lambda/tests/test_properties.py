"""
Property-Based Tests for Bedrock QA Validation System

This module contains property-based tests using the hypothesis library
to verify correctness properties defined in the design document.

Testing Framework: Python hypothesis
"""

import os
import pytest
from hypothesis import given, strategies as st, settings, assume
import re

# Import the config module
from config import (
    Config,
    DEFAULT_MODEL_ID,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_AWS_REGION,
    DEFAULT_DYNAMODB_TABLE_NAME,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    _parse_float,
)


# =============================================================================
# Property 12: 配置默认值属性
# Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
# 
# *对于任意* 缺失的配置参数，系统应使用预定义的默认值，
# 且默认值应为有效值（如 model_id 应为有效的 Bedrock 模型 ID）。
#
# **Validates: Requirements 8.4**
# =============================================================================

# Strategy for generating subsets of environment variable names to unset
ENV_VAR_NAMES = [
    "MODEL_ID",
    "SYSTEM_PROMPT",
    "AWS_REGION",
    "DYNAMODB_TABLE_NAME",
    "MAX_TOKENS",
    "TEMPERATURE",
]

# Strategy for generating random subsets of env vars to unset
env_vars_to_unset = st.lists(
    st.sampled_from(ENV_VAR_NAMES),
    min_size=0,
    max_size=len(ENV_VAR_NAMES),
    unique=True
)


def is_valid_bedrock_model_id(model_id: str) -> bool:
    """
    Check if a model_id is a valid Bedrock model ID format.
    
    Valid Bedrock model IDs follow patterns like:
    - anthropic.claude-3-sonnet-20240229-v1:0
    - amazon.titan-text-express-v1
    - meta.llama2-70b-chat-v1
    """
    if not model_id:
        return False
    
    # Must contain a dot separating provider and model name
    if "." not in model_id:
        return False
    
    # Known valid providers
    valid_providers = ["anthropic", "amazon", "meta", "cohere", "ai21", "stability", "mistral"]
    provider = model_id.split(".")[0]
    
    return provider in valid_providers


def is_valid_aws_region(region: str) -> bool:
    """
    Check if a region string is a valid AWS region format.
    
    AWS regions follow patterns like:
    - us-west-2
    - eu-central-1
    - ap-northeast-1
    """
    if not region:
        return False
    
    # AWS region pattern: letters-direction-number
    pattern = r'^[a-z]{2,}-[a-z]+-\d+$'
    return bool(re.match(pattern, region))


class TestProperty12ConfigDefaultValues:
    """
    Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
    
    Tests that for any combination of missing environment variables,
    the Config.from_environment() method returns valid default values.
    
    **Validates: Requirements 8.4**
    """
    
    @given(env_vars_to_unset)
    @settings(max_examples=20)
    def test_missing_env_vars_use_valid_defaults(self, vars_to_unset):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Property: For any combination of missing configuration parameters,
        the system should use predefined default values, and the default
        values should be valid.
        
        **Validates: Requirements 8.4**
        """
        # Store original environment
        original_env = {}
        for var in ENV_VAR_NAMES:
            original_env[var] = os.environ.get(var)
        
        try:
            # Unset the selected environment variables
            for var in vars_to_unset:
                if var in os.environ:
                    del os.environ[var]
            
            # Load config from environment
            config = Config.from_environment()
            
            # Verify default values are used for unset variables
            if "MODEL_ID" in vars_to_unset:
                assert config.model_id == DEFAULT_MODEL_ID
            
            if "SYSTEM_PROMPT" in vars_to_unset:
                assert config.system_prompt == DEFAULT_SYSTEM_PROMPT
            
            if "AWS_REGION" in vars_to_unset:
                assert config.aws_region == DEFAULT_AWS_REGION
            
            if "DYNAMODB_TABLE_NAME" in vars_to_unset:
                assert config.dynamodb_table_name == DEFAULT_DYNAMODB_TABLE_NAME
            
            if "MAX_TOKENS" in vars_to_unset:
                assert config.max_tokens == DEFAULT_MAX_TOKENS
            
            if "TEMPERATURE" in vars_to_unset:
                assert config.temperature == DEFAULT_TEMPERATURE
            
            # Verify all default values are valid
            # model_id should be a valid Bedrock model ID
            assert is_valid_bedrock_model_id(config.model_id), \
                f"model_id '{config.model_id}' is not a valid Bedrock model ID"
            
            # temperature should be in [0, 1]
            assert 0.0 <= config.temperature <= 1.0, \
                f"temperature {config.temperature} is not in valid range [0, 1]"
            
            # max_tokens should be positive
            assert config.max_tokens > 0, \
                f"max_tokens {config.max_tokens} is not positive"
            
            # system_prompt should not be empty
            assert len(config.system_prompt) > 0, \
                "system_prompt should not be empty"
            
            # aws_region should be a valid AWS region format
            assert is_valid_aws_region(config.aws_region), \
                f"aws_region '{config.aws_region}' is not a valid AWS region format"
            
            # dynamodb_table_name should not be empty
            assert len(config.dynamodb_table_name) > 0, \
                "dynamodb_table_name should not be empty"
        
        finally:
            # Restore original environment
            for var, value in original_env.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
    
    @given(st.text(alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='\x00'), min_size=0, max_size=50))
    @settings(max_examples=20)
    def test_invalid_max_tokens_uses_default(self, invalid_value):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Property: When MAX_TOKENS environment variable contains an invalid
        (non-integer) value, the system should use the default value.
        
        **Validates: Requirements 8.4**
        """
        # Skip if the value happens to be a valid integer
        try:
            int(invalid_value)
            assume(False)  # Skip this test case
        except (ValueError, TypeError):
            pass  # Continue with the test
        
        # Store original environment
        original_max_tokens = os.environ.get("MAX_TOKENS")
        
        try:
            # Set invalid MAX_TOKENS value
            os.environ["MAX_TOKENS"] = invalid_value
            
            # Load config from environment
            config = Config.from_environment()
            
            # Should use default value
            assert config.max_tokens == DEFAULT_MAX_TOKENS
            assert config.max_tokens > 0
        
        finally:
            # Restore original environment
            if original_max_tokens is not None:
                os.environ["MAX_TOKENS"] = original_max_tokens
            elif "MAX_TOKENS" in os.environ:
                del os.environ["MAX_TOKENS"]
    
    @given(st.text(alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='\x00'), min_size=0, max_size=50))
    @settings(max_examples=20)
    def test_invalid_temperature_uses_default_or_clamps(self, invalid_value):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Property: When TEMPERATURE environment variable contains an invalid
        value, the system should use the default value. If it's a valid float
        but out of range, it should be clamped to [0, 1]. NaN and infinity
        values should use the default.
        
        **Validates: Requirements 8.4**
        """
        import math
        
        # Store original environment
        original_temperature = os.environ.get("TEMPERATURE")
        
        try:
            # Set the TEMPERATURE value
            os.environ["TEMPERATURE"] = invalid_value
            
            # Load config from environment
            config = Config.from_environment()
            
            # Temperature should always be in valid range [0, 1]
            assert 0.0 <= config.temperature <= 1.0, \
                f"temperature {config.temperature} is not in valid range [0, 1]"
            
            # If the value was not a valid float, should use default
            try:
                parsed = float(invalid_value)
                # NaN and infinity should use default
                if math.isnan(parsed) or math.isinf(parsed):
                    assert config.temperature == DEFAULT_TEMPERATURE
                # If it parsed successfully, it should be clamped
                elif parsed < 0.0:
                    assert config.temperature == 0.0
                elif parsed > 1.0:
                    assert config.temperature == 1.0
                else:
                    assert config.temperature == parsed
            except (ValueError, TypeError):
                # Invalid float should use default
                assert config.temperature == DEFAULT_TEMPERATURE
        
        finally:
            # Restore original environment
            if original_temperature is not None:
                os.environ["TEMPERATURE"] = original_temperature
            elif "TEMPERATURE" in os.environ:
                del os.environ["TEMPERATURE"]
    
    @given(st.floats(allow_nan=False, allow_infinity=False))
    @settings(max_examples=20)
    def test_temperature_clamping_for_any_float(self, float_value):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Property: For any float value provided as TEMPERATURE, the resulting
        temperature should be clamped to the valid range [0, 1].
        
        **Validates: Requirements 8.4**
        """
        # Store original environment
        original_temperature = os.environ.get("TEMPERATURE")
        
        try:
            # Set the TEMPERATURE value
            os.environ["TEMPERATURE"] = str(float_value)
            
            # Load config from environment
            config = Config.from_environment()
            
            # Temperature should always be in valid range [0, 1]
            assert 0.0 <= config.temperature <= 1.0, \
                f"temperature {config.temperature} is not in valid range [0, 1] for input {float_value}"
            
            # Verify clamping behavior
            if float_value < 0.0:
                assert config.temperature == 0.0
            elif float_value > 1.0:
                assert config.temperature == 1.0
            else:
                assert config.temperature == float_value
        
        finally:
            # Restore original environment
            if original_temperature is not None:
                os.environ["TEMPERATURE"] = original_temperature
            elif "TEMPERATURE" in os.environ:
                del os.environ["TEMPERATURE"]
    
    @given(st.integers())
    @settings(max_examples=20)
    def test_valid_max_tokens_integer_values(self, int_value):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Property: For any valid integer value provided as MAX_TOKENS,
        the config should use that value (the validation happens separately).
        
        **Validates: Requirements 8.4**
        """
        # Store original environment
        original_max_tokens = os.environ.get("MAX_TOKENS")
        
        try:
            # Set the MAX_TOKENS value
            os.environ["MAX_TOKENS"] = str(int_value)
            
            # Load config from environment
            config = Config.from_environment()
            
            # Should use the provided integer value
            assert config.max_tokens == int_value
        
        finally:
            # Restore original environment
            if original_max_tokens is not None:
                os.environ["MAX_TOKENS"] = original_max_tokens
            elif "MAX_TOKENS" in os.environ:
                del os.environ["MAX_TOKENS"]


class TestDefaultValuesValidity:
    """
    Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
    
    Additional tests to verify that all predefined default values are valid.
    
    **Validates: Requirements 8.4**
    """
    
    def test_default_model_id_is_valid_bedrock_format(self):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Verify DEFAULT_MODEL_ID is a valid Bedrock model ID.
        
        **Validates: Requirements 8.4**
        """
        assert is_valid_bedrock_model_id(DEFAULT_MODEL_ID), \
            f"DEFAULT_MODEL_ID '{DEFAULT_MODEL_ID}' is not a valid Bedrock model ID"
    
    def test_default_temperature_in_valid_range(self):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Verify DEFAULT_TEMPERATURE is in valid range [0, 1].
        
        **Validates: Requirements 8.4**
        """
        assert 0.0 <= DEFAULT_TEMPERATURE <= 1.0, \
            f"DEFAULT_TEMPERATURE {DEFAULT_TEMPERATURE} is not in valid range [0, 1]"
    
    def test_default_max_tokens_is_positive(self):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Verify DEFAULT_MAX_TOKENS is positive.
        
        **Validates: Requirements 8.4**
        """
        assert DEFAULT_MAX_TOKENS > 0, \
            f"DEFAULT_MAX_TOKENS {DEFAULT_MAX_TOKENS} is not positive"
    
    def test_default_system_prompt_is_not_empty(self):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Verify DEFAULT_SYSTEM_PROMPT is not empty.
        
        **Validates: Requirements 8.4**
        """
        assert len(DEFAULT_SYSTEM_PROMPT) > 0, \
            "DEFAULT_SYSTEM_PROMPT should not be empty"
    
    def test_default_aws_region_is_valid_format(self):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Verify DEFAULT_AWS_REGION is a valid AWS region format.
        
        **Validates: Requirements 8.4**
        """
        assert is_valid_aws_region(DEFAULT_AWS_REGION), \
            f"DEFAULT_AWS_REGION '{DEFAULT_AWS_REGION}' is not a valid AWS region format"
    
    def test_default_dynamodb_table_name_is_not_empty(self):
        """
        Feature: bedrock-qa-validation-system, Property 12: 配置默认值属性
        
        Verify DEFAULT_DYNAMODB_TABLE_NAME is not empty.
        
        **Validates: Requirements 8.4**
        """
        assert len(DEFAULT_DYNAMODB_TABLE_NAME) > 0, \
            "DEFAULT_DYNAMODB_TABLE_NAME should not be empty"


# Import utility functions for sorting and filtering tests
from utils import (
    sort_chunks_by_confidence,
    filter_chunks_by_confidence,
    clamp_confidence_threshold,
)


# =============================================================================
# Property 3: 召回内容排序属性
# Feature: bedrock-qa-validation-system, Property 3: 召回内容排序属性
#
# *对于任意* 问答响应中的召回内容列表，列表中的元素应按 confidenceScore 降序排列，
# 即对于任意相邻元素 chunks[i] 和 chunks[i+1]，
# chunks[i].confidenceScore >= chunks[i+1].confidenceScore。
#
# **Validates: Requirements 3.4**
# =============================================================================

# Strategy for generating chunks with confidence scores
chunk_strategy = st.fixed_dictionaries({
    'confidenceScore': st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    'content': st.text(min_size=1, max_size=100),
    'chunkId': st.text(min_size=1, max_size=20),
})

chunks_list_strategy = st.lists(chunk_strategy, min_size=0, max_size=20)


class TestProperty3ChunkSorting:
    """
    Feature: bedrock-qa-validation-system, Property 3: 召回内容排序属性
    
    Tests that chunks are always sorted by confidence score in descending order.
    
    **Validates: Requirements 3.4**
    """
    
    @given(chunks_list_strategy)
    @settings(max_examples=20)
    def test_chunks_sorted_by_confidence_descending(self, chunks):
        """
        Feature: bedrock-qa-validation-system, Property 3: 召回内容排序属性
        
        Property: For any list of retrieved chunks, after sorting,
        adjacent elements should satisfy chunks[i].confidenceScore >= chunks[i+1].confidenceScore.
        
        **Validates: Requirements 3.4**
        """
        sorted_chunks = sort_chunks_by_confidence(chunks)
        
        # Verify descending order
        for i in range(len(sorted_chunks) - 1):
            assert sorted_chunks[i]['confidenceScore'] >= sorted_chunks[i + 1]['confidenceScore'], \
                f"Chunks not sorted: {sorted_chunks[i]['confidenceScore']} < {sorted_chunks[i + 1]['confidenceScore']}"
    
    @given(chunks_list_strategy)
    @settings(max_examples=20)
    def test_sorting_preserves_all_elements(self, chunks):
        """
        Feature: bedrock-qa-validation-system, Property 3: 召回内容排序属性
        
        Property: Sorting should preserve all elements (no elements lost or duplicated).
        
        **Validates: Requirements 3.4**
        """
        sorted_chunks = sort_chunks_by_confidence(chunks)
        
        # Same length
        assert len(sorted_chunks) == len(chunks)
        
        # All original elements present (by content)
        original_contents = set(c['content'] for c in chunks)
        sorted_contents = set(c['content'] for c in sorted_chunks)
        assert original_contents == sorted_contents


# =============================================================================
# Property 5: 置信度过滤属性
# Feature: bedrock-qa-validation-system, Property 5: 置信度过滤属性
#
# *对于任意* 置信度阈值 T 和召回内容列表，过滤后显示的所有内容项的 
# confidenceScore 都应大于或等于 T。
#
# **Validates: Requirements 6.3**
# =============================================================================

class TestProperty5ConfidenceFiltering:
    """
    Feature: bedrock-qa-validation-system, Property 5: 置信度过滤属性
    
    Tests that filtered chunks all have confidence scores >= threshold.
    
    **Validates: Requirements 6.3**
    """
    
    @given(
        chunks_list_strategy,
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=20)
    def test_filtered_chunks_above_threshold(self, chunks, threshold):
        """
        Feature: bedrock-qa-validation-system, Property 5: 置信度过滤属性
        
        Property: For any threshold T and chunk list, all filtered chunks
        should have confidenceScore >= T.
        
        **Validates: Requirements 6.3**
        """
        filtered = filter_chunks_by_confidence(chunks, threshold)
        
        for chunk in filtered:
            assert chunk['confidenceScore'] >= threshold, \
                f"Chunk with score {chunk['confidenceScore']} should not pass threshold {threshold}"
    
    @given(
        chunks_list_strategy,
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=20)
    def test_filtering_removes_only_below_threshold(self, chunks, threshold):
        """
        Feature: bedrock-qa-validation-system, Property 5: 置信度过滤属性
        
        Property: Filtering should only remove chunks below threshold,
        not any chunks at or above threshold.
        
        **Validates: Requirements 6.3**
        """
        filtered = filter_chunks_by_confidence(chunks, threshold)
        
        # Count chunks that should pass
        expected_count = sum(1 for c in chunks if c['confidenceScore'] >= threshold)
        
        assert len(filtered) == expected_count, \
            f"Expected {expected_count} chunks, got {len(filtered)}"


# =============================================================================
# Property 6: 置信度阈值范围属性
# Feature: bedrock-qa-validation-system, Property 6: 置信度阈值范围属性
#
# *对于任意* 置信度阈值设置操作，设置的值应在 [0.0, 1.0] 范围内。
# 超出范围的值应被限制到边界值。
#
# **Validates: Requirements 6.1**
# =============================================================================

class TestProperty6ThresholdClamping:
    """
    Feature: bedrock-qa-validation-system, Property 6: 置信度阈值范围属性
    
    Tests that confidence threshold is always clamped to [0.0, 1.0].
    
    **Validates: Requirements 6.1**
    """
    
    @given(st.floats(allow_nan=False, allow_infinity=False))
    @settings(max_examples=20)
    def test_threshold_always_in_valid_range(self, value):
        """
        Feature: bedrock-qa-validation-system, Property 6: 置信度阈值范围属性
        
        Property: For any input value, the clamped threshold should be in [0.0, 1.0].
        
        **Validates: Requirements 6.1**
        """
        clamped = clamp_confidence_threshold(value)
        
        assert 0.0 <= clamped <= 1.0, \
            f"Clamped value {clamped} is not in valid range [0.0, 1.0]"
    
    @given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=20)
    def test_values_in_range_unchanged(self, value):
        """
        Feature: bedrock-qa-validation-system, Property 6: 置信度阈值范围属性
        
        Property: Values already in [0.0, 1.0] should remain unchanged.
        
        **Validates: Requirements 6.1**
        """
        clamped = clamp_confidence_threshold(value)
        
        assert clamped == value, \
            f"Value {value} in range should be unchanged, got {clamped}"
    
    @given(st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False))
    @settings(max_examples=20)
    def test_negative_values_clamped_to_zero(self, value):
        """
        Feature: bedrock-qa-validation-system, Property 6: 置信度阈值范围属性
        
        Property: Negative values should be clamped to 0.0.
        
        **Validates: Requirements 6.1**
        """
        clamped = clamp_confidence_threshold(value)
        
        assert clamped == 0.0, \
            f"Negative value {value} should be clamped to 0.0, got {clamped}"
    
    @given(st.floats(min_value=1.001, allow_nan=False, allow_infinity=False))
    @settings(max_examples=20)
    def test_values_above_one_clamped_to_one(self, value):
        """
        Feature: bedrock-qa-validation-system, Property 6: 置信度阈值范围属性
        
        Property: Values above 1.0 should be clamped to 1.0.
        
        **Validates: Requirements 6.1**
        """
        clamped = clamp_confidence_threshold(value)
        
        assert clamped == 1.0, \
            f"Value {value} above 1.0 should be clamped to 1.0, got {clamped}"



# =============================================================================
# Property 8, 9, 10, 11: 数据访问层属性测试
# =============================================================================

# Import db module for data access layer tests
from db import SessionRepository, generate_session_id
import boto3
from moto import mock_aws


# Fixture-like context manager for DynamoDB mock
class DynamoDBMock:
    """Context manager for mocking DynamoDB"""
    
    def __enter__(self):
        self.mock = mock_aws()
        self.mock.start()
        
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        self.table = dynamodb.create_table(
            TableName='qa-validation-sessions',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
        )
        self.table.wait_until_exists()
        
        self.repository = SessionRepository('qa-validation-sessions', region='us-west-2')
        return self.repository
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mock.stop()


# Strategy for generating valid session data
# Use floats with reasonable precision to avoid DynamoDB Decimal underflow
safe_float_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_subnormal=False)

session_strategy = st.fixed_dictionaries({
    'user_id': st.text(min_size=1, max_size=10, alphabet='abcdefghij'),
    'question': st.text(min_size=1, max_size=20, alphabet='abcdefghij '),
    'answer': st.text(min_size=1, max_size=20, alphabet='abcdefghij '),
    'retrieved_chunks': st.just([]),  # Empty list for faster tests
    'confidence_threshold': st.just(0.5),  # Fixed value for faster tests
})

# Strategy for valid ratings
rating_strategy = st.integers(min_value=1, max_value=5)


class TestProperty8RatingPersistenceRoundTrip:
    """
    Feature: bedrock-qa-validation-system, Property 8: 评分持久化往返属性
    
    *对于任意* 评分操作（无论是对召回内容还是回答），保存评分后立即查询该记录，
    返回的评分值应与保存的值相等。
    
    **Validates: Requirements 4.2, 5.2**
    """
    
    @given(session_strategy, rating_strategy)
    @settings(max_examples=10, deadline=None)
    def test_answer_rating_round_trip(self, session_data, rating):
        """
        Feature: bedrock-qa-validation-system, Property 8: 评分持久化往返属性
        
        Property: After saving an answer rating, querying the record should
        return the same rating value.
        
        **Validates: Requirements 4.2, 5.2**
        """
        with DynamoDBMock() as repository:
            # Save session
            session_id = repository.save_session(session_data)
            
            # Update rating
            result = repository.update_rating(
                session_id=session_id,
                user_id=session_data['user_id'],
                chunk_id=None,
                rating=rating
            )
            
            assert result is True
            
            # Query and verify
            saved = repository.get_session(session_id, session_data['user_id'])
            assert saved['answerRating'] == rating


class TestProperty9RatingUpdate:
    """
    Feature: bedrock-qa-validation-system, Property 9: 评分更新属性
    
    *对于任意* 已有评分的记录，更新评分后查询该记录，返回的评分值应等于最新更新的值，
    而非原始值。
    
    **Validates: Requirements 4.3, 5.3, 7.3**
    """
    
    @given(session_strategy, rating_strategy, rating_strategy)
    @settings(max_examples=10, deadline=None)
    def test_rating_update_overwrites_previous(self, session_data, first_rating, second_rating):
        """
        Feature: bedrock-qa-validation-system, Property 9: 评分更新属性
        
        Property: After updating a rating, the new value should overwrite
        the previous value.
        
        **Validates: Requirements 4.3, 5.3, 7.3**
        """
        # Skip if ratings are the same (can't verify overwrite)
        assume(first_rating != second_rating)
        
        with DynamoDBMock() as repository:
            # Save session
            session_id = repository.save_session(session_data)
            
            # Set first rating
            repository.update_rating(
                session_id=session_id,
                user_id=session_data['user_id'],
                chunk_id=None,
                rating=first_rating
            )
            
            # Update to second rating
            repository.update_rating(
                session_id=session_id,
                user_id=session_data['user_id'],
                chunk_id=None,
                rating=second_rating
            )
            
            # Query and verify it's the second rating
            saved = repository.get_session(session_id, session_data['user_id'])
            assert saved['answerRating'] == second_rating
            assert saved['answerRating'] != first_rating


class TestProperty10SessionDataIntegrity:
    """
    Feature: bedrock-qa-validation-system, Property 10: 会话数据完整性属性
    
    *对于任意* 保存到 DynamoDB 的会话记录，记录应包含以下所有字段：
    userId、question、answer、retrievedChunks、timestamp、sessionId。
    
    **Validates: Requirements 7.1, 7.2**
    """
    
    @given(session_strategy)
    @settings(max_examples=10, deadline=None)
    def test_saved_session_has_all_required_fields(self, session_data):
        """
        Feature: bedrock-qa-validation-system, Property 10: 会话数据完整性属性
        
        Property: Every saved session should contain all required fields.
        
        **Validates: Requirements 7.1, 7.2**
        """
        with DynamoDBMock() as repository:
            # Save session
            session_id = repository.save_session(session_data)
            
            # Query
            saved = repository.get_session(session_id, session_data['user_id'])
            
            # Verify all required fields exist
            assert 'userId' in saved, "Missing userId"
            assert 'question' in saved, "Missing question"
            assert 'answer' in saved, "Missing answer"
            assert 'retrievedChunks' in saved, "Missing retrievedChunks"
            assert 'timestamp' in saved, "Missing timestamp"
            assert 'sessionId' in saved, "Missing sessionId"
            
            # Verify values match input
            assert saved['userId'] == session_data['user_id']
            assert saved['question'] == session_data['question']
            assert saved['answer'] == session_data['answer']
            assert len(saved['retrievedChunks']) == len(session_data['retrieved_chunks'])


class TestProperty11SessionIdUniqueness:
    """
    Feature: bedrock-qa-validation-system, Property 11: 会话ID唯一性属性
    
    *对于任意* 两个不同的会话记录，它们的 sessionId 应不相等。
    
    **Validates: Requirements 7.4**
    """
    
    @given(st.integers(min_value=2, max_value=10))
    @settings(max_examples=5, deadline=None)
    def test_generated_session_ids_are_unique(self, count):
        """
        Feature: bedrock-qa-validation-system, Property 11: 会话ID唯一性属性
        
        Property: All generated session IDs should be unique.
        
        **Validates: Requirements 7.4**
        """
        session_ids = [generate_session_id() for _ in range(count)]
        
        # All IDs should be unique
        assert len(session_ids) == len(set(session_ids)), \
            f"Duplicate session IDs found in {count} generated IDs"
    
    @given(session_strategy, session_strategy)
    @settings(max_examples=5, deadline=None)
    def test_saved_sessions_have_unique_ids(self, session1, session2):
        """
        Feature: bedrock-qa-validation-system, Property 11: 会话ID唯一性属性
        
        Property: Different saved sessions should have different session IDs.
        
        **Validates: Requirements 7.4**
        """
        with DynamoDBMock() as repository:
            # Save two sessions
            id1 = repository.save_session(session1)
            id2 = repository.save_session(session2)
            
            # IDs should be different
            assert id1 != id2, "Two sessions should have different IDs"
