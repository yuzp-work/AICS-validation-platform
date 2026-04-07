/**
 * QA Interface Component
 * 
 * Main component for the question-answering interface.
 * Includes question input, answer display, and chunk list.
 * 
 * Requirements:
 * - 2.1: WHEN 用户提交问题 THEN QA_System SHALL 接收问题
 * - 2.4: THE Frontend SHALL 显示加载状态直到收到响应
 * - 5.1: THE Frontend SHALL 在回答下方显示评分组件
 * - 5.4: THE 评分组件 SHALL 支持可选的文字反馈
 * - 10.1: THE Frontend SHALL 提供问题输入区域
 * - 10.2: THE Frontend SHALL 提供提交按钮
 * - 10.3: THE Frontend SHALL 显示回答区域
 */

import React, { useState, useEffect } from 'react';
import { QARequest, QASession } from '../types';
import ConfidenceSlider from './ConfidenceSlider';
import ChunkList from './ChunkList';
import RatingStars from './RatingStars';
import './QAInterface.css';

interface QAInterfaceProps {
  onSubmit: (request: QARequest) => Promise<QASession>;
  onRateChunk: (sessionId: string, chunkId: string, rating: number) => Promise<void>;
  onRateAnswer: (sessionId: string, rating: number, feedback?: string) => Promise<void>;
  onSaveChunkFeedback?: (sessionId: string, chunkId: string, feedback: string) => Promise<void>;
  selectedSession?: QASession | null;
  sessionLoading?: boolean;
  onClearSelection?: () => void;
}

/**
 * 问答界面主组件
 * 
 * 验证: 需求 2.1, 2.4, 5.1, 5.4, 10.1, 10.2, 10.3
 */
