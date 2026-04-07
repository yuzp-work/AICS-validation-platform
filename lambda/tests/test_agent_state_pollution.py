"""
Test for Agent State Pollution Bug Fix

This test verifies that the agent.messages history is properly cleared
between requests to prevent state pollution.
"""

import pytest
from unittest.mock import MagicMock, patch


def test_agent_messages_cleared_between_calls():
    """
    Test that agent.messages is cleared between successive ask() calls
    to prevent state pollution from previous questions.

    This is a regression test for the bug where:
    1. First question creates 6 messages (2 retrieve calls)
    2. Second question should start fresh, not accumulate to 10 messages
    """
    from agent import QAAgent

    # Mock the Bedrock components
    with patch('agent.BedrockModel') as MockModel, \
         patch('agent.Agent') as MockAgent, \
         patch('agent.retrieve'):

        # Create mock agent instance
        mock_agent_instance = MagicMock()
        mock_agent_instance.messages = []  # Start with empty messages
        mock_agent_instance.system_prompt = "Test prompt"
        MockAgent.return_value = mock_agent_instance

        # Mock response for first call
        mock_response_1 = MagicMock()
        mock_response_1.message = {'role': 'assistant', 'content': [{'text': 'Answer 1'}]}

        # Mock response for second call
        mock_response_2 = MagicMock()
        mock_response_2.message = {'role': 'assistant', 'content': [{'text': 'Answer 2'}]}

        # Set up agent to return different responses
        mock_agent_instance.side_effect = [mock_response_1, mock_response_2]

        # Create QAAgent
        qa_agent = QAAgent(
            knowledge_base_id="test-kb",
            model_id="test-model",
            system_prompt="Test prompt"
        )

        # Simulate first question - artificially add messages
        qa_agent._agent.messages = [
            {'role': 'user', 'content': 'Question 1'},
            {'role': 'assistant', 'content': [{'toolUse': 'retrieve'}]},
            {'role': 'user', 'content': [{'toolResult': {'status': 'success'}}]},
            {'role': 'assistant', 'content': [{'toolUse': 'retrieve'}]},
            {'role': 'user', 'content': [{'toolResult': {'status': 'success'}}]},
            {'role': 'assistant', 'content': [{'text': 'Answer 1'}]}
        ]

        # Verify messages exist after first question
        assert len(qa_agent._agent.messages) == 6, "Should have 6 messages after first question"

        # Call ask() for second question
        try:
            qa_agent.ask("Question 2", confidence_threshold=0.5)
        except:
            pass  # We don't care about the actual execution, just the state reset

        # CRITICAL: Verify that messages were cleared
        # The fix should set messages = [] at the start of ask()
        assert len(qa_agent._agent.messages) == 0, \
            "Agent messages should be cleared at the start of ask() to prevent state pollution"


def test_chunk_extraction_with_empty_results():
    """
    Test that chunk extraction handles empty retrieve results gracefully.

    This tests the scenario where retrieve tool returns results but
    all chunks are filtered out (e.g., no Answer field).
    """
    from agent import QAAgent

    qa_agent = QAAgent(
        knowledge_base_id="test-kb",
        model_id="test-model",
        system_prompt="Test prompt"
    )

    # Simulate messages with retrieve result that has no valid chunks
    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'toolResult': {
                        'status': 'success',
                        'toolUseId': 'test-1',
                        'content': [
                            {
                                'text': 'Retrieved 5 results with score >= 0.5:\nScore: 0.6\nDocument ID: s3://test\nContent: Question only\nMetadata: {}'
                            }
                        ]
                    }
                }
            ]
        }
    ]

    # Should return empty list without error
    chunks = qa_agent._extract_chunks_from_messages(messages, confidence_threshold=0.5)

    assert isinstance(chunks, list), "Should return a list"
    assert len(chunks) == 0, "Should return empty list when no valid chunks found"


def test_chunk_deduplication():
    """
    Test that duplicate chunks (same chunk_id) are deduplicated
    and the one with highest confidence score is kept.
    """
    from agent import QAAgent

    qa_agent = QAAgent(
        knowledge_base_id="test-kb",
        model_id="test-model",
        system_prompt="Test prompt"
    )

    # Simulate messages with duplicate chunks
    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'toolResult': {
                        'status': 'success',
                        'toolUseId': 'test-1',
                        'content': [
                            {
                                'text': '''Retrieved 2 results with score >= 0.5:
Score: 0.8
Document ID: s3://test/file.csv
Content: How to join?
Metadata: {'x-amz-bedrock-kb-chunk-id': 'chunk-1', 'Answer': 'Click the button'}

Score: 0.9
Document ID: s3://test/file.csv
Content: How to join?
Metadata: {'x-amz-bedrock-kb-chunk-id': 'chunk-1', 'Answer': 'Click the button'}'''
                            }
                        ]
                    }
                }
            ]
        }
    ]

    chunks = qa_agent._extract_chunks_from_messages(messages, confidence_threshold=0.5)

    assert len(chunks) == 1, "Should deduplicate chunks with same chunk_id"
    assert chunks[0]['confidence_score'] == 0.9, "Should keep the chunk with highest score"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
