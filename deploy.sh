#!/usr/bin/env bash
set -euo pipefail

API_KEY="${1:-mumbai-train-secret}"
REGION="${2:-ap-south-1}"
STACK_NAME="mumbai-train-api"

echo "==> Installing dependencies"

echo "==> Building"
sam build --template-file template.yaml

echo "==> Deploying to $REGION"
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides ApiKeyValue="$API_KEY" \
  --no-confirm-changeset

echo ""
echo "==> API URL:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text
