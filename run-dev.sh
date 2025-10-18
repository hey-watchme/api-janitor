#!/bin/bash

# ===========================================
# Janitor API - テスト環境起動スクリプト
# ===========================================

set -e

echo "🚀 Starting Janitor API deployment (DEV)..."

# ECRログイン
echo "🔐 Logging in to Amazon ECR..."
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin 754724220380.dkr.ecr.ap-southeast-2.amazonaws.com

# 最新イメージをプル
echo "📥 Pulling latest image from ECR..."
docker pull 754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-api-janitor:latest

# 古いコンテナを停止・削除
echo "🗑️ Stopping old containers..."
docker-compose -f docker-compose.dev.yml down || true

# 新しいコンテナを起動
echo "▶️ Starting new containers..."
docker-compose -f docker-compose.dev.yml up -d

# ログ確認
echo "📋 Checking container logs..."
sleep 3
docker logs janitor-api-dev --tail 50

echo "✅ Deployment completed (DEV)!"
echo "🌐 API URL: https://api.hey-watch.me/janitor/ (外部)"
echo "🏠 Local: http://localhost:8021/health"
echo "📊 Stats: curl http://localhost:8021/stats"
echo "🧹 Cleanup: curl -X POST http://localhost:8021/cleanup"
