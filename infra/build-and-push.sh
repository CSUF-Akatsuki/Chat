#!/usr/bin/env bash
# Build the Lambda container image and push to ECR.
# Run after `terraform apply` (which creates the ECR repo) and any time backend
# code or requirements change. The pushed tag is fed to Terraform via
# -var lambda_image_tag=... on the next apply, which triggers Lambda to roll.
#
# Usage:
#   ./build-and-push.sh           # tags with git short SHA + 'latest'
#   ./build-and-push.sh v1.2.3    # tags with v1.2.3 + 'latest'

set -euo pipefail

REGION="${AWS_REGION:-us-west-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REPO="room67chat-lambdas"
ECR_HOST="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE="${ECR_HOST}/${REPO}"

TAG="${1:-$(git rev-parse --short HEAD)}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}/backend"

echo "Logging in to ECR ${ECR_HOST}..."
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR_HOST}"

echo "Building image (linux/arm64)..."
docker buildx build \
  --platform linux/arm64 \
  -f Dockerfile.lambda \
  -t "${IMAGE}:${TAG}" \
  -t "${IMAGE}:latest" \
  --push \
  .

echo
echo "Pushed:"
echo "  ${IMAGE}:${TAG}"
echo "  ${IMAGE}:latest"
echo
echo "To roll the Lambdas to this image, run:"
echo "  cd infra && terraform apply -var lambda_image_tag=${TAG}"
