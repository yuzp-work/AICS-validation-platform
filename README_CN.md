# Bedrock 知识库问答验证系统

基于 Amazon Bedrock 知识库的问答验证系统，支持用户对问答结果进行评分和反馈。

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│    S3 Bucket    │     │  Cognito User   │
│   (CDN 分发)    │     │  (前端静态资源)  │     │     Pool        │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│  React 前端     │────▶│  API Gateway    │◀─────────────┘
│  (TypeScript)   │     │  (REST API)     │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Lambda 函数    │
                        │  (Python 3.11)  │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     ┌────────▼────────┐ ┌──────▼───────┐ ┌───────▼───────┐
     │   DynamoDB      │ │   Bedrock    │ │   Bedrock     │
     │   (会话存储)    │ │ Knowledge    │ │   Model       │
     └─────────────────┘ │    Base      │ └───────────────┘
                         └──────────────┘
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript |
| 后端 | Python 3.11 + Strands Agent SDK |
| 认证 | Amazon Cognito |
| 数据库 | Amazon DynamoDB |
| AI 模型 | Amazon Bedrock (可配置，默认 Claude) |
| 基础设施 | AWS CDK (TypeScript) |
| 托管 | S3 + CloudFront |

## 功能特性

- **智能问答**：基于 Bedrock Knowledge Base 的 RAG 问答，支持召回内容展示和置信度阈值过滤
- **用户认证**：Cognito 用户池认证，JWT 令牌管理，自动令牌刷新
- **评分反馈**：1-5 星评分，召回内容单独评分，文字反馈
- **历史记录**：问答历史查询，会话详情查看
- **日志记录**：DynamoDB 记录完整会话信息（用户邮箱、模型ID、知识库ID、召回内容）

## 前置条件

