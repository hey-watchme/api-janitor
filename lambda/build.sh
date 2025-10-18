#!/bin/bash

# ============================================
# Lambda関数デプロイパッケージのビルド
# ============================================

set -e

echo "📦 Building Lambda deployment package..."

# 作業ディレクトリを作成
rm -rf package
mkdir -p package

# 依存関係をインストール（Lambda実行環境に合わせる）
pip3 install -r requirements.txt -t package/ --platform manylinux2014_aarch64 --only-binary=:all:

# Lambda関数をコピー
cp lambda_function.py package/

# ZIPファイルを作成
cd package
zip -r ../lambda_function.zip .
cd ..

echo "✅ Build completed: lambda_function.zip"
echo "📦 Size: $(du -h lambda_function.zip | cut -f1)"
