#!/usr/bin/env bash
# One-time bootstrap for the Terraform S3 remote-state backend.
# Run this BEFORE `terraform init`. Idempotent — safe to re-run.

set -euo pipefail

REGION="us-west-1"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="room67chat-tfstate-${ACCOUNT_ID}"
TABLE="room67chat-tfstate-locks"

echo "Region:    ${REGION}"
echo "Account:   ${ACCOUNT_ID}"
echo "Bucket:    ${BUCKET}"
echo "Lock tbl:  ${TABLE}"
echo

if aws s3api head-bucket --bucket "${BUCKET}" --region "${REGION}" 2>/dev/null; then
  echo "S3 bucket ${BUCKET} already exists — skipping create."
else
  echo "Creating S3 bucket ${BUCKET}..."
  aws s3api create-bucket \
    --bucket "${BUCKET}" \
    --region "${REGION}" \
    --create-bucket-configuration "LocationConstraint=${REGION}"

  aws s3api put-bucket-versioning \
    --bucket "${BUCKET}" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "${BUCKET}" \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
      }]
    }'

  aws s3api put-public-access-block \
    --bucket "${BUCKET}" \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
fi

if aws dynamodb describe-table --table-name "${TABLE}" --region "${REGION}" >/dev/null 2>&1; then
  echo "DynamoDB table ${TABLE} already exists — skipping create."
else
  echo "Creating DynamoDB lock table ${TABLE}..."
  aws dynamodb create-table \
    --table-name "${TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${REGION}" >/dev/null

  aws dynamodb wait table-exists --table-name "${TABLE}" --region "${REGION}"
fi

echo
echo "Done. You can now run:"
echo "  cd infra && terraform init"