export const QAInterface: React.FC<QAInterfaceProps> = ({
  onSubmit,
  onRateChunk,
  onRateAnswer,
  onSaveChunkFeedback,
  selectedSession,
  sessionLoading = false,
  onClearSelection
}) => {
  const [question, setQuestion] = useState('');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [session, setSession] = useState<QASession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  
  // Use selected session from history if available
  // When submitting a new question, prefer the local session over selectedSession
  const displaySession = selectedSession || session;
  const isHistoryView = !!selectedSession;

  // Debug: Log displaySession changes
  useEffect(() => {
    console.log('[QAInterface] selectedSession:', selectedSession?.sessionId);
    console.log('[QAInterface] local session:', session?.sessionId);
    console.log('[QAInterface] displaySession changed:', displaySession);
    console.log('[QAInterface] displaySession.retrievedChunks:', displaySession?.retrievedChunks);
    console.log('[QAInterface] isHistoryView:', isHistoryView);
  }, [displaySession, selectedSession, session, isHistoryView]);

  // Reset feedback when session changes
  useEffect(() => {
    if (selectedSession) {
      setFeedback(selectedSession.feedback || '');
      setShowFeedback(!!selectedSession.feedback);
    }
  }, [selectedSession]);
  
  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }
    
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await onSubmit({
        question: question.trim(),
        confidenceThreshold,
      });
      console.log('[QAInterface] Submit result:', result);
      console.log('[QAInterface] Retrieved chunks:', result.retrievedChunks);
      console.log('[QAInterface] Chunks length:', result.retrievedChunks?.length || 0);
      setSession(result);
      setFeedback('');
      setShowFeedback(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit question');
    } finally {
      setLoading(false);
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to submit, Shift+Enter for new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading && question.trim()) {
        handleSubmit();
      }
    }
  };
  
  const handleRateChunk = async (chunkId: string, rating: number) => {
    if (!displaySession) return;
    
    try {
      await onRateChunk(displaySession.sessionId, chunkId, rating);
      // Update local state only if not viewing history (history updates handled by parent)
      if (!isHistoryView) {
        setSession(prev => {
          if (!prev) return null;
          return {
            ...prev,
            retrievedChunks: prev.retrievedChunks.map(chunk =>
              chunk.chunkId === chunkId ? { ...chunk, rating } : chunk
            ),
          };
        });
      }
    } catch (err) {
      console.error('Failed to rate chunk:', err);
    }
  };
  
  const handleRateAnswer = async (rating: number) => {
    if (!displaySession) return;
    
    try {
      await onRateAnswer(displaySession.sessionId, rating, feedback || undefined);
      // Update local state only if not viewing history
      if (!isHistoryView) {
        setSession(prev => prev ? { ...prev, answerRating: rating, feedback } : null);
      }
    } catch (err) {
      console.error('Failed to rate answer:', err);
    }
  };
  
  const handleNewQuestion = () => {
    if (onClearSelection) {
      onClearSelection();
    }
    setSession(null);
    setQuestion('');
    setFeedback('');
    setShowFeedback(false);
  };
  
  return (
    <div className="qa-interface">
      {!isHistoryView && (
        <form className="qa-interface__form" onSubmit={handleSubmit}>
          <div className="qa-interface__input-group">
            <label htmlFor="question" className="qa-interface__label">
              Ask a Question
            </label>
            <textarea
              id="question"
              className="qa-interface__textarea"
              placeholder="Enter your question... (Enter to submit, Shift+Enter for new line)"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              rows={3}
            />
          </div>
          
          <div className="qa-interface__controls">
            <ConfidenceSlider
              value={confidenceThreshold}
              onChange={setConfidenceThreshold}
              disabled={loading}
            />
            
            <button
              type="submit"
              className="qa-interface__submit"
              disabled={loading || !question.trim()}
            >
              {loading ? 'Processing...' : 'Submit Question'}
            </button>
          </div>
        </form>
      )}
      
      {isHistoryView && (
        <div className="qa-interface__history-header">
          <h3>Viewing History</h3>
          <button 
            className="qa-interface__new-question"
            onClick={handleNewQuestion}
          >
            ← Ask New Question
          </button>
        </div>
      )}
      
      {error && (
        <div className="qa-interface__error">
          {error}
        </div>
      )}
      
      {(loading || sessionLoading) && (
        <div className="qa-interface__loading">
          <div className="qa-interface__spinner" />
          <p>{sessionLoading ? 'Loading session...' : 'Searching knowledge base and generating answer...'}</p>
        </div>
      )}
      
      {displaySession && !loading && !sessionLoading && (
        <div className="qa-interface__result">
          {isHistoryView && (
            <div className="qa-interface__question-display">
              <h3>Question</h3>
              <p>{displaySession.question}</p>
              {displaySession.confidenceThreshold !== undefined && (
                <div className="qa-interface__confidence-display">
                  Confidence Threshold: {Math.round(displaySession.confidenceThreshold * 100)}%
                </div>
              )}
            </div>
          )}
          
          <div className="qa-interface__answer">
            <h3>Answer</h3>
            <div className="qa-interface__answer-text">
              {displaySession.answer}
            </div>
            
            <div className="qa-interface__answer-rating">
              <span>Rate this answer:</span>
              <RatingStars
                value={displaySession.answerRating}
                onChange={handleRateAnswer}
                size="medium"
              />
              
              <button
                type="button"
                className="qa-interface__feedback-toggle"
                onClick={() => setShowFeedback(!showFeedback)}
              >
                {showFeedback ? 'Hide feedback' : 'Add feedback'}
              </button>
            </div>
            
            {showFeedback && (
              <div className="qa-interface__feedback">
                <textarea
                  placeholder="Optional: Add your feedback about this answer..."
                  value={feedback}
                  onChange={(e) => {
                    setFeedback(e.target.value);
                    setFeedbackSaved(false);
                  }}
                  rows={2}
                />
                <div className="qa-interface__feedback-actions">
                  <button
                    type="button"
                    className="qa-interface__feedback-save"
                    onClick={async () => {
                      if (!displaySession) return;
                      try {
                        await onRateAnswer(displaySession.sessionId, displaySession.answerRating || 0, feedback || undefined);
                        setFeedbackSaved(true);
                        setTimeout(() => setFeedbackSaved(false), 3000);
                      } catch (err) {
                        console.error('Failed to save feedback:', err);
                        setError('Failed to save feedback. Please try again.');
                      }
                    }}
                    disabled={!feedback.trim()}
                  >
                    Save Feedback
                  </button>
                  {feedbackSaved && (
                    <span className="qa-interface__feedback-success">
                      ✓ Saved
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {displaySession.retrievedChunks && displaySession.retrievedChunks.length > 0 ? (
            <ChunkList
              chunks={displaySession.retrievedChunks}
              onRate={handleRateChunk}
              onSaveFeedback={onSaveChunkFeedback ? async (chunkId, feedback) => {
                await onSaveChunkFeedback(displaySession.sessionId, chunkId, feedback);
              } : undefined}
            />
          ) : (
            <div style={{padding: '20px', textAlign: 'center', color: '#666'}}>
              No retrieved chunks available for this session.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default QAInterface;
