"""
DynamoDB Data Access Module

Handles all database operations for session storage and retrieval.

Requirements:
- 7.1: WHEN 问答完成 THEN QA_System SHALL 将完整的 Session 信息保存到 DynamoDB_Table
- 7.2: THE Session 记录 SHALL 包含：用户ID、问题、答案、召回内容列表、时间戳、评分信息
- 7.3: WHEN 用户更新评分 THEN QA_System SHALL 更新对应 Session 记录中的评分字段
- 7.4: THE QA_System SHALL 为每个 Session 生成唯一的会话ID
- 7.5: THE DynamoDB_Table SHALL 支持按用户ID和时间范围查询历史记录
"""

import uuid
import logging
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """
    生成唯一的会话 ID
    
    使用 UUID4 确保唯一性。
    
    Returns:
        UUID 字符串
        
    验证: 需求 7.4 - THE QA_System SHALL 为每个 Session 生成唯一的会话ID
    """
    return str(uuid.uuid4())


class SessionRepository:
    """
    会话数据仓库
    
    负责与 DynamoDB 交互，处理会话的存储和检索。
    
    DynamoDB 表结构:
    - PK: USER#{userId}
    - SK: SESSION#{timestamp}#{sessionId}
    - GSI1PK: DATE#{date}
    - GSI1SK: {timestamp}#{sessionId}
    """
    
    def __init__(self, table_name: str, region: str = "us-west-2"):
        """
        初始化仓库
        
        Args:
            table_name: DynamoDB 表名
            region: AWS 区域
        """
        self.table_name = table_name
        self.region = region
        self._dynamodb = boto3.resource('dynamodb', region_name=region)
        self._table = self._dynamodb.Table(table_name)
        
        logger.info(f"SessionRepository initialized with table: {table_name}")
    
    def save_session(self, session: dict) -> str:
        """
        保存会话记录
        
        Args:
            session: 会话数据，应包含:
                - user_id: 用户 ID
                - user_email: 用户邮箱
                - question: 用户问题
                - answer: 模型回答
                - retrieved_chunks: 召回内容列表
                - confidence_threshold: 使用的置信度阈值
                - model_id: 使用的模型 ID
                - knowledge_base_id: 使用的知识库 ID
                
        Returns:
            会话 ID
            
        Raises:
            ValueError: 当必需字段缺失时
            ClientError: 当 DynamoDB 操作失败时
            
        验证: 需求 7.1, 7.2, 7.4
        """
        # Validate required fields
        required_fields = ['user_id', 'question', 'answer', 'retrieved_chunks']
        for field in required_fields:
            if field not in session:
                raise ValueError(f"Missing required field: {field}")
        
        # Generate session ID and timestamp
        session_id = generate_session_id()
        timestamp = datetime.utcnow().isoformat() + "Z"
        date_str = timestamp[:10]  # YYYY-MM-DD
        
        # Build DynamoDB item
        item = {
            'PK': f"USER#{session['user_id']}",
            'SK': f"SESSION#{timestamp}#{session_id}",
            'sessionId': session_id,
            'userId': session['user_id'],
            'userEmail': session.get('user_email', ''),
            'question': session['question'],
            'answer': session['answer'],
            'retrievedChunks': self._convert_to_dynamodb_format(session['retrieved_chunks']),
            'confidenceThreshold': Decimal(str(session.get('confidence_threshold', 0.5))),
            'modelId': session.get('model_id', ''),
            'knowledgeBaseId': session.get('knowledge_base_id', ''),
            'timestamp': timestamp,
            'GSI1PK': f"DATE#{date_str}",
            'GSI1SK': f"{timestamp}#{session_id}",
        }
        
        # Add optional fields
        if 'answer_rating' in session:
            item['answerRating'] = session['answer_rating']
        if 'feedback' in session:
            item['feedback'] = session['feedback']
        
        try:
            self._table.put_item(Item=item)
            logger.info(f"Session saved: {session_id}")
            return session_id
        except ClientError as e:
            logger.error(f"Failed to save session: {e}")
            raise
    
    def update_rating(
        self, 
        session_id: str,
        user_id: str,
        chunk_id: Optional[str],
        rating: int,
        feedback: Optional[str] = None
    ) -> bool:
        """
        更新评分
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            chunk_id: 召回片段 ID（None 表示对回答评分）
            rating: 评分 1-5
            feedback: 文字反馈
            
        Returns:
            是否更新成功
            
        Raises:
            ValueError: 当评分不在有效范围内时
            
        验证: 需求 4.2, 4.3, 5.2, 5.3, 7.3
        """
        # Validate rating
        if not 1 <= rating <= 5:
            raise ValueError(f"Rating must be between 1 and 5, got {rating}")
        
        # First, get the session to find the correct SK
        session = self.get_session(session_id, user_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return False
        
        pk = f"USER#{user_id}"
        sk = session['_sk']  # Internal SK from get_session
        
        try:
            if chunk_id is None:
                # Update answer rating
                update_expr = "SET answerRating = :rating"
                expr_values = {':rating': rating}
                
                if feedback:
                    update_expr += ", feedback = :feedback"
                    expr_values[':feedback'] = feedback
                
                self._table.update_item(
                    Key={'PK': pk, 'SK': sk},
                    UpdateExpression=update_expr,
                    ExpressionAttributeValues=expr_values
                )
            else:
                # Update chunk rating
                # Find the chunk index
                chunks = session.get('retrievedChunks', [])
                chunk_index = None
                for i, chunk in enumerate(chunks):
                    # Support both snake_case (stored) and camelCase (legacy) field names
                    stored_chunk_id = chunk.get('chunk_id') or chunk.get('chunkId')
                    if stored_chunk_id == chunk_id:
                        chunk_index = i
                        break
                
                if chunk_index is None:
                    logger.warning(f"Chunk not found: {chunk_id}")
                    return False
                
                self._table.update_item(
                    Key={'PK': pk, 'SK': sk},
                    UpdateExpression=f"SET retrievedChunks[{chunk_index}].rating = :rating",
                    ExpressionAttributeValues={':rating': rating}
                )
            
            logger.info(f"Rating updated for session {session_id}, chunk {chunk_id}: {rating}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update rating: {e}")
            return False

    def update_chunk_feedback(
        self,
        session_id: str,
        user_id: str,
        chunk_id: str,
        feedback: str
    ) -> bool:
        """
        更新召回内容的文字反馈

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            chunk_id: 召回片段 ID
            feedback: 文字反馈

        Returns:
            是否更新成功
        """
        # First, get the session to find the correct SK
        session = self.get_session(session_id, user_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return False

        pk = f"USER#{user_id}"
        sk = session['_sk']  # Internal SK from get_session

        try:
            # Find the chunk index
            chunks = session.get('retrievedChunks', [])
            chunk_index = None
            for i, chunk in enumerate(chunks):
                # Support both snake_case (stored) and camelCase (legacy) field names
                stored_chunk_id = chunk.get('chunk_id') or chunk.get('chunkId')
                if stored_chunk_id == chunk_id:
                    chunk_index = i
                    break

            if chunk_index is None:
                logger.warning(f"Chunk not found: {chunk_id}")
                return False

            self._table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression=f"SET retrievedChunks[{chunk_index}].feedback = :feedback",
                ExpressionAttributeValues={':feedback': feedback}
            )

            logger.info(f"Feedback updated for session {session_id}, chunk {chunk_id}")
            return True

        except ClientError as e:
            logger.error(f"Failed to update chunk feedback: {e}")
            return False

    def get_session(self, session_id: str, user_id: str) -> Optional[dict]:
        """
        获取单个会话
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            
        Returns:
            会话数据或 None
        """
        pk = f"USER#{user_id}"
        
        try:
            # Query for the session using begins_with on SK
            response = self._table.query(
                KeyConditionExpression=Key('PK').eq(pk),
                FilterExpression=Attr('sessionId').eq(session_id)
            )
            
            items = response.get('Items', [])
            if not items:
                return None
            
            item = items[0]
            return self._convert_from_dynamodb_format(item)
            
        except ClientError as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def get_sessions_by_user(
        self, 
        user_id: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20
    ) -> List[dict]:
        """
        按用户查询会话历史
        
        Args:
            user_id: 用户 ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            会话列表，按时间降序排列
            
        验证: 需求 7.5
        """
        pk = f"USER#{user_id}"
        
        try:
            # Build key condition
            key_condition = Key('PK').eq(pk)
            
            # Add time range filter if provided
            if start_time and end_time:
                start_sk = f"SESSION#{start_time.isoformat()}Z"
                end_sk = f"SESSION#{end_time.isoformat()}Z~"  # ~ is after Z in ASCII
                key_condition = key_condition & Key('SK').between(start_sk, end_sk)
            elif start_time:
                start_sk = f"SESSION#{start_time.isoformat()}Z"
                key_condition = key_condition & Key('SK').gte(start_sk)
            elif end_time:
                end_sk = f"SESSION#{end_time.isoformat()}Z~"
                key_condition = key_condition & Key('SK').lte(end_sk)
            
            response = self._table.query(
                KeyConditionExpression=key_condition,
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit
            )
            
            items = response.get('Items', [])
            return [self._convert_from_dynamodb_format(item) for item in items]
            
        except ClientError as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    def _convert_to_dynamodb_format(self, data):
        """
        将 Python 数据转换为 DynamoDB 格式
        
        主要处理 float 到 Decimal 的转换
        """
        if isinstance(data, list):
            return [self._convert_to_dynamodb_format(item) for item in data]
        elif isinstance(data, dict):
            return {k: self._convert_to_dynamodb_format(v) for k, v in data.items()}
        elif isinstance(data, float):
            return Decimal(str(data))
        else:
            return data
    
    def _convert_from_dynamodb_format(self, item: dict) -> dict:
        """
        将 DynamoDB 项转换为 Python 格式
        
        主要处理 Decimal 到 float 的转换，并移除内部字段
        """
        result = {}
        
        # Store internal SK for update operations
        result['_sk'] = item.get('SK')
        
        # Map DynamoDB fields to API response fields
        field_mapping = {
            'sessionId': 'sessionId',
            'userId': 'userId',
            'userEmail': 'userEmail',
            'question': 'question',
            'answer': 'answer',
            'retrievedChunks': 'retrievedChunks',
            'confidenceThreshold': 'confidenceThreshold',
            'modelId': 'modelId',
            'knowledgeBaseId': 'knowledgeBaseId',
            'timestamp': 'timestamp',
            'answerRating': 'answerRating',
            'feedback': 'feedback',
        }
        
        for db_field, api_field in field_mapping.items():
            if db_field in item:
                result[api_field] = self._convert_decimal(item[db_field])
        
        return result
    
    def _convert_decimal(self, data):
        """
        递归转换 Decimal 为 float
        """
        if isinstance(data, list):
            return [self._convert_decimal(item) for item in data]
        elif isinstance(data, dict):
            return {k: self._convert_decimal(v) for k, v in data.items()}
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data
