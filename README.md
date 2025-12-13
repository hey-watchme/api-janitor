# Janitor API - 音声データ自動削除サービス

**処理済み音声ファイルを自動削除し、プライバシーを保護するAPI**

WatchMeプロジェクトにおける音声データのライフサイクル管理を担当します。分析が完了した音声ファイルをS3から自動削除し、ユーザーのプライバシーを最大限に保護します。

---

## ✅ 実装状況（最終更新: 2025-10-19）

### 🎉 すべて完了 - 本番稼働中

- [x] FastAPI実装（S3削除ロジック、Supabase連携）
- [x] Docker & Docker Compose設定
- [x] GitHub Actions CI/CD（ECR & EC2自動デプロイ）
- [x] Nginx設定（`/janitor/` → `localhost:8030`）
- [x] 本番環境デプロイ完了（ポート8030）
- [x] Lambda関数のデプロイ（`watchme-janitor-trigger`）
- [x] EventBridgeルールの作成（6時間ごと自動実行）
- [x] 本番環境での動作確認（S3削除・DB更新）
- [x] `file_status`カラム実装（削除済みファイルをメタデータとして保持）
- [x] GitHubリポジトリ: https://github.com/hey-watchme/api-janitor

### 📊 動作実績（2025-10-19時点）

**Lambda実行履歴（過去24時間）:**
- 2025-10-19 13:31 JST - 削除0件（対象なし）
- 2025-10-19 15:00 JST - **削除100件成功**（8.3MB）

**データベース状態:**
- `file_status = 'deleted'`: 108件
- すべてのレコードで処理ステータス（文字起こし・行動分析・感情分析）が完了済み

**次回実行予定:**
- 2025-10-19 21:00 JST（UTC 12:00）

---

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
  └─ Supabaseレコードの`file_status`を'deleted'に更新
```

## 📁 ディレクトリ構成

```
janitor/
├── api/                    # FastAPI本体
│   ├── main.py
│   └── requirements.txt
│
├── lambda/                 # Lambda Trigger（本番稼働中）
│   ├── lambda_function.py
│   ├── requirements.txt
│   ├── build.sh
│   ├── deploy.sh
│   └── create-eventbridge-rule.sh
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

| 項目 | 値 |
|------|-----|
| **外部URL** | https://api.hey-watch.me/janitor/ |
| **内部ポート** | 8030 |
| **コンテナ名** | janitor-api |
| **IPアドレス** | 172.27.0.30（watchme-network） |
| **EC2ディレクトリ** | /home/ubuntu/janitor-api |
| **systemdサービス** | janitor-api |
| **ECRリポジトリ** | watchme-api-janitor |
| **デプロイ方式** | ECR |

### 自動実行スケジュール（EventBridge + Lambda）

| 項目 | 値 |
|------|-----|
| **Lambda関数名** | watchme-janitor-trigger |
| **実行間隔** | 6時間ごと |
| **EventBridge Cron** | `0 */6 * * ? *` (UTC) |
| **実行時刻（JST）** | 09:00, 15:00, 21:00, 03:00 |

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
- 09:00 JST（00:00 UTC）
- 15:00 JST（06:00 UTC）
- 21:00 JST（12:00 UTC）
- 03:00 JST（18:00 UTC）

### Lambda関数

Lambda関数 (`watchme-janitor-trigger`) がEventBridgeから6時間ごとに呼び出され、このAPIに削除リクエストを送信します。

**関数名**: `watchme-janitor-trigger`
**ランタイム**: Python 3.11
**タイムアウト**: 60秒
**メモリ**: 256MB
**環境変数**: `JANITOR_API_URL=https://api.hey-watch.me/janitor/cleanup`

**実装コード** (lambda/lambda_function.py):
```python
import json
import urllib3

http = urllib3.PoolManager()
JANITOR_API_URL = os.environ.get("JANITOR_API_URL")

def lambda_handler(event, context):
    print(f"🧹 Janitor Trigger: 削除処理開始")
    response = http.request('POST', JANITOR_API_URL, timeout=60.0)
    response_data = json.loads(response.data.decode('utf-8'))

    if response.status == 200:
        deleted_count = response_data.get('deleted_count', 0)
        print(f"✅ 削除処理成功 - 削除: {deleted_count}件")
        return {'statusCode': 200, 'body': json.dumps(response_data)}
    else:
        print(f"❌ API応答エラー: {response.status}")
        return {'statusCode': response.status, 'body': json.dumps(response_data)}
```

### Lambda実行ログの確認

```bash
# 最新のログを確認
aws logs tail /aws/lambda/watchme-janitor-trigger --follow --region ap-southeast-2

# 過去のログを確認
aws logs filter-log-events \
  --log-group-name /aws/lambda/watchme-janitor-trigger \
  --region ap-southeast-2 \
  --start-time 1760760000000 \
  --filter-pattern "削除"
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

# Lambda実行ログ
aws logs tail /aws/lambda/watchme-janitor-trigger --follow --region ap-southeast-2

# Lambda関数の手動実行テスト
aws lambda invoke \
  --function-name watchme-janitor-trigger \
  --region ap-southeast-2 \
  response.json && cat response.json | jq
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

```bash
# 1. EventBridgeルールの状態確認
aws events describe-rule --name watchme-janitor-schedule --region ap-southeast-2

# 2. Lambda関数の最新ログ確認
aws logs filter-log-events \
  --log-group-name /aws/lambda/watchme-janitor-trigger \
  --region ap-southeast-2 \
  --start-time $(($(date +%s) * 1000 - 86400000)) \
  --filter-pattern "削除"

# 3. APIのヘルスチェック
curl https://api.hey-watch.me/janitor/health
curl https://api.hey-watch.me/janitor/stats

# 4. 手動でLambda関数を実行してテスト
aws lambda invoke \
  --function-name watchme-janitor-trigger \
  --region ap-southeast-2 \
  response.json

# 5. データベースの削除状態を確認（Supabaseダッシュボードで）
# SELECT COUNT(*) FROM audio_files WHERE file_status = 'deleted';
```

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
