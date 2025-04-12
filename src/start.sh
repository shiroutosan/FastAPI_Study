#!/bin/bash

set -eu # エラーや未定義の変数を使おうとしたときには処理を打ち止め

# GCSからSQLiteデータベースをダウンロード
if [ -n "$DB_BUCKET_NAME" ] && [ -n "$DB_FILE_NAME" ]; then
    echo "Downloading SQLite database from GCS: gs://${DB_BUCKET_NAME}/${DB_FILE_NAME}"
    gcloud storage cp gs://${DB_BUCKET_NAME}/${DB_FILE_NAME} ${DB_FILE_PATH}
    echo "Database downloaded to ${DB_FILE_PATH}"
else
    echo "No GCS database configured, using local database file"
fi

# データベースファイルの権限を設定
chmod 644 ${DB_FILE_PATH}

# FastAPIアプリケーションを起動
exec python main.py