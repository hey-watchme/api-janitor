#!/usr/bin/env python3
"""
Janitor API - 音声データ自動削除サービス
処理済みの音声ファイルをS3から削除し、プライバシーを保護する

使用例:
- Lambda関数からAPI呼び出し（6時間ごと）
- EventBridge経由で定期実行
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import os
import boto3
from botocore.exceptions import ClientError

# FastAPIアプリ
app = FastAPI(
    title="WatchMe Janitor API",
    description="処理済み音声データを自動削除してプライバシーを保護",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "watchme-vault")
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")

# Supabaseクライアント
supabase_client: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# S3クライアント
s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


# レスポンスモデル
class CleanupResult(BaseModel):
    success: bool
    deleted_count: int
    failed_count: int
    skipped_count: int
    total_size_bytes: int
    deleted_files: List[str]
    failed_files: List[dict]
    message: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    s3_configured: bool
    supabase_configured: bool


# ユーティリティ関数
def get_utc_time():
    """UTC時刻を取得"""
    return datetime.now(timezone.utc)


@app.get("/")
async def root():
    """ルート情報"""
    return {
        "service": "WatchMe Janitor API",
        "version": "1.0.0",
        "description": "処理済み音声データを自動削除してプライバシーを保護",
        "endpoints": {
            "health": "/health",
            "cleanup": "/cleanup (POST)",
            "stats": "/stats"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェック"""
    return HealthResponse(
        status="healthy",
        timestamp=get_utc_time().isoformat(),
        s3_configured=s3_client is not None,
        supabase_configured=supabase_client is not None
    )


@app.get("/stats")
async def get_stats():
    """削除対象ファイルの統計情報を取得"""
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase client not configured")

    try:
        # 24時間以上前のデータを検索
        cutoff_time = get_utc_time() - timedelta(hours=24)

        # 削除対象の検索（すべての処理が完了しているファイル）
        response = supabase_client.table("audio_files") \
            .select("device_id,file_path,created_at") \
            .eq("transcriptions_status", "completed") \
            .eq("behavior_features_status", "completed") \
            .eq("emotion_features_status", "completed") \
            .lt("created_at", cutoff_time.isoformat()) \
            .execute()

        eligible_files = response.data if response.data else []

        return {
            "eligible_for_deletion": len(eligible_files),
            "cutoff_time": cutoff_time.isoformat(),
            "criteria": {
                "transcriptions_status": "completed",
                "behavior_features_status": "completed",
                "emotion_features_status": "completed",
                "age_threshold_hours": 24
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.post("/cleanup", response_model=CleanupResult)
async def cleanup_audio_files():
    """
    処理済み音声ファイルを削除

    削除条件:
    1. transcriptions_status = 'completed'
    2. behavior_features_status = 'completed'
    3. emotion_features_status = 'completed'
    4. created_at が 24時間以上前
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase client not configured")

    if not s3_client:
        raise HTTPException(status_code=500, detail="S3 client not configured")

    deleted_count = 0
    failed_count = 0
    skipped_count = 0
    total_size = 0
    deleted_files = []
    failed_files = []

    try:
        # 24時間以上前のデータを検索
        cutoff_time = get_utc_time() - timedelta(hours=24)

        print(f"🧹 Janitor: 削除処理開始 - cutoff_time={cutoff_time.isoformat()}")

        # 削除対象の検索（上限100件）
        response = supabase_client.table("audio_files") \
            .select("device_id,recorded_at,file_path,created_at") \
            .eq("transcriptions_status", "completed") \
            .eq("behavior_features_status", "completed") \
            .eq("emotion_features_status", "completed") \
            .lt("created_at", cutoff_time.isoformat()) \
            .limit(100) \
            .execute()

        files_to_delete = response.data if response.data else []

        print(f"📊 削除対象ファイル数: {len(files_to_delete)}")

        # ファイルを1つずつ削除
        for file_record in files_to_delete:
            file_path = file_record.get("file_path")
            device_id = file_record.get("device_id")
            recorded_at = file_record.get("recorded_at")

            if not file_path:
                skipped_count += 1
                print(f"⚠️ file_pathが空: device_id={device_id}")
                continue

            try:
                # ファイルサイズを取得（削除前）
                file_size = 0
                try:
                    head_response = s3_client.head_object(
                        Bucket=S3_BUCKET_NAME,
                        Key=file_path
                    )
                    file_size = head_response.get('ContentLength', 0)
                    total_size += file_size
                except ClientError as e:
                    if e.response.get('Error', {}).get('Code') != 'NoSuchKey':
                        print(f"⚠️ ファイルサイズ取得失敗: {file_path}")

                # S3からファイル削除
                s3_response = s3_client.delete_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=file_path
                )

                deleted_count += 1
                deleted_files.append(file_path)
                print(f"✅ 削除成功: {file_path} ({file_size} bytes)")

                # Supabaseレコードも削除（オプション）
                # もしくは deleted_at カラムを更新してソフトデリート
                try:
                    supabase_client.table("audio_files") \
                        .delete() \
                        .eq("device_id", device_id) \
                        .eq("recorded_at", recorded_at) \
                        .execute()
                    print(f"📝 Supabaseレコード削除: device_id={device_id}, recorded_at={recorded_at}")
                except Exception as db_error:
                    print(f"⚠️ Supabaseレコード削除失敗: {str(db_error)}")

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'NoSuchKey':
                    # ファイルが既に存在しない場合（問題なし）
                    print(f"ℹ️ ファイル既に存在しない: {file_path}")
                    skipped_count += 1

                    # Supabaseレコードも削除
                    try:
                        supabase_client.table("audio_files") \
                            .delete() \
                            .eq("device_id", device_id) \
                            .eq("recorded_at", recorded_at) \
                            .execute()
                    except:
                        pass
                else:
                    failed_count += 1
                    failed_files.append({
                        "file_path": file_path,
                        "error": str(e)
                    })
                    print(f"❌ 削除失敗: {file_path} - {str(e)}")

            except Exception as e:
                failed_count += 1
                failed_files.append({
                    "file_path": file_path,
                    "error": str(e)
                })
                print(f"❌ 削除失敗: {file_path} - {str(e)}")

        # 結果サマリー
        print(f"🎉 削除処理完了: 成功={deleted_count}, 失敗={failed_count}, スキップ={skipped_count}")

        return CleanupResult(
            success=failed_count == 0,
            deleted_count=deleted_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            total_size_bytes=total_size,
            deleted_files=deleted_files[:100],  # 最大100件まで返す
            failed_files=failed_files,
            message=f"削除完了: {deleted_count}件削除, {failed_count}件失敗, {skipped_count}件スキップ"
        )

    except Exception as e:
        print(f"❌ 削除処理エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# アプリケーション起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)
