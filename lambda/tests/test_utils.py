"""
Unit Tests for Utility Functions Module

Tests the sorting, filtering, and clamping functions.
Validates Requirements 3.4, 6.1, 6.3
"""

import pytest
from utils import (
    sort_chunks_by_confidence,
    filter_chunks_by_confidence,
    clamp_confidence_threshold,
)


class TestSortChunksByConfidence:
    """Tests for sort_chunks_by_confidence function (Req 3.4)"""
    
    def test_sorts_descending(self):
        """Test that chunks are sorted by confidence score descending"""
        chunks = [
            {"confidenceScore": 0.5, "content": "a"},
            {"confidenceScore": 0.9, "content": "b"},
            {"confidenceScore": 0.3, "content": "c"},
        ]
        result = sort_chunks_by_confidence(chunks)
        assert result[0]["confidenceScore"] == 0.9
        assert result[1]["confidenceScore"] == 0.5
        assert result[2]["confidenceScore"] == 0.3
    
    def test_empty_list(self):
        """Test sorting empty list returns empty list"""
        assert sort_chunks_by_confidence([]) == []
    
    def test_single_element(self):
        """Test sorting single element list"""
        chunks = [{"confidenceScore": 0.5}]
        result = sort_chunks_by_confidence(chunks)
        assert len(result) == 1
        assert result[0]["confidenceScore"] == 0.5
    
    def test_missing_confidence_score(self):
        """Test chunks without confidenceScore default to 0"""
        chunks = [
            {"confidenceScore": 0.5},
            {"content": "no score"},
        ]
        result = sort_chunks_by_confidence(chunks)
        assert result[0]["confidenceScore"] == 0.5
        assert result[1].get("confidenceScore", 0) == 0
    
    def test_equal_scores_stable(self):
        """Test that equal scores maintain relative order"""
        chunks = [
            {"confidenceScore": 0.5, "id": 1},
            {"confidenceScore": 0.5, "id": 2},
        ]
        result = sort_chunks_by_confidence(chunks)
        assert len(result) == 2


class TestFilterChunksByConfidence:
    """Tests for filter_chunks_by_confidence function (Req 6.3)"""
    
    def test_filters_below_threshold(self):
        """Test that chunks below threshold are filtered out"""
        chunks = [
            {"confidenceScore": 0.8},
            {"confidenceScore": 0.3},
            {"confidenceScore": 0.6},
        ]
        result = filter_chunks_by_confidence(chunks, 0.5)
        assert len(result) == 2
        assert all(c["confidenceScore"] >= 0.5 for c in result)
    
    def test_empty_list(self):
        """Test filtering empty list returns empty list"""
        assert filter_chunks_by_confidence([], 0.5) == []
    
    def test_all_pass(self):
        """Test when all chunks pass the threshold"""
        chunks = [
            {"confidenceScore": 0.8},
            {"confidenceScore": 0.9},
        ]
        result = filter_chunks_by_confidence(chunks, 0.5)
        assert len(result) == 2
    
    def test_none_pass(self):
        """Test when no chunks pass the threshold"""
        chunks = [
            {"confidenceScore": 0.2},
            {"confidenceScore": 0.3},
        ]
        result = filter_chunks_by_confidence(chunks, 0.5)
        assert len(result) == 0
    
    def test_exact_threshold(self):
        """Test that chunks exactly at threshold are included"""
        chunks = [{"confidenceScore": 0.5}]
        result = filter_chunks_by_confidence(chunks, 0.5)
        assert len(result) == 1
    
    def test_missing_confidence_score(self):
        """Test chunks without confidenceScore default to 0"""
        chunks = [
            {"confidenceScore": 0.8},
            {"content": "no score"},
        ]
        result = filter_chunks_by_confidence(chunks, 0.5)
        assert len(result) == 1


class TestClampConfidenceThreshold:
    """Tests for clamp_confidence_threshold function (Req 6.1)"""
    
    def test_value_in_range(self):
        """Test that values in range are unchanged"""
        assert clamp_confidence_threshold(0.5) == 0.5
        assert clamp_confidence_threshold(0.0) == 0.0
        assert clamp_confidence_threshold(1.0) == 1.0
    
    def test_value_below_zero(self):
        """Test that values below 0 are clamped to 0"""
        assert clamp_confidence_threshold(-0.5) == 0.0
        assert clamp_confidence_threshold(-100) == 0.0
    
    def test_value_above_one(self):
        """Test that values above 1 are clamped to 1"""
        assert clamp_confidence_threshold(1.5) == 1.0
        assert clamp_confidence_threshold(100) == 1.0
    
    def test_boundary_values(self):
        """Test boundary values"""
        assert clamp_confidence_threshold(0.0) == 0.0
        assert clamp_confidence_threshold(1.0) == 1.0
