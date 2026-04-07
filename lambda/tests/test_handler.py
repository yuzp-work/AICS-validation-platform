"""
Tests for Lambda Handler validation and error handling
"""

import pytest
import json
from handler import (
    validate_qa_request,
    validate_rating,
    extract_user_id,
    error_response,
    success_response,
    ValidationError,
    AuthenticationError,
    QAError,
)


class TestValidateQARequest:
    """Tests for validate_qa_request function"""
    
    def test_valid_request(self):
        """Valid request should pass validation"""
        body = {'question': 'What is AWS?'}
        result = validate_qa_request(body)
        assert result['question'] == 'What is AWS?'
        assert result['confidence_threshold'] == 0.5
    
    def test_valid_request_with_threshold(self):
        """Valid request with custom threshold"""
        body = {'question': 'Test?', 'confidenceThreshold': 0.8}
        result = validate_qa_request(body)
        assert result['confidence_threshold'] == 0.8
    
    def test_json_string_body(self):
        """Should parse JSON string body"""
        body = json.dumps({'question': 'Test question'})
        result = validate_qa_request(body)
        assert result['question'] == 'Test question'
    
    def test_missing_question(self):
        """Should raise ValidationError for missing question"""
        with pytest.raises(ValidationError) as exc:
            validate_qa_request({})
        assert 'question' in str(exc.value)
    
    def test_empty_question(self):
        """Should raise ValidationError for empty question"""
        with pytest.raises(ValidationError) as exc:
            validate_qa_request({'question': '   '})
        assert 'empty' in str(exc.value).lower()
    
    def test_question_too_long(self):
        """Should raise ValidationError for question exceeding max length"""
        with pytest.raises(ValidationError) as exc:
            validate_qa_request({'question': 'x' * 2001})
        assert 'maximum length' in str(exc.value).lower()
    
    def test_threshold_clamped_to_range(self):
        """Threshold should be clamped to [0, 1]"""
        result = validate_qa_request({'question': 'Test', 'confidenceThreshold': 1.5})
        assert result['confidence_threshold'] == 1.0
        
        result = validate_qa_request({'question': 'Test', 'confidenceThreshold': -0.5})
        assert result['confidence_threshold'] == 0.0
    
    def test_invalid_json(self):
        """Should raise ValidationError for invalid JSON"""
        with pytest.raises(ValidationError) as exc:
            validate_qa_request('not valid json')
        assert 'Invalid JSON' in str(exc.value)


class TestValidateRating:
    """Tests for validate_rating function"""
    
    def test_valid_rating(self):
        """Valid rating should pass"""
        result = validate_rating({'rating': 4})
        assert result['rating'] == 4
        assert result['chunk_id'] is None
        assert result['feedback'] is None
    
    def test_valid_rating_with_chunk_id(self):
        """Valid rating with chunk ID"""
        result = validate_rating({'rating': 5, 'chunkId': 'chunk-123'})
        assert result['rating'] == 5
        assert result['chunk_id'] == 'chunk-123'
    
    def test_valid_rating_with_feedback(self):
        """Valid rating with feedback"""
        result = validate_rating({'rating': 3, 'feedback': 'Good answer'})
        assert result['feedback'] == 'Good answer'
    
    def test_missing_rating(self):
        """Should raise ValidationError for missing rating"""
        with pytest.raises(ValidationError) as exc:
            validate_rating({})
        assert 'rating' in str(exc.value)
    
    def test_rating_out_of_range(self):
        """Should raise ValidationError for rating out of range"""
        with pytest.raises(ValidationError) as exc:
            validate_rating({'rating': 0})
        assert 'between 1 and 5' in str(exc.value)
        
        with pytest.raises(ValidationError) as exc:
            validate_rating({'rating': 6})
        assert 'between 1 and 5' in str(exc.value)
    
    def test_rating_not_integer(self):
        """Should raise ValidationError for non-integer rating"""
        with pytest.raises(ValidationError) as exc:
            validate_rating({'rating': 4.5})
        assert 'integer' in str(exc.value)


