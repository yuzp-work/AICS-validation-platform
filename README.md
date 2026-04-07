# Bedrock Knowledge Base QA Validation System

A full-stack application for validating Q&A responses from Amazon Bedrock Knowledge Base, with user rating and feedback capabilities.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│    S3 Bucket    │     │  Cognito User   │
│   (CDN)         │     │  (Frontend)     │     │     Pool        │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│  React Frontend │────▶│  API Gateway    │◀─────────────┘
│  (TypeScript)   │     │  (REST API)     │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Lambda         │
                        │  (Python 3.11)  │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     ┌────────▼────────┐ ┌──────▼───────┐ ┌───────▼───────┐
     │   DynamoDB      │ │   Bedrock    │ │   Bedrock     │
     │   (Sessions)    │ │ Knowledge    │ │   Model       │
     └─────────────────┘ │    Base      │ └───────────────┘
                         └──────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 19 + TypeScript |
| Backend | Python 3.11 + Strands Agent SDK |
| Auth | Amazon Cognito |
| Database | Amazon DynamoDB |
| AI | Amazon Bedrock (configurable model) |
| Infrastructure | AWS CDK (TypeScript) |
| Hosting | S3 + CloudFront |

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker (required for CDK Lambda Layer bundling)
- AWS CLI (configured with credentials)
- AWS CDK CLI (`npm install -g aws-cdk`)
- An existing Amazon Bedrock Knowledge Base
- IAM permissions for deployment (see [IAM Permissions](#iam-permissions))

## Project Structure

```
├── cdk/                    # CDK infrastructure code
│   ├── bin/cdk.ts         # CDK entry point
│   ├── lib/               # Stack definitions
│   ├── config.json        # Deployment config (edit this)
│   └── config.example.json
├── lambda/                 # Lambda backend
│   ├── handler.py         # API handler
│   ├── agent.py           # Strands Agent wrapper
│   ├── db.py              # DynamoDB access
│   ├── config.py          # Configuration
│   ├── utils.py           # Utilities
│   └── tests/
├── frontend/               # React frontend
│   ├── src/
│   └── public/
├── README.md              # This file
└── README_CN.md           # Chinese documentation
```

## Deployment

### Step 1: Get Knowledge Base ID

1. Open the AWS Console
2. Navigate to Amazon Bedrock
3. Go to "Knowledge bases"
4. Copy the Knowledge Base ID (e.g., `SWOFQ7S45C`)

> The Knowledge Base must be in the same region as the deployment (default: us-west-2).

### Step 2: Configure

Edit `cdk/config.json` (see `cdk/config.example.json` for reference):

```json
{
  "knowledgeBaseId": "YOUR_KNOWLEDGE_BASE_ID",
  "modelId": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
  "systemPrompt": "You are a professional assistant...",
  "awsRegion": "us-west-2",
  "stackName": "",
  "resourcePrefix": ""
}
```

| Field | Description | Required |
|-------|-------------|----------|
| `knowledgeBaseId` | Bedrock Knowledge Base ID | Yes |
| `modelId` | Bedrock model ID | No, defaults to Claude 3 Sonnet |
| `systemPrompt` | System prompt for the agent | No |
| `awsRegion` | Deployment region | No, defaults to `us-west-2` |
| `stackName` | CloudFormation stack name | No, auto-generated with timestamp |
| `resourcePrefix` | Prefix for all resource names, used to deploy multiple instances in the same account/region | No, empty by default |

> After first deployment, save the stack name to `stackName` so subsequent deploys update the same stack.

### Step 3: Deploy Infrastructure

```bash
cd cdk
npm install

# First time only: bootstrap CDK
npx cdk bootstrap

# Deploy
npx cdk deploy --require-approval never
```

> Docker must be running — CDK uses it to bundle Python dependencies for the Lambda Layer.

### Step 4: Note the Outputs

After deployment, note these values from the terminal output:

```
Outputs:
  ApiUrl = https://xxxxxx.execute-api.us-west-2.amazonaws.com/prod/
  UserPoolId = us-west-2_xxxxxxxx
  UserPoolClientId = xxxxxxxxxxxxxxxxxxxxxxxxxx
  CloudFrontUrl = https://dxxxxxxxxxx.cloudfront.net
  DistributionId = E1XXXXXXXXXX
  WebsiteBucketName = qa-validation-frontend-xxxxxxxxxxxx-us-west-2
```

### Step 5: Build and Deploy Frontend

```bash
cd frontend
npm install

# Create .env file with CDK output values
cat > .env << EOF
REACT_APP_API_URL=https://xxxxxx.execute-api.us-west-2.amazonaws.com/prod/
REACT_APP_USER_POOL_ID=us-west-2_xxxxxxxx
REACT_APP_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
REACT_APP_AWS_REGION=us-west-2
EOF

# Build
npm run build

# Upload to S3 (replace BUCKET_NAME with WebsiteBucketName from output)
aws s3 sync build/ s3://BUCKET_NAME --delete

# Invalidate CloudFront cache (use DistributionId from CDK output)
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/*"
```

### Step 6: Create Users

Create a Cognito user via the AWS Console:

1. Open the AWS Console and navigate to **Amazon Cognito**
2. Select "User pools" in the left navigation, then click the user pool created by CDK (name contains `qa-validation`)
3. Go to the "Users" tab and click "Create user"
4. Fill in the user details:
   - **Invitation message**: Select "Send an email invitation" (the temporary password will be sent to the user's email)
   - **User name**: Enter a login username (e.g., `testuser`)
   - **Email address**: Enter the user's email
   - **Temporary password**: Select "Generate a password" to let the system create a random temporary password
5. Click "Create user"

> The user will receive an email with the temporary password and must change it on first login.

### Step 7: Access

Open the `CloudFrontUrl` from the CDK output and log in.

## Multi-Instance Deployment

To deploy multiple instances of this system in the same AWS account and region, set a unique `resourcePrefix` and `stackName` for each instance in `cdk/config.json`.

Example — deploying a "dev" and a "prod" instance:

**dev** (`cdk/config.json`):
```json
{
  "knowledgeBaseId": "YOUR_KB_ID",
  "stackName": "QAValidation-Dev",
  "resourcePrefix": "dev"
}
```

**prod** (`cdk/config.json`):
```json
{
  "knowledgeBaseId": "YOUR_KB_ID",
  "stackName": "QAValidation-Prod",
  "resourcePrefix": "prod"
}
```

The `resourcePrefix` is prepended to all AWS resource names:

| Resource | Without prefix | With prefix `dev` |
|----------|---------------|-------------------|
| DynamoDB Table | `qa-validation-sessions` | `dev-qa-validation-sessions` |
| Cognito User Pool | `qa-validation-users` | `dev-qa-validation-users` |
| Lambda Function | `qa-validation-handler` | `dev-qa-validation-handler` |
| Lambda Layer | `qa-validation-dependencies` | `dev-qa-validation-dependencies` |
| S3 Bucket | `qa-validation-frontend-{account}-{region}` | `dev-qa-validation-frontend-{account}-{region}` |

> Each instance has its own independent set of resources (database, users, frontend). The IAM policy wildcards (`qa-validation-*`) already cover prefixed resource names.

## Updating

```bash
# Backend update
cd cdk && npx cdk deploy --require-approval never

# Frontend update
cd frontend && npm run build
aws s3 sync build/ s3://BUCKET_NAME --delete
aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths "/*"
```

## Local Development

### Backend

```bash
cd lambda
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm start
```

## API Endpoints

All requests require `Authorization: Bearer <id_token>` header.

| Method | Path | Description |
|--------|------|-------------|
| POST | /qa | Submit a question |
| GET | /qa/history | Get QA history |
| GET | /qa/{sessionId} | Get session details |
| PUT | /qa/{sessionId}/rating | Update rating |


## IAM Permissions

The deploying IAM user/role needs the following permissions. This policy follows the principle of least privilege, scoping resources to only what this solution creates.

> Replace `{ACCOUNT_ID}` with your AWS account ID and `{REGION}` with the deployment region (e.g., `us-west-2`) before use.

### Required Services

| Service | Purpose | Resource Scope |
|---------|---------|----------------|
| CloudFormation | CDK deployment | `QAValidationStack-*` and `CDKToolkit` |
| IAM | Lambda execution roles | `QAValidationStack-*` and `cdk-*` |
| Lambda | Function and Layer | `qa-validation-handler`, `qa-validation-dependencies` (or `{prefix}-qa-validation-*` if using `resourcePrefix`) |
| API Gateway | REST API | Current region (no resource-level ARN support) |
| DynamoDB | Session storage | `qa-validation-sessions` |
| Cognito | User pool and client | `qa-validation-users` |
| S3 | Frontend hosting + CDK assets | `qa-validation-frontend-*`, `cdk-*` |
| CloudFront | CDN distribution | Global service, region-conditioned |
| CloudWatch Logs | Lambda logging | `/aws/lambda/qa-validation-handler` |
| SSM | CDK bootstrap params | `/cdk-bootstrap/*` |
| ECR | CDK bootstrap images | `cdk-*` |
| STS | CDK identity | CDK execution roles |

### Policy 1: Deployment Policy (`qa-validation-deploy`)

Create an IAM Policy named `qa-validation-deploy`. Replace `{ACCOUNT_ID}` and `{REGION}` before use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CFN",
      "Effect": "Allow",
      "Action": ["cloudformation:Create*","cloudformation:Update*","cloudformation:Delete*","cloudformation:Describe*","cloudformation:Get*","cloudformation:Execute*","cloudformation:List*"],
      "Resource": ["arn:aws:cloudformation:{REGION}:{ACCOUNT_ID}:stack/QAValidationStack-*/*","arn:aws:cloudformation:{REGION}:{ACCOUNT_ID}:stack/CDKToolkit/*"]
    },
    {
      "Sid": "CFNRead",
      "Effect": "Allow",
      "Action": ["cloudformation:GetTemplateSummary","cloudformation:ListStacks"],
      "Resource": "*"
    },
    {
      "Sid": "IAMRole",
      "Effect": "Allow",
      "Action": ["iam:CreateRole","iam:DeleteRole","iam:GetRole","iam:PassRole","iam:AttachRolePolicy","iam:DetachRolePolicy","iam:PutRolePolicy","iam:DeleteRolePolicy","iam:GetRolePolicy","iam:TagRole","iam:UntagRole"],
      "Resource": ["arn:aws:iam::{ACCOUNT_ID}:role/QAValidationStack-*","arn:aws:iam::{ACCOUNT_ID}:role/cdk-*"]
    },
    {
      "Sid": "IAMPolicy",
      "Effect": "Allow",
      "Action": ["iam:CreatePolicy","iam:DeletePolicy","iam:GetPolicy","iam:GetPolicyVersion","iam:ListPolicyVersions","iam:CreatePolicyVersion","iam:DeletePolicyVersion"],
      "Resource": "arn:aws:iam::{ACCOUNT_ID}:policy/QAValidationStack-*"
    },
    {
      "Sid": "Lambda",
      "Effect": "Allow",
      "Action": ["lambda:*Function*","lambda:AddPermission","lambda:RemovePermission","lambda:InvokeFunction","lambda:TagResource","lambda:UntagResource","lambda:ListTags"],
      "Resource": "arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:qa-validation-*"
    },
    {
      "Sid": "LambdaLayer",
      "Effect": "Allow",
      "Action": ["lambda:PublishLayerVersion","lambda:DeleteLayerVersion","lambda:GetLayerVersion","lambda:ListLayerVersions"],
      "Resource": "arn:aws:lambda:{REGION}:{ACCOUNT_ID}:layer:qa-validation-*"
    },
    {
      "Sid": "APIGW",
      "Effect": "Allow",
      "Action": ["apigateway:GET","apigateway:POST","apigateway:PUT","apigateway:PATCH","apigateway:DELETE"],
      "Resource": "arn:aws:apigateway:{REGION}::/*"
    },
    {
      "Sid": "DDB",
      "Effect": "Allow",
      "Action": ["dynamodb:CreateTable","dynamodb:DeleteTable","dynamodb:Describe*","dynamodb:UpdateTable","dynamodb:UpdateContinuousBackups","dynamodb:TagResource","dynamodb:UntagResource","dynamodb:ListTagsOfResource"],
      "Resource": "arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/qa-validation-*"
    },
    {
      "Sid": "Cognito",
      "Effect": "Allow",
      "Action": ["cognito-idp:*UserPool*","cognito-idp:Admin*","cognito-idp:SetUserPoolMfaConfig"],
      "Resource": "arn:aws:cognito-idp:{REGION}:{ACCOUNT_ID}:userpool/*"
    },
    {
      "Sid": "S3Frontend",
      "Effect": "Allow",
      "Action": ["s3:CreateBucket","s3:DeleteBucket","s3:Get*","s3:Put*","s3:List*","s3:DeleteObject","s3:DeleteObjectVersion","s3:DeleteBucketPolicy"],
      "Resource": ["arn:aws:s3:::qa-validation-frontend-*","arn:aws:s3:::qa-validation-frontend-*/*"]
    },
    {
      "Sid": "CloudFront",
      "Effect": "Allow",
      "Action": ["cloudfront:*Distribution*","cloudfront:*OriginAccessControl*","cloudfront:CreateInvalidation","cloudfront:TagResource","cloudfront:UntagResource","cloudfront:ListDistributions","cloudfront:ListOriginAccessControls"],
      "Resource": "*",
      "Condition": {"StringEquals":{"aws:RequestedRegion":"{REGION}"}}
    },
    {
      "Sid": "Logs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup","logs:DeleteLogGroup","logs:DescribeLogGroups","logs:PutRetentionPolicy","logs:TagResource"],
      "Resource": "arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:/aws/lambda/qa-validation-*"
    },
    {
      "Sid": "STS",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity","sts:AssumeRole"],
      "Resource": ["*","arn:aws:iam::{ACCOUNT_ID}:role/cdk-*"]
    }
  ]
}
```

### Policy 2: CDK Bootstrap Policy (`qa-validation-cdk-bootstrap`)

Only needed for the first `cdk bootstrap`. Create an IAM Policy named `qa-validation-cdk-bootstrap`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3CDK",
      "Effect": "Allow",
      "Action": ["s3:CreateBucket","s3:Get*","s3:Put*","s3:List*"],
      "Resource": ["arn:aws:s3:::cdk-*-assets-{ACCOUNT_ID}-{REGION}","arn:aws:s3:::cdk-*-assets-{ACCOUNT_ID}-{REGION}/*"]
    },
    {
      "Sid": "SSM",
      "Effect": "Allow",
      "Action": ["ssm:GetParameter","ssm:PutParameter","ssm:DeleteParameter"],
      "Resource": "arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter/cdk-bootstrap/*"
    },
    {
      "Sid": "ECR",
      "Effect": "Allow",
      "Action": ["ecr:CreateRepository","ecr:DeleteRepository","ecr:Describe*","ecr:*RepositoryPolicy","ecr:PutImage","ecr:GetDownloadUrlForLayer","ecr:Batch*","ecr:InitiateLayerUpload","ecr:UploadLayerPart","ecr:CompleteLayerUpload"],
      "Resource": "arn:aws:ecr:{REGION}:{ACCOUNT_ID}:repository/cdk-*"
    },
    {
      "Sid": "ECRAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    }
  ]
}
```

