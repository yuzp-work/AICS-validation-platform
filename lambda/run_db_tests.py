#!/usr/bin/env python3
"""Simple test script for DB property tests"""

import sys
sys.path.insert(0, '.')

from db import generate_session_id

# Test Property 11: Session ID uniqueness
print("Testing Property 11: Session ID Uniqueness...")
ids = [generate_session_id() for _ in range(100)]
assert len(ids) == len(set(ids)), "Duplicate IDs found!"
print(f"  Generated {len(ids)} unique IDs - PASSED")

# Test with moto mock
print("\nTesting Property 8, 9, 10 with moto mock...")
import boto3
from moto import mock_aws

@mock_aws
def test_db_operations():
    # Create table
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
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5},
    )
    table.wait_until_exists()
    
    from db import SessionRepository
    repo = SessionRepository('qa-validation-sessions', region='us-west-2')
    
    # Test save and get (Property 10)
    session_data = {
        'user_id': 'testuser',
        'question': 'What is AWS?',
        'answer': 'AWS is Amazon Web Services',
        'retrieved_chunks': [],
        'confidence_threshold': 0.5,
    }
    
    session_id = repo.save_session(session_data)
    print(f"  Saved session: {session_id}")
    
    saved = repo.get_session(session_id, 'testuser')
    assert saved is not None, "Session not found"
    assert saved['userId'] == 'testuser'
    assert saved['question'] == 'What is AWS?'
    assert saved['answer'] == 'AWS is Amazon Web Services'
    assert 'timestamp' in saved
    assert 'sessionId' in saved
    print("  Property 10 (Data Integrity) - PASSED")
    
    # Test rating update (Property 8)
    result = repo.update_rating(session_id, 'testuser', None, 4)
    assert result is True
    saved = repo.get_session(session_id, 'testuser')
    assert saved['answerRating'] == 4
    print("  Property 8 (Rating Round-trip) - PASSED")
    
    # Test rating overwrite (Property 9)
    repo.update_rating(session_id, 'testuser', None, 5)
    saved = repo.get_session(session_id, 'testuser')
    assert saved['answerRating'] == 5
    assert saved['answerRating'] != 4
    print("  Property 9 (Rating Update) - PASSED")

test_db_operations()
print("\nAll DB property tests PASSED!")
