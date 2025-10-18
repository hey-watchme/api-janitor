# Janitor Lambda Trigger

EventBridgeから6時間ごとに呼び出され、Janitor APIに削除処理をリクエストするLambda関数

## 📋 機能

- **定期実行**: 6時間ごとにEventBridgeから自動実行
- **API呼び出し**: Janitor APIの`/cleanup`エンドポイントをHTTPリクエスト
- **ログ出力**: 削除件数、エラー情報をCloudWatch Logsに記録

## 🚀 デプロイ手順

### 1. Lambda関数の作成（初回のみ）

AWSコンソールまたはCLIでLambda関数を作成:

```bash
aws lambda create-function \
  --function-name watchme-janitor-trigger \
  --runtime python3.11 \
  --role arn:aws:iam::754724220380:role/lambda-basic-execution \
  --handler lambda_function.lambda_handler \
  --timeout 60 \
  --memory-size 256 \
  --zip-file fileb://lambda_function.zip \
  --region ap-southeast-2
```

### 2. 環境変数の設定

```bash
aws lambda update-function-configuration \
  --function-name watchme-janitor-trigger \
  --environment "Variables={JANITOR_API_URL=https://api.hey-watch.me/janitor/cleanup}" \
  --region ap-southeast-2
```

### 3. デプロイパッケージのビルド

```bash
./build.sh
```

### 4. Lambda関数の更新

```bash
./deploy.sh
```

### 5. EventBridgeルールの作成

```bash
./create-eventbridge-rule.sh
```

## ⏰ 実行スケジュール

**Cron式**: `0 */6 * * ? *`（UTC基準）

**実行タイミング（JST）**:
- 00:00 JST（15:00 UTC前日）
- 06:00 JST（21:00 UTC前日）
- 12:00 JST（03:00 UTC）
- 18:00 JST（09:00 UTC）

## 📊 監視

### CloudWatch Logsの確認

```bash
aws logs tail /aws/lambda/watchme-janitor-trigger --follow --region ap-southeast-2
```

### 手動実行（テスト）

```bash
aws lambda invoke \
  --function-name watchme-janitor-trigger \
  --region ap-southeast-2 \
  response.json

cat response.json | jq
```

## 🔧 トラブルシューティング

### Lambda関数が実行されない

1. EventBridgeルールが有効か確認
2. Lambda実行ロールに適切な権限があるか確認
3. CloudWatch Logsでエラーを確認

### API呼び出しが失敗する

1. 環境変数`JANITOR_API_URL`が正しいか確認
2. Janitor APIが稼働しているか確認（`/health`エンドポイント）
3. Lambda関数のタイムアウト設定を確認（60秒推奨）
