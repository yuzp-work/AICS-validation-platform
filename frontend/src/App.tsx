/**
 * Main Application Component
 * 
 * Handles routing and authentication state.
 * 
 * Requirements:
 * - 1.1: WHEN 用户访问系统 THEN 系统 SHALL 显示登录界面（未登录时）
 */

import React, { useState, useEffect, useCallback } from 'react';
import { AuthService } from './services/auth';
import { QAApiService } from './services/api';
import { AuthUser } from './types';
import LoginPage from './pages/LoginPage';
import MainPage from './pages/MainPage';
import config from './config';
import './App.css';

// Initialize services
const authService = new AuthService({
  userPoolId: config.userPoolId,
  clientId: config.userPoolClientId,
  region: config.region,
});

const apiService = new QAApiService(
  config.apiUrl,
  () => authService.getIdToken()  // API Gateway Cognito Authorizer requires ID Token
);

function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (authService.isAuthenticated()) {
        try {
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
        } catch (err) {
          console.error('Failed to get current user:', err);
        }
      }
      setLoading(false);
    };
    
    checkAuth();
  }, []);
  
  const handleLogin = useCallback(async (username: string, password: string, newPassword?: string) => {
    const loggedInUser = await authService.signIn(username, password, newPassword);
    setUser(loggedInUser);
  }, []);
  
  const handleLogout = useCallback(async () => {
    await authService.signOut();
    setUser(null);
  }, []);
  
  if (loading) {
    return (
      <div className="app-loading">
        <div className="app-loading__spinner" />
        <p>Loading...</p>
      </div>
    );
  }
  
  // Show login page if not authenticated
  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }
  
  // Show main page if authenticated
  return (
    <MainPage
      onLogout={handleLogout}
      onSubmitQuestion={(req) => apiService.submitQuestion(req)}
      onRateChunk={(sessionId, chunkId, rating) => apiService.rateChunk(sessionId, chunkId, rating)}
      onRateAnswer={(sessionId, rating, feedback) => apiService.rateAnswer(sessionId, rating, feedback)}
      onSaveChunkFeedback={(sessionId, chunkId, feedback) => apiService.saveChunkFeedback(sessionId, chunkId, feedback)}
      onGetHistory={(limit) => apiService.getHistory(limit)}
      onGetSession={(sessionId) => apiService.getSession(sessionId)}
      username={user.username}
    />
  );
}

export default App;
