# CPSC465Chat — Terraform (Lambdas + Cognito)

Provisions the new Lambda + API Gateway + Cognito stack for CPSC465Chat. Existing infra (VPC, subnets, RDS, ElastiCache, NAT, ECS, ALB, CloudFront, S3, Secrets Manager) is **referenced via data sources** and not managed here — Option A from the architecture decision.

## What this creates

- ECR repository (`room67chat-lambdas`) for the Lambda container image
- Cognito User Pool + App Client (with secret, for pycognito server-side flows)
- IAM execution role for Lambdas (basic + VPC + Secrets Manager + Cognito read)
- Security group for Lambdas + ingress rules into existing RDS / Redis SGs
- 12 Lambda functions (auth × 5, friends × 8, messages × 3) sharing one container image, each with a different handler `CMD`
- API Gateway HTTP API v2 with Cognito JWT authorizer + routes for each Lambda
- CloudWatch log groups (14-day retention) for each Lambda and API Gateway

## What it references but does not manage

- VPC `Room67Chat-vpc`
- Subnets `Room67Chat-subnet-private-app-{a,b}` (where Lambdas run)
- Security groups `Room67Chat-sg-rds`, `Room67Chat-sg-redis` (ingress rules added)
- Secrets `room67chat/db`, `room67chat/redis`, `room67chat/jwt`

## One-time setup

### 1. Bootstrap the remote state backend

```bash
./bootstrap.sh
```

Creates `room67chat-tfstate-<account-id>` S3 bucket (versioned + encrypted) and `room67chat-tfstate-locks` DynamoDB table. Idempotent.

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Build and push the Lambda image

You need a placeholder image in ECR before the first `terraform apply`, otherwise the Lambda functions will fail to create. The repo must exist first — but since `aws_lambda_function` references `image_uri`, we have a chicken-and-egg.

The clean workflow:

```bash
# Apply just the ECR repo first
terraform apply -target=aws_ecr_repository.lambdas

# Build and push the image
./build-and-push.sh

# Apply everything else
terraform apply
```

## Day-to-day workflow

When backend code changes:

```bash
./build-and-push.sh                          # builds + pushes :latest and :<git-sha>
terraform apply -var lambda_image_tag=<sha>  # rolls the Lambdas
```

When Terraform code changes:

```bash
terraform plan
terraform apply
```

## Frontend integration

After `terraform apply`, capture outputs:

```bash
terraform output api_url               # base URL for HTTP API calls
terraform output cognito_user_pool_id  # for Amplify / Cognito SDK config
terraform output cognito_client_id     # for Amplify / Cognito SDK config
```

Set these as Vite env vars (`client/.env.production`) and rebuild the frontend.

## WebSocket server (ECS) integration

The ECS task running `backend/websocket_server.py` needs:

- `AWS_COGNITO_USER_POOL_ID` — from `terraform output cognito_user_pool_id`
- `AWS_COGNITO_CLIENT_ID` — from `terraform output cognito_client_id`
- `AWS_AZ` — `us-west-1` (the lambda code uses this as region)
- `LOCAL_AUTH_MODE` — `false` in production; `true` for offline dev (falls back to legacy SECRET_KEY)

Update the ECS task definition env vars manually (not in this Terraform — ECS is in the unmanaged set).

## Decisions

- **Greenfield Terraform** — does not import existing infra. See `MEMORY.md` for the rationale.
- **Container images** — Lambdas use container images instead of zip because `asyncpg`, `psycopg2-binary`, and `pwdlib[argon2]` have native compiled deps that don't cross-compile cleanly from Mac to Lambda Linux.
- **arm64** — cheaper than x86_64 and builds natively on Apple Silicon.
- **One image, multiple functions** — simpler than per-function images; Terraform overrides `CMD` per function to point at the right handler.
- **App client has a secret** — pycognito uses USER_PASSWORD_AUTH which requires the client secret. Frontend will need a separate public client (no secret) for browser-based Cognito SDK calls when the frontend Cognito migration happens.
