#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import * as fs from 'fs';
import * as path from 'path';
import { QAValidationStack } from '../lib/qa-validation-stack';

const app = new cdk.App();

// Load configuration from config.json
const configPath = path.join(__dirname, '../config.json');
let fileConfig: Record<string, string> = {};
if (fs.existsSync(configPath)) {
  try {
    fileConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    console.log('📄 Loaded configuration from config.json');
  } catch (e) {
    console.warn('⚠️  Failed to parse config.json, using defaults');
  }
}

// Get configuration: CLI context overrides config.json
const knowledgeBaseId = app.node.tryGetContext('knowledgeBaseId') || fileConfig.knowledgeBaseId || 'YOUR_KNOWLEDGE_BASE_ID';
const modelId = app.node.tryGetContext('modelId') || fileConfig.modelId || 'global.anthropic.claude-haiku-4-5-20251001-v1:0';
const systemPrompt = app.node.tryGetContext('systemPrompt') || fileConfig.systemPrompt || '你是一个专业的客服助手。请根据提供的知识库内容回答用户的问题。';
const awsRegion = app.node.tryGetContext('awsRegion') || fileConfig.awsRegion || 'us-west-2';
const resourcePrefix = app.node.tryGetContext('resourcePrefix') || fileConfig.resourcePrefix || '';

// Validate knowledgeBaseId
if (knowledgeBaseId === 'YOUR_KNOWLEDGE_BASE_ID') {
  console.warn('\n⚠️  WARNING: knowledgeBaseId is not configured!');
  console.warn('   Please edit cdk/config.json and set your Knowledge Base ID\n');
}

// Stack name: CLI context > config.json > generate with timestamp
const providedStackName = app.node.tryGetContext('stackName') || fileConfig.stackName;
let stackName: string;
if (providedStackName) {
  stackName = providedStackName;
} else {
  const now = new Date();
  const timestamp = now.toISOString().slice(0, 10).replace(/-/g, '') + '-' + now.toISOString().slice(11, 16).replace(':', '');
  stackName = `QAValidationStack-${timestamp}`;
  console.log(`\n📦 Creating new stack: ${stackName}`);
  console.log(`   To update this stack later, use: --context stackName=${stackName}`);
  console.log(`   Or add "stackName": "${stackName}" to config.json\n`);
}

console.log(`🚀 Deploying with configuration:`);
console.log(`   Stack Name: ${stackName}`);
console.log(`   Resource Prefix: ${resourcePrefix || '(none)'}`);
console.log(`   Knowledge Base ID: ${knowledgeBaseId}`);
console.log(`   Model ID: ${modelId}`);
console.log(`   Region: ${awsRegion}\n`);

new QAValidationStack(app, stackName, {
  knowledgeBaseId,
  modelId,
  systemPrompt,
  resourcePrefix: resourcePrefix || undefined,
  env: { region: awsRegion },
});