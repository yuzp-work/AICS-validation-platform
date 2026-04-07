/**
 * Main Page Component
 * 
 * The main application page containing the QA interface and history.
 * 
 * Requirements:
 * - 1.4: WHEN 用户点击登出 THEN 系统 SHALL 清除本地令牌并重定向到登录页
 * - 10.5: THE Frontend SHALL 提供响应式布局
 */

import React, { useState, useEffect, useCallback } from 'react';
import { QASession, QARequest } from '../types';
import QAInterface from '../components/QAInterface';
import HistoryList from '../components/HistoryList';
import './MainPage.css';

interface MainPageProps {
  onLogout: () => void;
  onSubmitQuestion: (request: QARequest) => Promise<QASession>;
  onRateChunk: (sessionId: string, chunkId: string, rating: number) => Promise<void>;
  onRateAnswer: (sessionId: string, rating: number, feedback?: string) => Promise<void>;
  onSaveChunkFeedback?: (sessionId: string, chunkId: string, feedback: string) => Promise<void>;
  onGetHistory: (limit?: number) => Promise<QASession[]>;
  onGetSession: (sessionId: string) => Promise<QASession>;
  username?: string;
}

/**
 * 主页面组件
 * 
 * 验证: 需求 1.4, 10.5
 */
export const MainPage: React.FC<MainPageProps> = ({
  onLogout,
  onSubmitQuestion,
  onRateChunk,
  onRateAnswer,
  onSaveChunkFeedback,
  onGetHistory,
  onGetSession,
  username
}) => {
  const [history, setHistory] = useState<QASession[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>();
  const [selectedSession, setSelectedSession] = useState<QASession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const sessions = await onGetHistory(20);
      setHistory(sessions);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, [onGetHistory]);
  
  useEffect(() => {
    loadHistory();
  }, [loadHistory]);
  
  const handleSubmitQuestion = async (request: QARequest): Promise<QASession> => {
    // Clear selected session BEFORE submitting (to ensure new session is displayed)
    setSelectedSession(null);
    setSelectedSessionId(undefined);

    const session = await onSubmitQuestion(request);

    // Refresh history after submission
    loadHistory();
    return session;
  };
  
  const handleSelectSession = async (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setSessionLoading(true);
    try {
      const session = await onGetSession(sessionId);
      setSelectedSession(session);
    } catch (err) {
      console.error('Failed to load session:', err);
    } finally {
      setSessionLoading(false);
    }
  };
  
  const handleClearSelection = () => {
    setSelectedSession(null);
    setSelectedSessionId(undefined);
  };
  
  const handleRateChunkWithRefresh = async (sessionId: string, chunkId: string, rating: number) => {
    await onRateChunk(sessionId, chunkId, rating);
    // Update selected session if it's the current one
    if (selectedSession && selectedSession.sessionId === sessionId) {
      setSelectedSession(prev => {
        if (!prev) return null;
        return {
          ...prev,
          retrievedChunks: prev.retrievedChunks.map(chunk =>
            chunk.chunkId === chunkId ? { ...chunk, rating } : chunk
          ),
        };
      });
    }
  };
  
  const handleRateAnswerWithRefresh = async (sessionId: string, rating: number, feedback?: string) => {
    await onRateAnswer(sessionId, rating, feedback);
    // Update selected session and history
    if (selectedSession && selectedSession.sessionId === sessionId) {
      setSelectedSession(prev => prev ? { ...prev, answerRating: rating, feedback } : null);
    }
    // Update history list
    setHistory(prev => prev.map(s =>
      s.sessionId === sessionId ? { ...s, answerRating: rating } : s
    ));
  };

  const handleSaveChunkFeedback = async (sessionId: string, chunkId: string, feedback: string) => {
    if (!onSaveChunkFeedback) return;
    await onSaveChunkFeedback(sessionId, chunkId, feedback);
    // Update selected session to reflect the saved feedback
    if (selectedSession && selectedSession.sessionId === sessionId) {
      setSelectedSession(prev => {
        if (!prev) return null;
        return {
          ...prev,
          retrievedChunks: prev.retrievedChunks.map(chunk =>
            chunk.chunkId === chunkId ? { ...chunk, feedback } : chunk
          ),
        };
      });
    }
  };
  
  return (
    <div className="main-page">
      <header className="main-header">
        <div className="main-header__brand">
          <h1>QA Validation System</h1>
        </div>
        <div className="main-header__user">
          {username && <span className="main-header__username">{username}</span>}
          <button className="main-header__logout" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>
      
      <main className="main-content">
        <div className="main-content__qa">
          <QAInterface
            onSubmit={handleSubmitQuestion}
            onRateChunk={handleRateChunkWithRefresh}
            onRateAnswer={handleRateAnswerWithRefresh}
            onSaveChunkFeedback={handleSaveChunkFeedback}
            selectedSession={selectedSession}
            sessionLoading={sessionLoading}
            onClearSelection={handleClearSelection}
          />
        </div>
        
        <aside className="main-content__sidebar">
          <HistoryList
            sessions={history}
            onSelect={handleSelectSession}
            loading={historyLoading}
            selectedId={selectedSessionId}
          />
        </aside>
      </main>
    </div>
  );
};

export default MainPage;