- Node.js 18+
- Python 3.11+
- Docker（CDK 打包 Lambda Layer 需要）
- AWS CLI（已配置凭证）
- AWS CDK CLI (`npm install -g aws-cdk`)
- 已创建的 Amazon Bedrock 知识库
- 部署账号需要的 IAM 权限（见 [IAM 权限要求](#iam-权限要求)）

## 项目结构

```
├── cdk/                    # CDK 基础设施代码
│   ├── bin/cdk.ts         # CDK 入口
│   ├── lib/               # Stack 定义
│   ├── config.json        # 部署配置（需修改）
│   └── config.example.json # 配置示例
├── lambda/                 # Lambda 后端代码
│   ├── handler.py         # API 处理器
│   ├── agent.py           # Strands Agent 封装
│   ├── db.py              # DynamoDB 数据访问
│   ├── config.py          # 配置管理
│   ├── utils.py           # 工具函数
│   └── tests/             # 测试文件
├── frontend/               # React 前端代码
│   ├── src/
│   │   ├── components/    # UI 组件
│   │   ├── pages/         # 页面组件
│   │   ├── services/      # API 和认证服务
│   │   └── types/         # TypeScript 类型定义
│   └── public/
├── README.md              # 英文文档
└── README_CN.md           # 本文档
```

## 部署指南

### 第一步：获取知识库 ID

1. 登录 AWS 控制台
2. 进入 Amazon Bedrock 服务
3. 选择「知识库」
4. 复制目标知识库的 ID（如 `SWOFQ7S45C`）

> 注意：知识库必须与部署区域在同一 Region（默认 us-west-2）

### 第二步：配置部署参数

编辑 `cdk/config.json`（参考 `cdk/config.example.json`）：

```json
{
  "knowledgeBaseId": "YOUR_KNOWLEDGE_BASE_ID",
  "modelId": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
  "systemPrompt": "你是一个专业的客服助手。请根据提供的知识库内容回答用户的问题。如果知识库中没有相关信息，请诚实地告知用户你无法回答该问题。回答时请保持专业、友好的语气。",
  "awsRegion": "us-west-2",
  "stackName": "",
  "resourcePrefix": ""
}
```

配置说明：

| 字段 | 说明 | 是否必填 |
|------|------|----------|
| `knowledgeBaseId` | Bedrock 知识库 ID | 必填 |
| `modelId` | Bedrock 模型 ID | 选填，默认 `global.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `systemPrompt` | 系统提示词 | 选填 |
| `awsRegion` | 部署区域 | 选填，默认 `us-west-2` |
| `stackName` | CloudFormation Stack 名称 | 选填，留空则自动生成带时间戳的名称 |
| `resourcePrefix` | 资源名称前缀，用于在同一账号/区域下部署多套服务 | 选填，默认为空 |

> 首次部署后，请将 CDK 输出的 Stack 名称填入 `stackName`，后续更新时会复用同一 Stack。

### 第三步：部署基础设施

```bash
# 进入 CDK 目录
cd cdk

# 安装依赖
npm install

# 首次使用 CDK 需要 bootstrap（每个账号/区域只需一次）
npx cdk bootstrap

# 部署
npx cdk deploy --require-approval never
```

> 部署过程中 Lambda Layer 会通过 Docker 打包 Python 依赖，请确保 Docker 正在运行。
> 如果 pip 下载缓慢，CDK 已配置使用清华镜像源。

### 第四步：记录输出值

部署完成后，终端会输出以下信息（请记录）：

```
Outputs:
QAValidationStack.ApiUrl = https://xxxxxx.execute-api.us-west-2.amazonaws.com/prod/
QAValidationStack.UserPoolId = us-west-2_xxxxxxxx
QAValidationStack.UserPoolClientId = xxxxxxxxxxxxxxxxxxxxxxxxxx
QAValidationStack.CloudFrontUrl = https://dxxxxxxxxxx.cloudfront.net
QAValidationStack.DistributionId = E1XXXXXXXXXX
QAValidationStack.WebsiteBucketName = qa-validation-frontend-xxxxxxxxxxxx-us-west-2
```

### 第五步：构建并部署前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 创建 .env 文件（使用 CDK 输出值）
cat > .env << EOF
REACT_APP_API_URL=https://xxxxxx.execute-api.us-west-2.amazonaws.com/prod/
REACT_APP_USER_POOL_ID=us-west-2_xxxxxxxx
REACT_APP_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
REACT_APP_AWS_REGION=us-west-2
EOF

# 构建
npm run build

# 上传到 S3（替换 BUCKET_NAME 为 CDK 输出的 WebsiteBucketName）
aws s3 sync build/ s3://BUCKET_NAME --delete

# 清除 CloudFront 缓存（使用 CDK 输出的 DistributionId）
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/*"
```

> 可通过 `aws cloudfront list-distributions` 查找 Distribution ID。

### 第六步：创建用户

在 AWS 控制台中创建 Cognito 用户：

1. 登录 AWS 控制台，进入 **Amazon Cognito** 服务
2. 在左侧导航栏选择「用户池」，点击 CDK 创建的用户池（名称包含 `qa-validation`）
3. 选择「用户」选项卡，点击「创建用户」按钮
4. 填写用户信息：
   - **邀请消息**：选择「发送电子邮件邀请」（系统会将临时密码发送到用户邮箱）
   - **用户名**：输入登录用户名（如 `testuser`）
   - **电子邮件地址**：输入用户邮箱
   - **临时密码**：选择「生成密码」，系统将自动生成随机临时密码
5. 点击「创建用户」

> 用户会收到包含临时密码的邮件，首次登录时需修改密码。

### 第七步：访问系统

打开 CDK 输出的 `CloudFrontUrl`，使用创建的用户登录即可。

## 多套部署

如需在同一 AWS 账号和区域下部署多套服务，只需为每套服务设置不同的 `resourcePrefix` 和 `stackName`。

示例 — 部署「开发」和「生产」两套环境：

**开发环境** (`cdk/config.json`)：
```json
{
  "knowledgeBaseId": "YOUR_KB_ID",
  "stackName": "QAValidation-Dev",
  "resourcePrefix": "dev"
}
```

**生产环境** (`cdk/config.json`)：
```json
{
  "knowledgeBaseId": "YOUR_KB_ID",
  "stackName": "QAValidation-Prod",
  "resourcePrefix": "prod"
}
```

`resourcePrefix` 会作为前缀添加到所有 AWS 资源名称上：

| 资源 | 无前缀 | 前缀为 `dev` 时 |
|------|--------|-----------------|
| DynamoDB 表 | `qa-validation-sessions` | `dev-qa-validation-sessions` |
| Cognito 用户池 | `qa-validation-users` | `dev-qa-validation-users` |
| Lambda 函数 | `qa-validation-handler` | `dev-qa-validation-handler` |
| Lambda Layer | `qa-validation-dependencies` | `dev-qa-validation-dependencies` |
| S3 桶 | `qa-validation-frontend-{account}-{region}` | `dev-qa-validation-frontend-{account}-{region}` |

> 每套服务拥有独立的数据库、用户池和前端资源，互不影响。IAM 策略中的通配符（`qa-validation-*`）已覆盖带前缀的资源名称。

## 更新部署

修改代码后重新部署：

```bash
# 更新后端（Lambda + 基础设施）
cd cdk
npx cdk deploy --require-approval never

# 更新前端
cd frontend
npm run build
aws s3 sync build/ s3://BUCKET_NAME --delete
aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths "/*"
```

## 本地开发

### 后端开发

```bash
cd lambda
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 运行测试
PYTHONPATH=. pytest tests/ -v
```

### 前端开发

```bash
cd frontend
npm install
npm start
```

## API 接口文档

所有 API 请求需要在 Header 中携带 JWT 令牌：
```
Authorization: Bearer <id_token>
```

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /qa | 提交问题 |
| GET | /qa/history | 获取历史记录 |
| GET | /qa/{sessionId} | 获取会话详情 |
| PUT | /qa/{sessionId}/rating | 更新评分 |

### POST /qa - 提交问题

请求体：
```json
{
  "question": "如何修改昵称？",
  "confidenceThreshold": 0.5
}
```

响应：
```json
{
  "sessionId": "uuid-xxxx",
  "question": "如何修改昵称？",
  "answer": "左上角头像进入个人信息页面...",
  "retrievedChunks": [
    {
      "chunkId": "chunk-1",
      "content": "左上角头像进入个人信息页面，输入昵称后，花费100钻即可改名",
      "confidenceScore": 0.64,
      "source": "s3://bucket/file.csv"
    }
  ],
  "timestamp": "2026-02-09T00:00:00Z",
  "confidenceThreshold": 0.5
}
```

### PUT /qa/{sessionId}/rating - 更新评分

回答评分：
```json
{ "rating": 5, "feedback": "回答很准确" }
```

召回内容评分：
```json
{ "chunkId": "chunk-1", "rating": 4 }
```

## 环境变量参考

### Lambda 环境变量（由 CDK 自动设置）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| KNOWLEDGE_BASE_ID | Bedrock 知识库 ID | 必填 |
| MODEL_ID | Bedrock 模型 ID | anthropic.claude-3-sonnet-20240229-v1:0 |
| SYSTEM_PROMPT | 系统提示词 | 预定义客服助手提示词 |
| DYNAMODB_TABLE_NAME | DynamoDB 表名 | qa-validation-sessions（使用 `resourcePrefix` 时为 `{prefix}-qa-validation-sessions`） |
| AWS_REGION_NAME | AWS 区域 | us-west-2 |

### 前端环境变量（.env 文件）

| 变量名 | 说明 |
|--------|------|
| REACT_APP_API_URL | API Gateway URL（CDK 输出） |
| REACT_APP_USER_POOL_ID | Cognito 用户池 ID（CDK 输出） |
| REACT_APP_USER_POOL_CLIENT_ID | Cognito 客户端 ID（CDK 输出） |
| REACT_APP_AWS_REGION | AWS 区域 |


## IAM 权限要求

部署此系统的 IAM 用户/角色需要以下权限。以下 Policy 已按照最小权限原则，将 Resource 限定到本方案实际创建的资源范围。

> 使用前请将 `{ACCOUNT_ID}` 替换为你的 AWS 账号 ID，`{REGION}` 替换为部署区域（如 `us-west-2`）。

### 所需 AWS 服务权限概览

| 服务 | 用途 | 资源范围 |
|------|------|----------|
| CloudFormation | CDK 部署基础设施 | `QAValidationStack-*` 和 `CDKToolkit` |
| IAM | 创建 Lambda 执行角色 | `QAValidationStack-*` 和 `cdk-*` |
| Lambda | 创建函数和 Layer | `qa-validation-handler`、`qa-validation-dependencies`（使用 `resourcePrefix` 时为 `{prefix}-qa-validation-*`） |
| API Gateway | 创建 REST API | 当前区域所有 API（API Gateway 不支持资源级限定） |
| DynamoDB | 创建会话存储表 | `qa-validation-sessions` |
| Cognito | 创建用户池和客户端 | `qa-validation-users` |
| S3 | 前端托管 + CDK 资产 | `qa-validation-frontend-*`、`cdk-*` |
| CloudFront | CDN 分发 | 所有分发（CloudFront 为全局服务） |
| CloudWatch Logs | Lambda 日志 | `/aws/lambda/qa-validation-handler` |
| SSM | CDK bootstrap 参数 | `/cdk-bootstrap/*` |
| ECR | CDK bootstrap 镜像 | `cdk-*` |
| STS | CDK 获取账号信息 | CDK 执行角色 |

### Policy 1: 部署权限 (`qa-validation-deploy`)

创建 IAM Policy，命名为 `qa-validation-deploy`，替换 `{ACCOUNT_ID}` 和 `{REGION}`：

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

### Policy 2: CDK Bootstrap 权限 (`qa-validation-cdk-bootstrap`)

仅首次 `cdk bootstrap` 时需要，创建 IAM Policy 命名为 `qa-validation-cdk-bootstrap`：

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

> 将两个 Policy 都附加到部署用户/角色。`cdk bootstrap` 完成后可移除 Policy 2。

### 权限说明

| 权限项 | 为什么需要 `*` 或宽泛范围 | 风险等级 |
|--------|--------------------------|----------|
| `cloudformation:GetTemplateSummary` | AWS 要求此操作的 Resource 必须为 `*` | 低（只读） |
| `cloudformation:ListStacks` | AWS 要求此操作的 Resource 必须为 `*` | 低（只读） |
| `apigateway:*` | API Gateway 不支持资源级 ARN 限定，已限定到当前区域 | 中 |
| `cloudfront:*` | CloudFront 为全局服务，ARN 不含区域，已通过 Condition 限定区域 | 中 |
| `ecr:GetAuthorizationToken` | AWS 要求此操作的 Resource 必须为 `*` | 低（只读） |
| `sts:GetCallerIdentity` | AWS 要求此操作的 Resource 必须为 `*` | 低（只读） |
| `cognito-idp:*` | Cognito 用户池 ID 在创建前未知，使用通配符限定到当前区域和账号 | 低 |

> Lambda 运行时所需的 Bedrock 和 DynamoDB 读写权限由 CDK 自动创建的执行角色管理，不在此部署权限中。

## 常见问题

### Q: 部署失败，提示权限不足？
A: 确保部署用户具有上述 IAM 权限。运行 `aws sts get-caller-identity` 确认当前身份。

### Q: Lambda Layer 打包失败？
A: 确保 Docker 正在运行。CDK 使用 Docker 容器打包 Python 依赖。

### Q: 前端无法连接 API？
A: 检查 `.env` 文件中的 `REACT_APP_API_URL` 是否正确，末尾需要有 `/`。

### Q: 知识库查询无结果？
A: 确认知识库 ID 正确，且知识库与 Lambda 在同一 Region。检查知识库中是否已有数据。

### Q: 登录失败？
A: 确认用户已在 Cognito 中创建。首次登录使用临时密码后需要修改密码。

### Q: 如何查看 Lambda 日志？
A: 在 CloudWatch Logs 中查找 `/aws/lambda/qa-validation-handler` 日志组（使用 `resourcePrefix` 时为 `/aws/lambda/{prefix}-qa-validation-handler`）。

## 清理资源

```bash
cd cdk
npx cdk destroy
```

> 注意：S3 桶中的文件和 DynamoDB 表数据会被自动删除（removalPolicy 设置为 DESTROY）。

## 许可证

MIT
