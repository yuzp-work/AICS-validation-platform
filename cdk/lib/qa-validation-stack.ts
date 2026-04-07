/**
 * QA Validation Stack
 * 
 * CDK Stack for the Bedrock Knowledge Base QA Validation System.
 * Creates all necessary AWS resources including:
 * - API Gateway
 * - Lambda Function
 * - Cognito User Pool
 * - DynamoDB Table
 * - S3 + CloudFront for frontend hosting
 * 
 * Requirements:
 * - 9.1: API Gateway + S3/CloudFront hosting
 * - 9.2: Lambda function with Python runtime
 * - 9.3: Cognito User Pool with USER_PASSWORD_AUTH
 * - 9.4: DynamoDB table with PK/SK and GSI
 * - 9.5: CORS configuration
 * - 9.6: Stack outputs for frontend config
 * - 9.7: IAM permissions for Bedrock and DynamoDB
 */

import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import * as path from 'path';

export interface QAValidationStackProps extends cdk.StackProps {
  /**
   * Bedrock Knowledge Base ID
   */
  knowledgeBaseId: string;
  
  /**
   * Bedrock Model ID (optional, defaults to Claude Haiku 4.5)
   */
  modelId?: string;
  
  /**
   * System prompt for the agent (optional)
   */
  systemPrompt?: string;

  /**
   * 资源名称前缀，用于在同一账号/区域下部署多套服务时区分资源
   * 例如 "dev"、"staging"、"prod" 或 "teamA"
   */
  resourcePrefix?: string;
}

export class QAValidationStack extends cdk.Stack {
  public readonly apiUrl: string;
  public readonly userPoolId: string;
  public readonly userPoolClientId: string;
  public readonly cloudFrontUrl: string;
  
