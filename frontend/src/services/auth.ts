/**
 * Authentication Service
 * 
 * Handles Cognito authentication including sign-in, sign-out,
 * token management, and refresh.
 * 
 * Requirements:
 * - 1.1: WHEN 用户访问系统 THEN 系统 SHALL 显示登录界面
 * - 1.2: WHEN 用户提交凭证 THEN Cognito_UserPool SHALL 验证用户身份
 * - 1.3: WHEN 认证成功 THEN Cognito_UserPool SHALL 返回 JWT 令牌
 * - 1.4: WHEN 用户点击登出 THEN 系统 SHALL 清除本地令牌并重定向到登录页
 * - 1.5: THE JWT 令牌 SHALL 包含用户ID用于后续 API 请求认证
 */

import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
  RespondToAuthChallengeCommand,
  GetUserCommand,
  GlobalSignOutCommand,
  AuthFlowType,
  ChallengeNameType,
} from '@aws-sdk/client-cognito-identity-provider';
import { AuthUser } from '../types';

export interface AuthConfig {
  userPoolId: string;
  clientId: string;
  region: string;
}

// Token storage keys
const ACCESS_TOKEN_KEY = 'qa_access_token';
const REFRESH_TOKEN_KEY = 'qa_refresh_token';
const ID_TOKEN_KEY = 'qa_id_token';
const TOKEN_EXPIRY_KEY = 'qa_token_expiry';

export class AuthService {
  private client: CognitoIdentityProviderClient;
  private config: AuthConfig;
  
  constructor(config: AuthConfig) {
    this.config = config;
    this.client = new CognitoIdentityProviderClient({ region: config.region });
  }
  
  /**
   * 用户登录
   * 
   * 验证: 需求 1.2, 1.3
   */
  async signIn(username: string, password: string, newPassword?: string): Promise<AuthUser> {
    const command = new InitiateAuthCommand({
      AuthFlow: AuthFlowType.USER_PASSWORD_AUTH,
      ClientId: this.config.clientId,
      AuthParameters: {
        USERNAME: username,
        PASSWORD: password,
      },
    });
    
    const response = await this.client.send(command);
    
    // Handle NEW_PASSWORD_REQUIRED challenge (first-time login)
    if (response.ChallengeName === ChallengeNameType.NEW_PASSWORD_REQUIRED) {
      if (!newPassword) {
        throw new Error('NEW_PASSWORD_REQUIRED');
      }
      
      const challengeResponse = new RespondToAuthChallengeCommand({
        ChallengeName: ChallengeNameType.NEW_PASSWORD_REQUIRED,
        ClientId: this.config.clientId,
        Session: response.Session,
        ChallengeResponses: {
          USERNAME: username,
          NEW_PASSWORD: newPassword,
        },
      });
      
      const challengeResult = await this.client.send(challengeResponse);
      
      if (!challengeResult.AuthenticationResult) {
        throw new Error('Password change failed');
      }
      
      const { AccessToken, RefreshToken, IdToken, ExpiresIn } = challengeResult.AuthenticationResult;
      
      if (!AccessToken || !RefreshToken || !IdToken) {
        throw new Error('Authentication failed: Missing tokens after password change');
      }
      
      this.storeTokens(AccessToken, RefreshToken, IdToken, ExpiresIn || 3600);
      return this.getCurrentUser();
    }
    
    if (!response.AuthenticationResult) {
      throw new Error('Authentication failed: No result returned');
    }
    
    const { AccessToken, RefreshToken, IdToken, ExpiresIn } = response.AuthenticationResult;
    
    if (!AccessToken || !RefreshToken || !IdToken) {
      throw new Error('Authentication failed: Missing tokens');
    }
    
    // Store tokens
    this.storeTokens(AccessToken, RefreshToken, IdToken, ExpiresIn || 3600);
    
    // Get user info
    return this.getCurrentUser();
  }
  
  /**
   * 获取当前访问令牌
   * 
   * 验证: 需求 1.5
   */
  async getAccessToken(): Promise<string> {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
    
    if (!accessToken) {
      throw new Error('No access token available');
    }
    
    // Check if token is expired (with 5 minute buffer)
    if (expiry && Date.now() > parseInt(expiry) - 5 * 60 * 1000) {
      await this.refreshTokens();
      return localStorage.getItem(ACCESS_TOKEN_KEY) || '';
    }
    
    return accessToken;
  }
  
  /**
   * 获取 ID Token（用于 API Gateway Cognito Authorizer）
   * 
   * API Gateway 的 Cognito Authorizer 需要 ID Token，而不是 Access Token
   */
  async getIdToken(): Promise<string> {
    const idToken = localStorage.getItem(ID_TOKEN_KEY);
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
    
    if (!idToken) {
      throw new Error('No ID token available');
    }
    
    // Check if token is expired (with 5 minute buffer)
    if (expiry && Date.now() > parseInt(expiry) - 5 * 60 * 1000) {
      await this.refreshTokens();
      return localStorage.getItem(ID_TOKEN_KEY) || '';
    }
    
    return idToken;
  }
  
  /**
   * 刷新令牌
   */
  async refreshTokens(): Promise<void> {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    
    const command = new InitiateAuthCommand({
      AuthFlow: AuthFlowType.REFRESH_TOKEN_AUTH,
      ClientId: this.config.clientId,
      AuthParameters: {
        REFRESH_TOKEN: refreshToken,
      },
    });
    
    const response = await this.client.send(command);
    
    if (!response.AuthenticationResult) {
      this.clearTokens();
      throw new Error('Token refresh failed');
    }
    
    const { AccessToken, IdToken, ExpiresIn } = response.AuthenticationResult;
    
    if (AccessToken) {
      localStorage.setItem(ACCESS_TOKEN_KEY, AccessToken);
    }
    if (IdToken) {
      localStorage.setItem(ID_TOKEN_KEY, IdToken);
    }
    if (ExpiresIn) {
      localStorage.setItem(TOKEN_EXPIRY_KEY, String(Date.now() + ExpiresIn * 1000));
    }
  }
  
  /**
   * 登出
   * 
   * 验证: 需求 1.4
   */
  async signOut(): Promise<void> {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    
    if (accessToken) {
      try {
        const command = new GlobalSignOutCommand({
          AccessToken: accessToken,
        });
        await this.client.send(command);
      } catch (error) {
        // Ignore errors during sign out
        console.warn('Sign out error:', error);
      }
    }
    
    this.clearTokens();
  }
  
  /**
   * 检查是否已登录
   */
  isAuthenticated(): boolean {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
    
    if (!accessToken) {
      return false;
    }
    
    // Check if token is expired
    if (expiry && Date.now() > parseInt(expiry)) {
      return false;
    }
    
    return true;
  }
  
  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<AuthUser> {
    const accessToken = await this.getAccessToken();
    
    const command = new GetUserCommand({
      AccessToken: accessToken,
    });
    
    const response = await this.client.send(command);
    
    const email = response.UserAttributes?.find(attr => attr.Name === 'email')?.Value || '';
    const sub = response.UserAttributes?.find(attr => attr.Name === 'sub')?.Value || '';
    
    return {
      userId: sub,
      email,
      username: response.Username || '',
    };
  }
  
  /**
   * 存储令牌到本地存储
   */
  private storeTokens(accessToken: string, refreshToken: string, idToken: string, expiresIn: number): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    localStorage.setItem(ID_TOKEN_KEY, idToken);
    localStorage.setItem(TOKEN_EXPIRY_KEY, String(Date.now() + expiresIn * 1000));
  }
  
  /**
   * 清除本地存储的令牌
   */
  private clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(ID_TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
  }
}
