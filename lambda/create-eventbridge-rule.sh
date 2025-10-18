#!/bin/bash

# ============================================
# EventBridgeルールの作成
# ============================================

set -e

FUNCTION_NAME="watchme-janitor-trigger"
RULE_NAME="watchme-janitor-schedule"
REGION="ap-southeast-2"

echo "⏰ Creating EventBridge rule: ${RULE_NAME}"

# EventBridgeルールを作成（6時間ごと）
aws events put-rule \
  --name ${RULE_NAME} \
  --schedule-expression "cron(0 */6 * * ? *)" \
  --state ENABLED \
  --description "Janitor APIを6時間ごとに実行して音声データを削除" \
  --region ${REGION}

# Lambda関数にEventBridgeからの実行権限を付与
aws lambda add-permission \
  --function-name ${FUNCTION_NAME} \
  --statement-id ${RULE_NAME} \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:${REGION}:754724220380:rule/${RULE_NAME} \
  --region ${REGION} || true

# EventBridgeターゲットを設定
LAMBDA_ARN=$(aws lambda get-function --function-name ${FUNCTION_NAME} --region ${REGION} --query 'Configuration.FunctionArn' --output text)

aws events put-targets \
  --rule ${RULE_NAME} \
  --targets "Id"="1","Arn"="${LAMBDA_ARN}" \
  --region ${REGION}

echo "✅ EventBridge rule created successfully!"
echo "📋 Rule: ${RULE_NAME}"
echo "⏰ Schedule: 6時間ごと (0 */6 * * ? *)"
echo "🎯 Target: ${FUNCTION_NAME}"