  constructor(scope: Construct, id: string, props: QAValidationStackProps) {
    super(scope, id, props);

    const prefix = props.resourcePrefix ? `${props.resourcePrefix}-` : '';
    
    // =========================================================================
    // DynamoDB Table (Requirement 9.4)
    // =========================================================================
    const sessionsTable = new dynamodb.Table(this, 'SessionsTable', {
      tableName: `${prefix}qa-validation-sessions`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev; use RETAIN in prod
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
    });
    
    // GSI for querying by date
    sessionsTable.addGlobalSecondaryIndex({
      indexName: 'GSI1',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });
    
    // =========================================================================
    // Cognito User Pool (Requirement 9.3)
    // =========================================================================
    const userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `${prefix}qa-validation-users`,
      selfSignUpEnabled: false, // Admin creates users
      signInAliases: { username: true, email: true },
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    
    const userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool,
      userPoolClientName: `${prefix}qa-validation-client`,
      authFlows: {
        userPassword: true, // USER_PASSWORD_AUTH
        userSrp: true,
      },
      generateSecret: false,
      accessTokenValidity: cdk.Duration.hours(1),
      idTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
    });
    
    // =========================================================================
    // Lambda Layer for Dependencies (to handle large packages)
    // =========================================================================
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      layerVersionName: `${prefix}qa-validation-dependencies`,
      description: 'Dependencies for QA Validation Lambda',
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      compatibleArchitectures: [lambda.Architecture.X86_64],
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          platform: 'linux/amd64',  // Ensure x86_64 binaries for Lambda
          command: [
            'bash', '-c',
            'pip install -r requirements-lambda.txt -t /asset-output/python --no-cache-dir --platform manylinux2014_x86_64 --only-binary=:all: && find /asset-output -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true',
          ],
        },
      }),
    });
    
    // =========================================================================
    // Lambda Function (Requirement 9.2, 9.7)
    // =========================================================================
    const qaLambda = new lambda.Function(this, 'QALambda', {
      functionName: `${prefix}qa-validation-handler`,
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.X86_64,  // Match Layer architecture
      handler: 'handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda'), {
        exclude: [
          '.venv',
          '.venv/**',
          '__pycache__',
          '__pycache__/**',
          '**/__pycache__',
          '**/__pycache__/**',
          'tests',
          'tests/**',
          '.pytest_cache',
          '.pytest_cache/**',
          '.hypothesis',
          '.hypothesis/**',
          '*.pyc',
          '**/*.pyc',
          'pytest.ini',
          'run_*.py',
          'run_*.sh',
          'requirements.txt',
          'requirements-lambda.txt',
          'node_modules',
          'node_modules/**',
        ],
      }),
      layers: [dependenciesLayer],
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      environment: {
        KNOWLEDGE_BASE_ID: props.knowledgeBaseId,
        MODEL_ID: props.modelId || 'global.anthropic.claude-haiku-4-5-20251001-v1:0',
        SYSTEM_PROMPT: props.systemPrompt || '你是一个专业的客服助手。请根据提供的知识库内容回答用户的问题。如果知识库中没有相关信息，请诚实地告知用户你无法回答该问题。回答时请保持专业、友好的语气。',
        DYNAMODB_TABLE_NAME: sessionsTable.tableName,
        AWS_REGION_NAME: this.region,
      },
    });
    
    // Grant DynamoDB permissions
    sessionsTable.grantReadWriteData(qaLambda);
    
    // Grant Bedrock permissions (Requirement 9.7)
    qaLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
        'bedrock:Retrieve',
        'bedrock:RetrieveAndGenerate',
      ],
      resources: ['*'], // Bedrock doesn't support resource-level permissions well
    }));
    
    // =========================================================================
    // API Gateway (Requirement 9.1, 9.5)
    // =========================================================================
    const api = new apigateway.RestApi(this, 'QAApi', {
      restApiName: `${prefix}QA Validation API`,
      description: 'API for Bedrock Knowledge Base QA Validation System',
      deployOptions: {
        stageName: 'prod',
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
      },
    });
    
    // Cognito Authorizer
    const authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [userPool],
      authorizerName: 'CognitoAuthorizer',
    });
    
    const lambdaIntegration = new apigateway.LambdaIntegration(qaLambda);
    
    // Routes
    const qaResource = api.root.addResource('qa');
    
    // POST /qa - Submit question
    qaResource.addMethod('POST', lambdaIntegration, {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });
    
    // GET /qa/history - Get history
    const historyResource = qaResource.addResource('history');
    historyResource.addMethod('GET', lambdaIntegration, {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });
    
    // GET /qa/{sessionId} - Get single session
    const sessionResource = qaResource.addResource('{sessionId}');
    sessionResource.addMethod('GET', lambdaIntegration, {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });
    
    // PUT /qa/{sessionId}/rating - Update rating
    const ratingResource = sessionResource.addResource('rating');
    ratingResource.addMethod('PUT', lambdaIntegration, {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });

    // PUT /qa/{sessionId}/chunk-feedback - Update chunk feedback
    const chunkFeedbackResource = sessionResource.addResource('chunk-feedback');
    chunkFeedbackResource.addMethod('PUT', lambdaIntegration, {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });

    // =========================================================================
    // S3 + CloudFront for Frontend (Requirement 9.1)
    // =========================================================================
    const websiteBucket = new s3.Bucket(this, 'WebsiteBucket', {
      bucketName: `${prefix}qa-validation-frontend-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    
    // CloudFront Distribution with OAC (Origin Access Control)
    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(websiteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html', // SPA routing
          ttl: cdk.Duration.seconds(0),
        },
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.seconds(0),
        },
      ],
    });
    
    // =========================================================================
    // Outputs (Requirement 9.6)
    // =========================================================================
    this.apiUrl = api.url;
    this.userPoolId = userPool.userPoolId;
    this.userPoolClientId = userPoolClient.userPoolClientId;
    this.cloudFrontUrl = `https://${distribution.distributionDomainName}`;
    
    const exportPrefix = prefix ? prefix.replace(/-$/, '') : 'QAValidation';

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.apiUrl,
      description: 'API Gateway URL',
      exportName: `${exportPrefix}-ApiUrl`,
    });
    
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `${exportPrefix}-UserPoolId`,
    });
    
    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClientId,
      description: 'Cognito User Pool Client ID',
      exportName: `${exportPrefix}-UserPoolClientId`,
    });
    
    new cdk.CfnOutput(this, 'CloudFrontUrl', {
      value: this.cloudFrontUrl,
      description: 'CloudFront Distribution URL',
      exportName: `${exportPrefix}-CloudFrontUrl`,
    });

    new cdk.CfnOutput(this, 'DistributionId', {
      value: distribution.distributionId,
      description: 'CloudFront Distribution ID',
      exportName: `${exportPrefix}-DistributionId`,
    });
    
    new cdk.CfnOutput(this, 'WebsiteBucketName', {
      value: websiteBucket.bucketName,
      description: 'S3 Bucket for frontend assets',
      exportName: `${exportPrefix}-WebsiteBucket`,
    });
  }
}
