/**
 * Login Page Component
 * 
 * Handles user authentication via Cognito.
 * 
 * Requirements:
 * - 1.1: WHEN 用户访问系统 THEN 系统 SHALL 显示登录界面
 * - 1.2: WHEN 用户提交凭证 THEN Cognito_UserPool SHALL 验证用户身份
 */

import React, { useState } from 'react';
import './LoginPage.css';

interface LoginPageProps {
  onLogin: (username: string, password: string, newPassword?: string) => Promise<void>;
}

/**
 * 登录页面组件
 * 
 * 验证: 需求 1.1, 1.2
 */
export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [needsNewPassword, setNeedsNewPassword] = useState(false);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!username.trim() || !password) {
      setError('Please enter username and password');
      return;
    }
    
    if (needsNewPassword) {
      if (!newPassword || !confirmPassword) {
        setError('Please enter and confirm your new password');
        return;
      }
      if (newPassword !== confirmPassword) {
        setError('New passwords do not match');
        return;
      }
      if (newPassword.length < 8) {
        setError('New password must be at least 8 characters');
        return;
      }
    }
    
    setLoading(true);
    setError(null);
    
    try {
      await onLogin(username.trim(), password, needsNewPassword ? newPassword : undefined);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      
      // Handle NEW_PASSWORD_REQUIRED challenge
      if (errorMessage === 'NEW_PASSWORD_REQUIRED') {
        setNeedsNewPassword(true);
        setError('Please set a new password for your first login');
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">QA Validation System</h1>
        <p className="login-subtitle">
          {needsNewPassword ? 'Set your new password' : 'Sign in to continue'}
        </p>
        
        <form className="login-form" onSubmit={handleSubmit}>
          {error && (
            <div className="login-error">
              {error}
            </div>
          )}
          
          <div className="login-field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              disabled={loading || needsNewPassword}
              autoComplete="username"
            />
          </div>
          
          <div className="login-field">
            <label htmlFor="password">
              {needsNewPassword ? 'Current Password' : 'Password'}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              disabled={loading || needsNewPassword}
              autoComplete="current-password"
            />
          </div>
          
          {needsNewPassword && (
            <>
              <div className="login-field">
                <label htmlFor="newPassword">New Password</label>
                <input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password (min 8 chars)"
                  disabled={loading}
                  autoComplete="new-password"
                />
              </div>
              
              <div className="login-field">
                <label htmlFor="confirmPassword">Confirm New Password</label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  disabled={loading}
                  autoComplete="new-password"
                />
              </div>
            </>
          )}
          
          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? 'Processing...' : (needsNewPassword ? 'Set Password & Sign In' : 'Sign In')}
          </button>
          
          {needsNewPassword && (
            <button
              type="button"
              className="login-button login-button-secondary"
              onClick={() => {
                setNeedsNewPassword(false);
                setNewPassword('');
                setConfirmPassword('');
                setError(null);
              }}
              disabled={loading}
            >
              Back to Login
            </button>
          )}
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
