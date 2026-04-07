/**
 * API Service
 * 
 * Handles all API calls to the backend including
 * question submission, rating updates, and history retrieval.
 * 
 * Requirements:
 * - 2.1: WHEN 用户提交问题 THEN QA_System SHALL 接收问题并调用 Bedrock_Agent
 * - 4.2: WHEN 用户点击评分 THEN Frontend SHALL 发送评分到后端 API
 * - 5.2: WHEN 用户点击评分 THEN Frontend SHALL 发送评分到后端 API
 * - 6.2: THE Frontend SHALL 将置信度阈值作为参数传递给后端 API
 */

import { QARequest, QASession } from '../types';

export class QAApiService {
  constructor(
    private apiUrl: string, 
    private getToken: () => Promise<string>
  ) {}
  
  /**
   * 发送带认证的请求
   * 
   * 验证: 需求 1.5 - JWT 令牌用于 API 请求认证
   */
  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const token = await this.getToken();
    
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    };
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.error?.message || error.message || `HTTP ${response.status}`);
    }
    
    return response;
  }
  
  /**
   * 提交问答请求
   * 
   * 验证: 需求 2.1, 6.2
   */
  async submitQuestion(request: QARequest): Promise<QASession> {
    const response = await this.fetchWithAuth(`${this.apiUrl}/qa`, {
      method: 'POST',
      body: JSON.stringify({
        question: request.question,
        confidenceThreshold: request.confidenceThreshold,
      }),
    });
    
    return response.json();
  }
  
  /**
   * 更新召回内容评分
   *
   * 验证: 需求 4.2
   */
  async rateChunk(sessionId: string, chunkId: string, rating: number): Promise<void> {
    await this.fetchWithAuth(`${this.apiUrl}/qa/${sessionId}/rating`, {
      method: 'PUT',
      body: JSON.stringify({
        chunkId,
        rating,
      }),
    });
  }

  /**
   * 保存召回内容的文字反馈
   */
  async saveChunkFeedback(sessionId: string, chunkId: string, feedback: string): Promise<void> {
    await this.fetchWithAuth(`${this.apiUrl}/qa/${sessionId}/chunk-feedback`, {
      method: 'PUT',
      body: JSON.stringify({
        chunkId,
        feedback,
      }),
    });
  }
  
  /**
   * 更新回答评分
   * 
   * 验证: 需求 5.2
   */
  async rateAnswer(sessionId: string, rating: number, feedback?: string): Promise<void> {
    await this.fetchWithAuth(`${this.apiUrl}/qa/${sessionId}/rating`, {
      method: 'PUT',
      body: JSON.stringify({
        rating,
        feedback: feedback || null,
      }),
    });
  }
  
  /**
   * 获取历史会话
   * 
   * 验证: 需求 7.5
   */
  async getHistory(limit: number = 20): Promise<QASession[]> {
    const response = await this.fetchWithAuth(
      `${this.apiUrl}/qa/history?limit=${limit}`
    );
    
    const data = await response.json();
    return data.sessions || [];
  }
  
  /**
   * 获取会话详情
   */
  async getSession(sessionId: string): Promise<QASession> {
    const response = await this.fetchWithAuth(`${this.apiUrl}/qa/${sessionId}`);
    return response.json();
  }
}
