/**
 * Type Definitions for the QA Validation System
 * 
 * Contains interfaces for API requests, responses, and component props.
 */

export interface RetrievedChunk {
  chunkId: string;
  content: string;
  question?: string;
  confidenceScore: number;
  source: string;
  rating?: number;
  feedback?: string;
}

export interface QASession {
  sessionId: string;
  question: string;
  answer: string;
  retrievedChunks: RetrievedChunk[];
  timestamp: string;
  answerRating?: number;
  feedback?: string;
  confidenceThreshold?: number;
}

export interface QARequest {
  question: string;
  confidenceThreshold: number;
}

export interface RatingUpdate {
  chunkId?: string | null;
  rating: number;
  feedback?: string | null;
}

export interface AuthUser {
  userId: string;
  email: string;
  username: string;
}

export interface AppConfig {
  apiUrl: string;
  userPoolId: string;
  userPoolClientId: string;
  region: string;
}
