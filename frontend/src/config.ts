/**
 * Frontend Configuration
 * 
 * Loads configuration from environment variables.
 * These values are injected at build time from CDK outputs.
 */

import { AppConfig } from './types';

export const config: AppConfig = {
  apiUrl: process.env.REACT_APP_API_URL || '',
  userPoolId: process.env.REACT_APP_USER_POOL_ID || '',
  userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || '',
  region: process.env.REACT_APP_AWS_REGION || 'us-west-2',
};

export default config;
