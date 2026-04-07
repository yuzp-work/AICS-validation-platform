/**
 * Chunk List Component
 * 
 * Displays retrieved knowledge base chunks with confidence scores
 * and rating functionality.
 * 
 * Requirements:
 * - 3.1: THE Frontend SHALL 显示召回内容列表
 * - 3.2: THE 召回内容项 SHALL 包含：内容摘要、来源信息、置信度分数
 * - 3.3: THE Frontend SHALL 支持展开/折叠召回内容详情
 * - 3.4: THE 召回内容列表 SHALL 按置信度分数降序排列
 * - 4.1: THE Frontend SHALL 在每个召回内容项旁显示评分组件
 */

import React, { useState } from 'react';
import { RetrievedChunk } from '../types';
import RatingStars from './RatingStars';
import './ChunkList.css';

interface ChunkListProps {
  chunks: RetrievedChunk[];
  onRate: (chunkId: string, rating: number) => void;
  onSaveFeedback?: (chunkId: string, feedback: string) => Promise<void>;
  loading?: boolean;
}

/**
 * 召回内容列表组件
 * 
 * 验证: 需求 3.1, 3.2, 3.3, 3.4, 4.1
 */
export const ChunkList: React.FC<ChunkListProps> = ({ chunks, onRate, onSaveFeedback, loading = false }) => {
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());
  const [chunkFeedbacks, setChunkFeedbacks] = useState<Record<string, string>>({});
  const [showFeedbackFor, setShowFeedbackFor] = useState<Set<string>>(new Set());
  const [savedFeedbacks, setSavedFeedbacks] = useState<Set<string>>(new Set());

  // Initialize feedback from chunks - only update if chunk data actually changed
  React.useEffect(() => {
    const feedbacks: Record<string, string> = {};
    const showFeedback = new Set<string>();

    chunks.forEach(chunk => {
      console.log('[ChunkList] Chunk ID:', chunk.chunkId, 'Feedback:', chunk.feedback);
      if (chunk.feedback) {
        feedbacks[chunk.chunkId] = chunk.feedback;
        showFeedback.add(chunk.chunkId);
      }
    });

    // Only update if different from current state (preserve user input)
    setChunkFeedbacks(prev => {
      const needsUpdate = chunks.some(chunk =>
        chunk.feedback && prev[chunk.chunkId] !== chunk.feedback
      );
      if (needsUpdate) {
        return { ...prev, ...feedbacks };
      }
      return prev;
    });

    setShowFeedbackFor(prev => {
      const needsUpdate = chunks.some(chunk =>
        chunk.feedback && !prev.has(chunk.chunkId)
      );
      if (needsUpdate) {
        const newSet = new Set(prev);
        showFeedback.forEach(id => newSet.add(id));
        return newSet;
      }
      return prev;
    });
  }, [chunks]);

  // Debug: Log chunks data
  React.useEffect(() => {
    console.log('[ChunkList] Received chunks:', chunks);
    console.log('[ChunkList] Chunks count:', chunks?.length || 0);
    if (chunks && chunks.length > 0) {
      console.log('[ChunkList] First chunk:', chunks[0]);
      console.log('[ChunkList] All chunk IDs:', chunks.map(c => c.chunkId));
      console.log('[ChunkList] All chunk ratings:', chunks.map(c => ({ id: c.chunkId, rating: c.rating, feedback: c.feedback })));
    }
    console.log('[ChunkList] Current chunkFeedbacks state:', chunkFeedbacks);
  }, [chunks, chunkFeedbacks]);

  const toggleExpand = (chunkId: string) => {
    setExpandedChunks(prev => {
      const next = new Set(prev);
      if (next.has(chunkId)) {
        next.delete(chunkId);
      } else {
        next.add(chunkId);
      }
      return next;
    });
  };

  const toggleFeedback = (chunkId: string) => {
    setShowFeedbackFor(prev => {
      const next = new Set(prev);
      if (next.has(chunkId)) {
        next.delete(chunkId);
      } else {
        next.add(chunkId);
      }
      return next;
    });
  };

  const handleSaveFeedback = async (chunkId: string) => {
    if (!onSaveFeedback) return;

    const feedback = chunkFeedbacks[chunkId] || '';
    try {
      await onSaveFeedback(chunkId, feedback);
      setSavedFeedbacks(prev => new Set(prev).add(chunkId));
      setTimeout(() => {
        setSavedFeedbacks(prev => {
          const next = new Set(prev);
          next.delete(chunkId);
          return next;
        });
      }, 3000);
    } catch (err) {
      console.error('Failed to save chunk feedback:', err);
      // Error handling could be improved with a toast notification
    }
  };

  // Chunks should already be sorted by confidence (from backend)
  // But we ensure it here for display
  const sortedChunks = [...chunks].sort((a, b) => b.confidenceScore - a.confidenceScore);
  
  if (loading) {
    return (
      <div className="chunk-list chunk-list--loading">
        <div className="chunk-list__spinner" />
        <p>Loading chunks...</p>
      </div>
    );
  }
  
  if (sortedChunks.length === 0) {
    return (
      <div className="chunk-list chunk-list--empty">
        <p>No retrieved chunks available.</p>
      </div>
    );
  }
  
  return (
    <div className="chunk-list">
      <h3 className="chunk-list__title">
        Retrieved Chunks ({sortedChunks.length})
      </h3>
      <div className="chunk-list__items">
        {sortedChunks.map((chunk, index) => {
          const isExpanded = expandedChunks.has(chunk.chunkId);
          const confidencePercent = Math.round(chunk.confidenceScore * 100);
          
          return (
            <div 
              key={chunk.chunkId} 
              className={`chunk-item ${isExpanded ? 'chunk-item--expanded' : ''}`}
            >
              <div className="chunk-item__header" onClick={() => toggleExpand(chunk.chunkId)}>
                <span className="chunk-item__index">#{index + 1}</span>
                <div className="chunk-item__confidence">
                  <div 
                    className="chunk-item__confidence-bar"
                    style={{ width: `${confidencePercent}%` }}
                  />
                  <span className="chunk-item__confidence-value">{confidencePercent}%</span>
                </div>
                <button 
                  className="chunk-item__toggle"
                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                >
                  {isExpanded ? '▼' : '▶'}
                </button>
              </div>
              
              <div className="chunk-item__content">
                {chunk.question && (
                  <div className={`chunk-item__qa ${isExpanded ? '' : 'chunk-item__content--truncated'}`}>
                    <p className="chunk-item__question"><strong>Q:</strong> {chunk.question}</p>
                    <p className="chunk-item__answer-text"><strong>A:</strong> {chunk.content}</p>
                  </div>
                )}
                {!chunk.question && (
                  <p className={isExpanded ? '' : 'chunk-item__content--truncated'}>
                    {chunk.content}
                  </p>
                )}
              </div>
              
              {isExpanded && (
                <div className="chunk-item__details">
                  {chunk.source && (
                    <div className="chunk-item__source">
                      <strong>Source:</strong> {chunk.source}
                    </div>
                  )}
                  <div className="chunk-item__rating">
                    <span>Rate this chunk:</span>
                    <RatingStars
                      value={chunk.rating}
                      onChange={(rating) => {
                        console.log(`[ChunkList] Rating chunk ${chunk.chunkId} with rating ${rating}`);
                        onRate(chunk.chunkId, rating);
                      }}
                      size="small"
                    />
                    {onSaveFeedback && (
                      <button
                        type="button"
                        className="chunk-item__feedback-toggle"
                        onClick={() => toggleFeedback(chunk.chunkId)}
                      >
                        {showFeedbackFor.has(chunk.chunkId) ? 'Hide feedback' : 'Add feedback'}
                      </button>
                    )}
                  </div>
                  {onSaveFeedback && showFeedbackFor.has(chunk.chunkId) && (
                    <div className="chunk-item__feedback">
                      <textarea
                        placeholder="Add your feedback about this retrieved chunk..."
                        value={chunkFeedbacks[chunk.chunkId] || ''}
                        onChange={(e) => {
                          setChunkFeedbacks(prev => ({
                            ...prev,
                            [chunk.chunkId]: e.target.value
                          }));
                          setSavedFeedbacks(prev => {
                            const next = new Set(prev);
                            next.delete(chunk.chunkId);
                            return next;
                          });
                        }}
                        rows={2}
                      />
                      <div className="chunk-item__feedback-actions">
                        <button
                          type="button"
                          className="chunk-item__feedback-save"
                          onClick={() => handleSaveFeedback(chunk.chunkId)}
                          disabled={!chunkFeedbacks[chunk.chunkId]?.trim()}
                        >
                          Save Feedback
                        </button>
                        {savedFeedbacks.has(chunk.chunkId) && (
                          <span className="chunk-item__feedback-success">
                            ✓ Saved
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ChunkList;