> Attach both policies to the deploying user/role. Policy 2 can be removed after `cdk bootstrap` completes.

### Why Some Resources Use `*`

| Permission | Why `*` is needed | Risk |
|------------|-------------------|------|
| `cloudformation:GetTemplateSummary` | AWS requires `*` for this action | Low (read-only) |
| `cloudformation:ListStacks` | AWS requires `*` for this action | Low (read-only) |
| `apigateway:*` | API Gateway doesn't support resource-level ARNs, scoped to region | Medium |
| `cloudfront:*` | Global service, no region in ARN, region-conditioned | Medium |
| `ecr:GetAuthorizationToken` | AWS requires `*` for this action | Low (read-only) |
| `sts:GetCallerIdentity` | AWS requires `*` for this action | Low (read-only) |
| `cognito-idp:*` | User Pool ID unknown before creation, scoped to account/region | Low |

> Bedrock and DynamoDB runtime permissions for the Lambda function are automatically managed by CDK-created execution roles and are not part of this deployment policy.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment fails with permission error | Verify IAM permissions. Run `aws sts get-caller-identity` to check identity. |
| Lambda Layer bundling fails | Ensure Docker is running. CDK uses Docker to package Python dependencies. |
| Frontend can't connect to API | Check `.env` values match CDK outputs. `REACT_APP_API_URL` needs trailing `/`. |
| Knowledge Base returns no results | Verify KB ID is correct and KB is in the same region as Lambda. |
| Login fails | Ensure user is created in Cognito. First login with temp password requires password change. |
| View Lambda logs | Check CloudWatch Logs group `/aws/lambda/qa-validation-handler` (or `/aws/lambda/{prefix}-qa-validation-handler` if using `resourcePrefix`). |

## Cleanup

```bash
cd cdk
npx cdk destroy
```

> S3 objects and DynamoDB data will be automatically deleted (removalPolicy is set to DESTROY).

## License

MIT
