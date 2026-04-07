"""
Unit Tests for DynamoDB Data Access Module

Tests the SessionRepository class using moto for DynamoDB mocking.
Validates Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

import pytest
import boto3
from moto import mock_aws
from datetime import datetime, timedelta
from decimal import Decimal

from db import SessionRepository, generate_session_id


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table for testing"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        
        table = dynamodb.create_table(
            TableName='qa-validation-sessions',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5,
                    },
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
        )
        
        table.wait_until_exists()
        yield table


@pytest.fixture
def repository(dynamodb_table):
    """Create a SessionRepository instance"""
    return SessionRepository('qa-validation-sessions', region='us-west-2')


@pytest.fixture
def sample_session():
    """Create a sample session for testing"""
    return {
        'user_id': 'user-123',
        'question': 'What is AWS Lambda?',
        'answer': 'AWS Lambda is a serverless compute service.',
        'retrieved_chunks': [
            {
                'chunkId': 'chunk-1',
                'content': 'Lambda runs code without provisioning servers.',
                'confidenceScore': 0.95,
                'source': 's3://bucket/doc1.pdf',
            },
            {
                'chunkId': 'chunk-2',
                'content': 'Lambda scales automatically.',
                'confidenceScore': 0.85,
                'source': 's3://bucket/doc2.pdf',
            },
        ],
        'confidence_threshold': 0.5,
    }


class TestGenerateSessionId:
    """Tests for generate_session_id function (Req 7.4)"""
    
    def test_generates_uuid_format(self):
        """Test that session ID is in UUID format"""
        session_id = generate_session_id()
        assert len(session_id) == 36
        assert session_id.count('-') == 4
    
    def test_generates_unique_ids(self):
        """Test that generated IDs are unique"""
        ids = [generate_session_id() for _ in range(100)]
        assert len(ids) == len(set(ids))


class TestSaveSession:
    """Tests for SessionRepository.save_session (Req 7.1, 7.2)"""
    
    def test_saves_session_successfully(self, repository, sample_session):
        """Test saving a complete session"""
        session_id = repository.save_session(sample_session)
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID format
    
    def test_saves_all_required_fields(self, repository, sample_session):
        """Test that all required fields are saved (Req 7.2)"""
        session_id = repository.save_session(sample_session)
        
        # Retrieve and verify
        saved = repository.get_session(session_id, sample_session['user_id'])
        
        assert saved['userId'] == sample_session['user_id']
        assert saved['question'] == sample_session['question']
        assert saved['answer'] == sample_session['answer']
        assert len(saved['retrievedChunks']) == 2
        assert saved['timestamp'] is not None
        assert saved['sessionId'] == session_id
    
    def test_raises_on_missing_user_id(self, repository):
        """Test that missing user_id raises ValueError"""
        session = {
            'question': 'test',
            'answer': 'test',
            'retrieved_chunks': [],
        }
        with pytest.raises(ValueError, match="user_id"):
            repository.save_session(session)
    
    def test_raises_on_missing_question(self, repository):
        """Test that missing question raises ValueError"""
        session = {
            'user_id': 'user-123',
            'answer': 'test',
            'retrieved_chunks': [],
        }
        with pytest.raises(ValueError, match="question"):
            repository.save_session(session)


class TestUpdateRating:
    """Tests for SessionRepository.update_rating (Req 4.2, 4.3, 5.2, 5.3, 7.3)"""
    
    def test_updates_answer_rating(self, repository, sample_session):
        """Test updating answer rating"""
        session_id = repository.save_session(sample_session)
        
        result = repository.update_rating(
            session_id=session_id,
            user_id=sample_session['user_id'],
            chunk_id=None,
            rating=4
        )
        
        assert result is True
        
        # Verify the rating was saved
        saved = repository.get_session(session_id, sample_session['user_id'])
        assert saved['answerRating'] == 4
    
    def test_updates_answer_rating_with_feedback(self, repository, sample_session):
        """Test updating answer rating with feedback"""
        session_id = repository.save_session(sample_session)
        
        result = repository.update_rating(
            session_id=session_id,
            user_id=sample_session['user_id'],
            chunk_id=None,
            rating=5,
            feedback="Great answer!"
        )
        
        assert result is True
        
        saved = repository.get_session(session_id, sample_session['user_id'])
        assert saved['answerRating'] == 5
        assert saved['feedback'] == "Great answer!"
    
    def test_updates_chunk_rating(self, repository, sample_session):
        """Test updating chunk rating"""
        session_id = repository.save_session(sample_session)
        
        result = repository.update_rating(
            session_id=session_id,
            user_id=sample_session['user_id'],
            chunk_id='chunk-1',
            rating=3
        )
        
        assert result is True
        
        saved = repository.get_session(session_id, sample_session['user_id'])
        chunk = next(c for c in saved['retrievedChunks'] if c['chunkId'] == 'chunk-1')
        assert chunk['rating'] == 3
    
    def test_rejects_invalid_rating(self, repository, sample_session):
        """Test that invalid ratings are rejected"""
        session_id = repository.save_session(sample_session)
        
        with pytest.raises(ValueError, match="Rating must be between"):
            repository.update_rating(
                session_id=session_id,
                user_id=sample_session['user_id'],
                chunk_id=None,
                rating=0
            )
        
        with pytest.raises(ValueError, match="Rating must be between"):
            repository.update_rating(
                session_id=session_id,
                user_id=sample_session['user_id'],
                chunk_id=None,
                rating=6
            )
    
    def test_returns_false_for_nonexistent_session(self, repository):
        """Test that updating nonexistent session returns False"""
        result = repository.update_rating(
            session_id='nonexistent',
            user_id='user-123',
            chunk_id=None,
            rating=4
        )
        
        assert result is False


class TestGetSession:
    """Tests for SessionRepository.get_session"""
    
    def test_retrieves_existing_session(self, repository, sample_session):
        """Test retrieving an existing session"""
        session_id = repository.save_session(sample_session)
        
        saved = repository.get_session(session_id, sample_session['user_id'])
        
        assert saved is not None
        assert saved['sessionId'] == session_id
    
    def test_returns_none_for_nonexistent(self, repository):
        """Test that nonexistent session returns None"""
        result = repository.get_session('nonexistent', 'user-123')
        assert result is None


class TestGetSessionsByUser:
    """Tests for SessionRepository.get_sessions_by_user (Req 7.5)"""
    
    def test_retrieves_user_sessions(self, repository, sample_session):
        """Test retrieving all sessions for a user"""
        # Save multiple sessions
        repository.save_session(sample_session)
        repository.save_session(sample_session)
        repository.save_session(sample_session)
        
        sessions = repository.get_sessions_by_user(sample_session['user_id'])
        
        assert len(sessions) == 3
    
    def test_respects_limit(self, repository, sample_session):
        """Test that limit parameter is respected"""
        # Save multiple sessions
        for _ in range(5):
            repository.save_session(sample_session)
        
        sessions = repository.get_sessions_by_user(sample_session['user_id'], limit=2)
        
        assert len(sessions) == 2
    
    def test_returns_newest_first(self, repository, sample_session):
        """Test that sessions are returned newest first"""
        # Save sessions
        id1 = repository.save_session(sample_session)
        id2 = repository.save_session(sample_session)
        id3 = repository.save_session(sample_session)
        
        sessions = repository.get_sessions_by_user(sample_session['user_id'])
        
        # Newest should be first
        assert sessions[0]['sessionId'] == id3
        assert sessions[2]['sessionId'] == id1
    
    def test_returns_empty_for_no_sessions(self, repository):
        """Test that empty list is returned when no sessions exist"""
        sessions = repository.get_sessions_by_user('nonexistent-user')
        assert sessions == []
