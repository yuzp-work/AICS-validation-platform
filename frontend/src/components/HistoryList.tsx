/**
 * History List Component
 * 
 * Displays a list of past QA sessions.
 * 
 * Requirements:
 * - 10.4: THE Frontend SHALL 显示历史问答列表
 * - 10.6: THE 历史列表 SHALL 支持点击加载详情
 */

import React from 'react';
import { QASession } from '../types';
import './HistoryList.css';

interface HistoryListProps {
  sessions: QASession[];
  onSelect: (sessionId: string) => void;
  loading?: boolean;
  selectedId?: string;
}

/**
 * 历史记录组件
 * 
 * 验证: 需求 10.4, 10.6
 */
export const HistoryList: React.FC<HistoryListProps> = ({ 
  sessions, 
  onSelect,
  loading = false,
  selectedId 
}) => {
  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  const truncateText = (text: string, maxLength: number = 80) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };
  
  if (loading) {
    return (
      <div className="history-list history-list--loading">
        <h3 className="history-list__title">History</h3>
        <div className="history-list__spinner" />
      </div>
    );
  }
  
  return (
    <div className="history-list">
      <h3 className="history-list__title">History</h3>
      
      {sessions.length === 0 ? (
        <p className="history-list__empty">No history yet. Ask a question to get started!</p>
      ) : (
        <div className="history-list__items">
          {sessions.map((session) => (
            <div 
              key={session.sessionId} 
              className={`history-item ${selectedId === session.sessionId ? 'history-item--selected' : ''}`}
              onClick={() => onSelect(session.sessionId)}
              role="button"
              tabIndex={0}
              onKeyPress={(e) => e.key === 'Enter' && onSelect(session.sessionId)}
            >
              <div className="history-item__question">
                {truncateText(session.question)}
              </div>
              <div className="history-item__meta">
                <span className="history-item__time">{formatDate(session.timestamp)}</span>
                <span className="history-item__confidence">
                  {session.confidenceThreshold !== undefined 
                    ? `${Math.round(session.confidenceThreshold * 100)}%` 
                    : '-'}
                </span>
                {session.answerRating && (
                  <span className="history-item__rating">
                    {'★'.repeat(session.answerRating)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HistoryList;
