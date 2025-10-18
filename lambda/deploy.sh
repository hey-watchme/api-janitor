#!/bin/bash

# ============================================
# Lambda関数のデプロイスクリプト
# ============================================

set -e

FUNCTION_NAME="watchme-janitor-trigger"
REGION="ap-southeast-2"

echo "🚀 Deploying Lambda function: ${FUNCTION_NAME}"

# ビルド
./build.sh

# Lambda関数を更新
aws lambda update-function-code \
  --function-name ${FUNCTION_NAME} \
  --zip-file fileb://lambda_function.zip \
  --region ${REGION}

echo "✅ Deployment completed!"
echo "🔍 Function: ${FUNCTION_NAME}"
echo "📍 Region: ${REGION}"
