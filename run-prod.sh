#!/bin/bash

# ===========================================
# Janitor API - 本番環境起動スクリプト
# ===========================================

set -e

echo "🚀 Starting Janitor API deployment..."

# ECRログイン
echo "🔐 Logging in to Amazon ECR..."
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin 754724220380.dkr.ecr.ap-southeast-2.amazonaws.com

# 最新イメージをプル
echo "📥 Pulling latest image from ECR..."
docker pull 754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-api-janitor:latest

# 古いコンテナを停止・削除
echo "🗑️ Stopping old containers..."
docker-compose -f docker-compose.prod.yml down || true

# 新しいコンテナを起動
echo "▶️ Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# ログ確認
echo "📋 Checking container logs..."
sleep 3
docker logs janitor-api --tail 50

echo "✅ Deployment completed!"
echo "🌐 API URL: https://api.hey-watch.me/janitor/"
echo "🏥 Health check: curl http://localhost:8030/health"
