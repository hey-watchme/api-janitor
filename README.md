# Janitor API - 音声データ自動削除サービス

**処理済み音声ファイルを自動削除し、プライバシーを保護するAPI**

WatchMeプロジェクトにおける音声データのライフサイクル管理を担当します。分析が完了した音声ファイルをS3から自動削除し、ユーザーのプライバシーを最大限に保護します。

## 🎯 主な責務

1. **処理済み音声ファイルの削除** - すべての分析が完了したファイルをS3から削除
2. **プライバシー保護** - 音声データを最短時間で削除し、第三者閲覧を防止
3. **定期実行** - 6時間ごとに自動実行（EventBridge連携）

## 📋 削除条件

以下の**すべて**を満たすファイルを削除:

1. `transcriptions_status = 'completed'`（文字起こし完了）
2. `behavior_features_status = 'completed'`（行動分析完了）
3. `emotion_features_status = 'completed'`（感情分析完了）
4. `created_at`が**24時間以上経過**（安全マージン）

※ `failed`ステータスのファイルは削除しない（再処理の可能性を残す）

## 🏗️ アーキテクチャ

```
EventBridge (6時間ごと: 0 */6 * * ? *)
  ↓
Lambda: janitor-trigger
  ↓ (HTTP Request)
API: janitor (FastAPI - EC2/Docker)
  ├─ Supabaseから削除対象を検索
  ├─ S3からファイル削除
  └─ Supabaseレコード削除
```

## 📁 ディレクトリ構成

```
janitor/
├── api/                    # FastAPI本体
│   ├── main.py
│   └── requirements.txt
│
├── lambda/                 # Lambda Trigger（将来実装）
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── build.sh
│   └── deploy.sh
│
├── .github/
│   └── workflows/
│       └── deploy-to-ecr.yml  # CI/CD設定
│
├── Dockerfile.prod         # 本番用Dockerfile
├── docker-compose.prod.yml # Docker Compose設定
├── run-prod.sh             # デプロイスクリプト
├── .env.example            # 環境変数サンプル
├── .gitignore
└── README.md               # このファイル
```

## 🚀 セットアップ

### 1. 環境変数設定

```bash
cp .env.example .env
# .envを編集してAWS・Supabase認証情報を設定
```

**.env の内容:**
```bash
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
S3_BUCKET_NAME=watchme-vault
AWS_REGION=ap-southeast-2
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
```

### 2. ローカル起動（開発）

```bash
cd api

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip3 install -r requirements.txt

# APIサーバー起動
python3 main.py
```

API: http://localhost:8030

### 3. 本番デプロイ（自動）

mainブランチへのプッシュで自動デプロイ:

```bash
git add .
git commit -m "feat: 新機能の追加"
git push origin main
```

**CI/CDプロセス**:
1. GitHub ActionsがECRにDockerイメージをプッシュ
2. GitHub Secretsから環境変数を取得してEC2に`.env`ファイルを作成
3. Docker Composeでコンテナを再起動

### 必要なGitHub Secrets

```
AWS_ACCESS_KEY_ID       # AWS認証
AWS_SECRET_ACCESS_KEY   # AWS認証
EC2_HOST                # デプロイ先EC2
EC2_SSH_PRIVATE_KEY     # SSH接続用
EC2_USER                # SSHユーザー
S3_BUCKET_NAME          # S3バケット名
SUPABASE_URL            # Supabase URL
SUPABASE_KEY            # Supabase APIキー
```

## 📋 API仕様

### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | API情報 |
| GET | `/health` | ヘルスチェック |
| GET | `/stats` | 削除対象ファイルの統計情報 |
| POST | `/cleanup` | 削除処理を実行 |

### GET /health

**レスポンス例:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-19T12:00:00+00:00",
  "s3_configured": true,
  "supabase_configured": true
}
```

### GET /stats

削除対象ファイルの統計情報を取得

**レスポンス例:**
```json
{
  "eligible_for_deletion": 45,
  "cutoff_time": "2025-10-18T12:00:00+00:00",
  "criteria": {
    "transcriptions_status": "completed",
    "behavior_features_status": "completed",
    "emotion_features_status": "completed",
    "age_threshold_hours": 24
  }
}
```

### POST /cleanup

処理済み音声ファイルを削除

**レスポンス例:**
```json
{
  "success": true,
  "deleted_count": 45,
  "failed_count": 0,
  "skipped_count": 2,
  "total_size_bytes": 123456789,
  "deleted_files": [
    "files/device123/2025-10-18/13-00/audio.wav",
    "files/device456/2025-10-18/13-30/audio.wav"
  ],
  "failed_files": [],
  "message": "削除完了: 45件削除, 0件失敗, 2件スキップ"
}
```

## 🚀 環境情報

### 本番環境

- **外部URL**: `https://api.hey-watch.me/janitor/`
- **内部ポート**: `8030`
- **コンテナ名**: `janitor-api`
- **EC2サーバー**: `3.24.16.82`
- **ECRリポジトリ**: `754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-api-janitor`

