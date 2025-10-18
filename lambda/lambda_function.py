"""
Janitor Trigger Lambda Function
EventBridgeから6時間ごとに呼び出され、Janitor APIに削除処理をリクエストする
"""

import json
import os
import urllib3

# HTTPクライアント
http = urllib3.PoolManager()

# Janitor APIのエンドポイント
JANITOR_API_URL = os.environ.get("JANITOR_API_URL", "https://api.hey-watch.me/janitor/cleanup")


def lambda_handler(event, context):
    """
    Lambda関数のエントリーポイント

    Args:
        event: EventBridgeからのイベントデータ
        context: Lambda実行コンテキスト

    Returns:
        dict: 実行結果
    """

    print(f"🧹 Janitor Trigger: 削除処理開始")
    print(f"   API URL: {JANITOR_API_URL}")

    try:
        # Janitor APIに削除リクエストを送信
        response = http.request(
            'POST',
            JANITOR_API_URL,
            headers={'Content-Type': 'application/json'},
            timeout=60.0  # 60秒タイムアウト
        )

        # レスポンスのパース
        response_data = json.loads(response.data.decode('utf-8'))

        # ステータスコード確認
        if response.status == 200:
            deleted_count = response_data.get('deleted_count', 0)
            failed_count = response_data.get('failed_count', 0)
            total_size = response_data.get('total_size_bytes', 0)

            print(f"✅ 削除処理成功")
            print(f"   - 削除: {deleted_count}件")
            print(f"   - 失敗: {failed_count}件")
            print(f"   - 合計サイズ: {total_size} bytes")

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': '削除処理完了',
                    'deleted_count': deleted_count,
                    'failed_count': failed_count,
                    'total_size_bytes': total_size
                })
            }
        else:
            print(f"❌ API応答エラー: {response.status}")
            print(f"   Response: {response_data}")

            return {
                'statusCode': response.status,
                'body': json.dumps({
                    'message': 'APIエラー',
                    'status_code': response.status,
                    'detail': response_data
                })
            }

    except Exception as e:
        error_message = str(e)
        print(f"❌ 削除処理エラー: {error_message}")

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': '削除処理失敗',
                'error': error_message
            })
        }
