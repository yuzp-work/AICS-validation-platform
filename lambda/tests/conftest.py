"""
Pytest Configuration and Fixtures

Provides shared fixtures for testing the Lambda backend.
"""

import pytest
import os


@pytest.fixture(autouse=True)
def set_test_environment():
    """Set up test environment variables"""
    os.environ.setdefault("KNOWLEDGE_BASE_ID", "test-kb-id")
    os.environ.setdefault("MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
    os.environ.setdefault("SYSTEM_PROMPT", "You are a helpful assistant.")
    os.environ.setdefault("AWS_REGION", "us-west-2")
    os.environ.setdefault("DYNAMODB_TABLE_NAME", "qa-validation-sessions")
    os.environ.setdefault("MAX_TOKENS", "4096")
    os.environ.setdefault("TEMPERATURE", "0.3")
    yield


@pytest.fixture
def sample_chunks():
    """Sample retrieved chunks for testing"""
    return [
        {"chunkId": "chunk-1", "content": "Content 1", "confidenceScore": 0.9, "source": "doc1.pdf"},
        {"chunkId": "chunk-2", "content": "Content 2", "confidenceScore": 0.7, "source": "doc2.pdf"},
        {"chunkId": "chunk-3", "content": "Content 3", "confidenceScore": 0.5, "source": "doc3.pdf"},
    ]


@pytest.fixture
def sample_session():
    """Sample session data for testing"""
    return {
        "sessionId": "test-session-123",
        "userId": "user-456",
        "question": "What is AWS Lambda?",
        "answer": "AWS Lambda is a serverless compute service.",
        "retrievedChunks": [
            {"chunkId": "chunk-1", "content": "Lambda content", "confidenceScore": 0.85, "source": "lambda.pdf"}
        ],
        "timestamp": "2024-01-01T00:00:00Z",
        "confidenceThreshold": 0.5
    }