### テスト環境

- **外部URL**: `https://api.hey-watch.me/janitor/`
- **内部ポート**: `8021`
- **コンテナ名**: `janitor-api-dev`
- **EC2サーバー**: `3.24.16.82`
- **ECRリポジトリ**: `754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-api-janitor`

### API利用方法

#### 外部からのアクセス

```bash
# ヘルスチェック
curl https://api.hey-watch.me/janitor/health

# 統計情報
curl https://api.hey-watch.me/janitor/stats

# 削除実行
curl -X POST https://api.hey-watch.me/janitor/cleanup
```

#### 内部からのアクセス

```bash
# 本番環境（ポート8030）
curl http://localhost:8030/health
curl -X POST http://localhost:8030/cleanup

# テスト環境（ポート8021）
curl http://localhost:8021/health
curl -X POST http://localhost:8021/cleanup
```

### 運用管理コマンド

#### SSH接続

```bash
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
```

#### サービス管理

```bash
# コンテナ確認
docker ps | grep janitor-api

# ログ確認（本番）
docker logs janitor-api --tail 100 -f

# ログ確認（テスト）
docker logs janitor-api-dev --tail 100 -f

# コンテナ再起動（本番）
cd /home/ubuntu/janitor
docker-compose -f docker-compose.prod.yml restart

# コンテナ再起動（テスト）
cd /home/ubuntu/janitor
docker-compose -f docker-compose.dev.yml restart

# コンテナ停止・削除・再起動（本番）
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# コンテナ停止・削除・再起動（テスト）
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

### 重要な設定情報

- **ECRリポジトリ**: `754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-api-janitor`
- **リージョン**: `ap-southeast-2`
- **ポート**: 8030
- **コンテナ名**: `janitor-api`
- **設定ファイル**: `/home/ubuntu/janitor/.env`
- **docker-compose**: `/home/ubuntu/janitor/docker-compose.prod.yml`
- **メモリ制限**: 512MB
- **Nginx設定**: `/janitor/` → `localhost:8030`に転送

## ⏰ 定期実行設定

### EventBridge設定（Lambda経由）

**実行頻度**: 6時間ごと

**Cron式**: `0 */6 * * ? *`（UTC基準）

**JST換算**:
- 00:00 JST（15:00 UTC前日）
- 06:00 JST（21:00 UTC前日）
- 12:00 JST（03:00 UTC）
- 18:00 JST（09:00 UTC）

### Lambda関数（将来実装予定）

Lambda関数 (`watchme-janitor-trigger`) がこのAPIを呼び出す:

```python
import requests

def lambda_handler(event, context):
    response = requests.post("https://api.hey-watch.me/janitor/cleanup")
    result = response.json()
    print(f"Cleanup result: {result}")
    return result
```

## 🔐 プライバシー保護

### ユーザー向け説明文

> **音声データの自動削除について**
>
> 録音された音声データは、AIによる分析が完了した後、自動的に削除されます。
> - **保存期間**: 分析完了後、最長24時間以内
> - **削除頻度**: 6時間ごとに自動削除処理を実行
> - **削除対象**: 文字起こし、行動分析、感情分析がすべて完了したデータ
>
> このため、音声データそのものが第三者に閲覧されることはありません。
> 分析結果（テキスト、グラフデータ）のみがダッシュボードに表示されます。

## 📊 監視とメンテナンス

### ログの確認

```bash
# APIログ
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
docker logs janitor-api --tail 100 -f

# Lambda実行ログ（将来実装時）
aws logs tail /aws/lambda/watchme-janitor-trigger --follow --region ap-southeast-2
```

### ヘルスチェック

```bash
# API正常性確認
curl https://api.hey-watch.me/janitor/health

# 削除対象統計
curl https://api.hey-watch.me/janitor/stats
```

## ❗ トラブルシューティング

### APIが応答しない場合

```bash
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
cd /home/ubuntu/janitor
docker-compose -f docker-compose.prod.yml restart
```

### 削除処理が実行されない場合

1. EventBridgeルールが有効化されているか確認
2. Lambda関数の実行ログを確認
3. APIのヘルスチェックを確認
4. Supabaseの`audio_files`テーブルを確認

### S3削除エラーが発生する場合

1. AWS認証情報が正しいか確認（.envファイル）
2. S3バケット名が正しいか確認
3. IAMロールにS3削除権限があるか確認

## 🧪 テスト

### ローカルテスト

```bash
cd api
source venv/bin/activate

# API起動
python3 main.py

# 別ターミナルでテスト
curl http://localhost:8030/health
curl http://localhost:8030/stats
curl -X POST http://localhost:8030/cleanup
```

## 📝 ライセンス

プロプライエタリ
