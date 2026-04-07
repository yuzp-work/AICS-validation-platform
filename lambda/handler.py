"""
Lambda Handler Module

Main entry point for the Lambda function.
Handles API Gateway requests for the QA validation system.

Requirements:
- 2.1: WHEN 用户提交问题 THEN QA_System SHALL 接收问题并调用 Bedrock_Agent
- 2.3: THE 问答响应 SHALL 包含：答案文本、召回内容列表、置信度分数、会话ID
- 2.5: WHEN 问题为空或无效 THEN QA_System SHALL 返回适当的错误信息
- 7.1: WHEN 问答完成 THEN QA_System SHALL 将完整的 Session 信息保存到 DynamoDB_Table
"""

from typing import List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os

from config import Config
from agent import QAAgent
from db import SessionRepository
from utils import sort_chunks_by_confidence, filter_chunks_by_confidence

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# =============================================================================
# Error Classes (Requirement 2.5)
# =============================================================================

class QAError(Exception):
    """Base exception for QA system errors"""
    
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class ValidationError(QAError):
    """Raised when request validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")
        self.field = field


class AuthenticationError(QAError):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401, error_code="AUTHENTICATION_ERROR")


class NotFoundError(QAError):
    """Raised when a resource is not found"""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, error_code="NOT_FOUND")


class RateLimitError(QAError):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RetrievedChunk:
    """召回的知识库片段"""
    chunk_id: str
    content: str
    confidence_score: float
    source: str
    rating: Optional[int] = None


@dataclass
class QARequest:
    """问答请求"""
    question: str
    confidence_threshold: float = 0.5
    user_id: str = ""


@dataclass
class QAResponse:
    """问答响应"""
    session_id: str
    question: str
    answer: str
    retrieved_chunks: List[RetrievedChunk]
    timestamp: str
    answer_rating: Optional[int] = None
    feedback: Optional[str] = None


# =============================================================================
# Validation Functions (Requirement 2.5)
# =============================================================================

def validate_qa_request(body: Any) -> dict:
    """
    验证问答请求
    
    Args:
        body: 请求体（可能是字符串或字典）
        
    Returns:
        验证后的请求字典
        
    Raises:
        ValidationError: 当验证失败时
        
    验证: 需求 2.5 - WHEN 问题为空或无效 THEN QA_System SHALL 返回适当的错误信息
    """
    # Parse JSON if string
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {str(e)}")
    
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    
    # Validate question field
    question = body.get('question')
    if question is None:
        raise ValidationError("Missing required field: question", field="question")
    
    if not isinstance(question, str):
        raise ValidationError("Field 'question' must be a string", field="question")
    
    question = question.strip()
    if len(question) == 0:
        raise ValidationError("Field 'question' cannot be empty", field="question")
    
    if len(question) > 2000:
        raise ValidationError("Field 'question' exceeds maximum length of 2000 characters", field="question")
    
    # Validate confidence_threshold (optional)
    confidence_threshold = body.get('confidenceThreshold', 0.5)
    if not isinstance(confidence_threshold, (int, float)):
        raise ValidationError("Field 'confidenceThreshold' must be a number", field="confidenceThreshold")
    
    # Clamp to valid range
    confidence_threshold = max(0.0, min(1.0, float(confidence_threshold)))
    
    return {
        'question': question,
        'confidence_threshold': confidence_threshold,
    }


def validate_rating(body: Any) -> dict:
    """
    验证评分请求
    
    Args:
        body: 请求体
        
    Returns:
        验证后的评分字典
        
    Raises:
        ValidationError: 当验证失败时
    """
    # Parse JSON if string
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {str(e)}")
    
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    
    # Validate rating field
    rating = body.get('rating')
    if rating is None:
        raise ValidationError("Missing required field: rating", field="rating")
    
    if not isinstance(rating, int):
        raise ValidationError("Field 'rating' must be an integer", field="rating")
    
    if not 1 <= rating <= 5:
        raise ValidationError("Field 'rating' must be between 1 and 5", field="rating")
    
    # Validate optional chunkId
    chunk_id = body.get('chunkId')
    if chunk_id is not None and not isinstance(chunk_id, str):
        raise ValidationError("Field 'chunkId' must be a string", field="chunkId")
    
    # Validate optional feedback
    feedback = body.get('feedback')
    if feedback is not None:
        if not isinstance(feedback, str):
            raise ValidationError("Field 'feedback' must be a string", field="feedback")
        if len(feedback) > 1000:
            raise ValidationError("Field 'feedback' exceeds maximum length of 1000 characters", field="feedback")
    
    return {
        'rating': rating,
        'chunk_id': chunk_id,
        'feedback': feedback,
    }


def extract_user_info(event: dict) -> dict:
    """
    从 API Gateway 事件中提取用户信息
    
    Args:
        event: API Gateway 事件
        
    Returns:
        包含 user_id 和 email 的字典
        
    Raises:
        AuthenticationError: 当无法提取用户信息时
    """
    user_info = {'user_id': None, 'email': None}
    
    # Try to get from Cognito authorizer claims
    try:
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        user_info['user_id'] = claims.get('sub') or claims.get('cognito:username')
        user_info['email'] = claims.get('email')
        if user_info['user_id']:
            return user_info
    except (KeyError, TypeError):
        pass
    
    # Try to get from JWT authorizer
    try:
        jwt = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {})
        claims = jwt.get('claims', {})
        user_info['user_id'] = claims.get('sub')
        user_info['email'] = claims.get('email')
        if user_info['user_id']:
            return user_info
    except (KeyError, TypeError):
        pass
    
    raise AuthenticationError("Unable to extract user info from request")


def extract_user_id(event: dict) -> str:
    """
    从 API Gateway 事件中提取用户 ID（兼容旧代码）
    
    Args:
        event: API Gateway 事件
        
    Returns:
        用户 ID
        
    Raises:
        AuthenticationError: 当无法提取用户 ID 时
    """
    return extract_user_info(event)['user_id']


# =============================================================================
# Response Helpers
# =============================================================================

def success_response(body: Any, status_code: int = 200) -> dict:
    """
    创建成功响应
    
    Args:
        body: 响应体
        status_code: HTTP 状态码
        
    Returns:
        API Gateway 响应格式
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        },
        'body': json.dumps(body, ensure_ascii=False),
    }