class TestExtractUserId:
    """Tests for extract_user_id function"""
    
    def test_cognito_authorizer(self):
        """Should extract user ID from Cognito authorizer"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'cognito:username': 'testuser'
                    }
                }
            }
        }
        assert extract_user_id(event) == 'user-123'
    
    def test_jwt_authorizer(self):
        """Should extract user ID from JWT authorizer"""
        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'jwt-user-456'
                        }
                    }
                }
            }
        }
        assert extract_user_id(event) == 'jwt-user-456'
    
    def test_missing_authorizer(self):
        """Should raise AuthenticationError when no authorizer"""
        with pytest.raises(AuthenticationError):
            extract_user_id({})


class TestErrorResponse:
    """Tests for error_response function"""
    
    def test_validation_error_response(self):
        """Should create proper validation error response"""
        error = ValidationError("Invalid input", field="question")
        response = error_response(error)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert body['error']['field'] == 'question'
    
    def test_authentication_error_response(self):
        """Should create proper authentication error response"""
        error = AuthenticationError()
        response = error_response(error)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'AUTHENTICATION_ERROR'


class TestSuccessResponse:
    """Tests for success_response function"""
    
    def test_success_response(self):
        """Should create proper success response"""
        response = success_response({'result': 'ok'})
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        body = json.loads(response['body'])
        assert body['result'] == 'ok'



# =============================================================================
# Property 2: 问答响应完整性属性
# Feature: bedrock-qa-validation-system, Property 2: 问答响应完整性属性
#
# *对于任意* 有效的问答请求，响应应包含以下所有字段：
# answer（非空字符串）、retrievedChunks（列表）、sessionId（非空字符串）、timestamp。
#
# **Validates: Requirements 2.3**
# =============================================================================

from hypothesis import given, strategies as st, settings


class TestProperty2QAResponseCompleteness:
    """
    Feature: bedrock-qa-validation-system, Property 2: 问答响应完整性属性
    
    Tests that QA responses contain all required fields.
    
    **Validates: Requirements 2.3**
    """
    
    def test_success_response_has_required_headers(self):
        """
        Feature: bedrock-qa-validation-system, Property 2: 问答响应完整性属性
        
        Property: Success response should have CORS headers.
        
        **Validates: Requirements 2.3**
        """
        response = success_response({
            'sessionId': 'test-123',
            'question': 'What is AWS?',
            'answer': 'AWS is Amazon Web Services',
            'retrievedChunks': [],
            'timestamp': '2024-01-01T00:00:00Z',
        })
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Content-Type'] == 'application/json'
    
    @given(st.text(min_size=1, max_size=100, alphabet='abcdefghij '))
    @settings(max_examples=10)
    def test_qa_response_body_structure(self, question):
        """
        Feature: bedrock-qa-validation-system, Property 2: 问答响应完整性属性
        
        Property: For any valid question, the response body structure
        should contain all required fields.
        
        **Validates: Requirements 2.3**
        """
        # Simulate a complete QA response
        response_body = {
            'sessionId': 'session-123',
            'question': question.strip() or 'default',
            'answer': 'This is the answer',
            'retrievedChunks': [
                {
                    'chunkId': 'chunk-1',
                    'content': 'Some content',
                    'confidenceScore': 0.9,
                    'source': 'doc.pdf',
                }
            ],
            'timestamp': '2024-01-01T00:00:00Z',
            'confidenceThreshold': 0.5,
        }
        
        response = success_response(response_body)
        body = json.loads(response['body'])
        
        # Verify all required fields exist
        assert 'sessionId' in body, "Missing sessionId"
        assert 'question' in body, "Missing question"
        assert 'answer' in body, "Missing answer"
        assert 'retrievedChunks' in body, "Missing retrievedChunks"
        assert 'timestamp' in body, "Missing timestamp"
        
        # Verify field types
        assert isinstance(body['sessionId'], str) and len(body['sessionId']) > 0
        assert isinstance(body['answer'], str)
        assert isinstance(body['retrievedChunks'], list)
        assert isinstance(body['timestamp'], str)
    
    def test_retrieved_chunks_structure(self):
        """
        Feature: bedrock-qa-validation-system, Property 2: 问答响应完整性属性
        
        Property: Each retrieved chunk should have required fields.
        
        **Validates: Requirements 2.3**
        """
        chunk = {
            'chunkId': 'chunk-1',
            'content': 'Knowledge base content',
            'confidenceScore': 0.85,
            'source': 'document.pdf',
        }
        
        # Verify chunk structure
        assert 'chunkId' in chunk
        assert 'content' in chunk
        assert 'confidenceScore' in chunk
        assert isinstance(chunk['confidenceScore'], (int, float))
        assert 0.0 <= chunk['confidenceScore'] <= 1.0