def error_response(error: QAError) -> dict:
    """
    创建错误响应
    
    Args:
        error: QAError 异常
        
    Returns:
        API Gateway 响应格式
        
    验证: 需求 2.5
    """
    body = {
        'error': {
            'code': error.error_code,
            'message': error.message,
        }
    }
    
    if isinstance(error, ValidationError) and error.field:
        body['error']['field'] = error.field
    
    return {
        'statusCode': error.status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        },
        'body': json.dumps(body, ensure_ascii=False),
    }


# =============================================================================
# Handler Functions
# =============================================================================

# Global instances (initialized on cold start)
_config: Optional[Config] = None
_agent: Optional[QAAgent] = None
_repository: Optional[SessionRepository] = None


def _get_config() -> Config:
    """Get or create Config instance"""
    global _config
    if _config is None:
        _config = Config.from_environment()
    return _config


def _get_agent() -> QAAgent:
    """Get or create QAAgent instance"""
    global _agent
    if _agent is None:
        config = _get_config()
        _agent = QAAgent(
            knowledge_base_id=config.knowledge_base_id,
            model_id=config.model_id,
            system_prompt=config.system_prompt,
            region=config.aws_region,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
    return _agent


def _get_repository() -> SessionRepository:
    """Get or create SessionRepository instance"""
    global _repository
    if _repository is None:
        config = _get_config()
        _repository = SessionRepository(
            table_name=config.dynamodb_table_name,
            region=config.aws_region
        )
    return _repository


def handler(event: dict, context) -> dict:
    """
    Lambda 入口函数
    
    Args:
        event: API Gateway 事件，包含请求体和认证信息
        context: Lambda 上下文
        
    Returns:
        API Gateway 响应格式的字典
        
    验证: 需求 2.1, 2.3, 2.5, 7.1
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Handle CORS preflight
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', ''))
        if http_method == 'OPTIONS':
            return success_response({})
        
        # Extract path and route
        path = event.get('path', event.get('rawPath', ''))
        resource = event.get('resource', path)
        
        # Route to appropriate handler
        if resource == '/qa' and http_method == 'POST':
            return handle_qa_request(event)
        elif resource == '/qa/history' and http_method == 'GET':
            return handle_get_history(event)
        elif resource == '/qa/{sessionId}' and http_method == 'GET':
            return handle_get_session(event)
        elif resource == '/qa/{sessionId}/rating' and http_method == 'PUT':
            return handle_rating(event)
        elif resource == '/qa/{sessionId}/chunk-feedback' and http_method == 'PUT':
            return handle_chunk_feedback(event)
        else:
            return error_response(NotFoundError(f"Route not found: {http_method} {path}"))
    
    except QAError as e:
        logger.warning(f"QA Error: {e.message}")
        return error_response(e)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return error_response(QAError(f"Internal server error: {str(e)}"))


def handle_qa_request(event: dict) -> dict:
    """
    处理问答请求 POST /qa
    
    Args:
        event: API Gateway 事件
        
    Returns:
        API Gateway 响应
        
    验证: 需求 2.1, 2.2, 2.3, 7.1
    """
    # Extract user info from JWT
    user_info = extract_user_info(event)
    user_id = user_info['user_id']
    user_email = user_info['email']
    
    # Validate request body
    body = event.get('body', '{}')
    validated = validate_qa_request(body)
    
    question = validated['question']
    confidence_threshold = validated['confidence_threshold']
    
    logger.info(f"Processing QA request for user {user_email or user_id}: {question[:50]}...")
    
    # Get config for model and knowledge base info
    config = _get_config()
    
    # Call QA Agent
    agent = _get_agent()
    answer, chunks = agent.ask(question, confidence_threshold)

    # Log retrieved chunks for debugging
    logger.info(f"Retrieved {len(chunks)} chunks from knowledge base")
    if chunks:
        logger.info(f"First chunk from agent: {chunks[0]}")

    # Chunks are already filtered and sorted by agent.ask, no need to filter again
    # Just use them directly
    filtered_chunks = chunks
    logger.info(f"Using {len(filtered_chunks)} chunks from agent (already filtered and sorted)")
    
    # Save session to DynamoDB
    repository = _get_repository()
    session_data = {
        'user_id': user_id,
        'user_email': user_email or '',
        'question': question,
        'answer': answer,
        'retrieved_chunks': filtered_chunks,  # Save chunks (already filtered by agent)
        'confidence_threshold': confidence_threshold,
        'model_id': config.model_id,
        'knowledge_base_id': config.knowledge_base_id,
    }
    session_id = repository.save_session(session_data)
    
    # Build response
    response_body = {
        'sessionId': session_id,
        'question': question,
        'answer': answer,
        'retrievedChunks': [
            {
                'chunkId': c.get('chunk_id', ''),
                'content': c.get('content', ''),
                'question': c.get('question', ''),  # Include question field from CSV metadata
                'confidenceScore': c.get('confidence_score', 0.0),
                'source': c.get('source', ''),
            }
            for c in filtered_chunks
        ],
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'confidenceThreshold': confidence_threshold,
    }

    # Debug log
    logger.info(f"Returning {len(filtered_chunks)} chunks")
    if filtered_chunks:
        logger.info(f"First chunk: {filtered_chunks[0]}")
    
    logger.info(f"QA request completed: session_id={session_id}")
    return success_response(response_body)


def handle_get_history(event: dict) -> dict:
    """
    获取历史记录 GET /qa/history
    
    Args:
        event: API Gateway 事件
        
    Returns:
        API Gateway 响应
        
    验证: 需求 7.5
    """
    user_id = extract_user_id(event)
    
    # Get query parameters
    params = event.get('queryStringParameters') or {}
    limit = min(int(params.get('limit', 20)), 100)
    
    repository = _get_repository()
    sessions = repository.get_sessions_by_user(user_id, limit=limit)
    
    # Format response
    response_body = {
        'sessions': [
            {
                'sessionId': s.get('sessionId'),
                'question': s.get('question'),
                'answer': s.get('answer', '')[:200] + '...' if len(s.get('answer', '')) > 200 else s.get('answer', ''),
                'timestamp': s.get('timestamp'),
                'answerRating': s.get('answerRating'),
                'confidenceThreshold': s.get('confidenceThreshold'),
            }
            for s in sessions
        ]
    }
    
    return success_response(response_body)


def handle_get_session(event: dict) -> dict:
    """
    获取单个会话 GET /qa/{sessionId}
    
    Args:
        event: API Gateway 事件
        
    Returns:
        API Gateway 响应
    """
    user_id = extract_user_id(event)
    
    # Get session ID from path
    path_params = event.get('pathParameters') or {}
    session_id = path_params.get('sessionId')
    
    if not session_id:
        raise ValidationError("Missing sessionId in path")
    
    repository = _get_repository()
    session = repository.get_session(session_id, user_id)
    
    if not session:
        raise NotFoundError(f"Session not found: {session_id}")

    # Remove internal fields
    session.pop('_sk', None)

    # Normalize retrievedChunks field names from snake_case to camelCase
    if 'retrievedChunks' in session:
        session['retrievedChunks'] = [
            {
                'chunkId': c.get('chunkId') or c.get('chunk_id', ''),
                'content': c.get('content', ''),
                'question': c.get('question', ''),
                'confidenceScore': c.get('confidenceScore') if c.get('confidenceScore') is not None else c.get('confidence_score', 0.0),
                'source': c.get('source', ''),
                'rating': c.get('rating'),
                'feedback': c.get('feedback'),
            }
            for c in session['retrievedChunks']
        ]

    return success_response(session)


def handle_rating(event: dict) -> dict:
    """
    更新评分 PUT /qa/{sessionId}/rating
    
    Args:
        event: API Gateway 事件
        
    Returns:
        API Gateway 响应
        
    验证: 需求 4.2, 4.3, 5.2, 5.3
    """
    user_id = extract_user_id(event)
    
    # Get session ID from path
    path_params = event.get('pathParameters') or {}
    session_id = path_params.get('sessionId')
    
    if not session_id:
        raise ValidationError("Missing sessionId in path")
    
    # Validate request body
    body = event.get('body', '{}')
    validated = validate_rating(body)
    
    repository = _get_repository()
    success = repository.update_rating(
        session_id=session_id,
        user_id=user_id,
        chunk_id=validated['chunk_id'],
        rating=validated['rating'],
        feedback=validated['feedback']
    )
    
    if not success:
        raise NotFoundError(f"Session not found or update failed: {session_id}")
    
    return success_response({'success': True})


def handle_chunk_feedback(event: dict) -> dict:
    """
    保存召回内容的文字反馈 PUT /qa/{sessionId}/chunk-feedback

    Args:
        event: API Gateway 事件

    Returns:
        API Gateway 响应
    """
    user_id = extract_user_id(event)

    # Get session ID from path
    path_params = event.get('pathParameters') or {}
    session_id = path_params.get('sessionId')

    if not session_id:
        raise ValidationError("Missing sessionId in path")

    # Parse and validate request body
    body = event.get('body', '{}')
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {str(e)}")

    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")

    # Validate chunkId
    chunk_id = body.get('chunkId')
    if not chunk_id or not isinstance(chunk_id, str):
        raise ValidationError("Missing or invalid field: chunkId", field="chunkId")

    # Validate feedback
    feedback = body.get('feedback')
    if feedback is not None:
        if not isinstance(feedback, str):
            raise ValidationError("Field 'feedback' must be a string", field="feedback")
        if len(feedback) > 1000:
            raise ValidationError("Field 'feedback' exceeds maximum length of 1000 characters", field="feedback")

    repository = _get_repository()
    success = repository.update_chunk_feedback(
        session_id=session_id,
        user_id=user_id,
        chunk_id=chunk_id,
        feedback=feedback or ''
    )

    if not success:
        raise NotFoundError(f"Session or chunk not found: {session_id}/{chunk_id}")

    return success_response({'success': True})


def process_qa(request: QARequest) -> QAResponse:
    """
    处理问答请求（内部方法）

    Args:
        request: 问答请求对象

    Returns:
        问答响应对象
    """
    # This is now handled by handle_qa_request
    pass
