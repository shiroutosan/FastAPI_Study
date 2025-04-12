# ビルドステージ - 依存関係のインストールと最適化
FROM python:3.11-slim AS builder

WORKDIR /app

# Poetry のインストール
ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=2.1.1

RUN pip install "poetry==$POETRY_VERSION"

# 依存関係ファイルをコピー
COPY pyproject.toml* poetry.lock* ./

# 依存関係をインストール
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# 実行ステージ - 必要なファイルのみをコピー
FROM python:3.11-slim

WORKDIR /app

# 実行に必要な追加パッケージをインストール
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Google Cloud Storage との連携に必要なパッケージ
RUN pip install --no-cache-dir google-cloud-storage

# ビルドステージからPythonパッケージをコピー
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションコードをコピー
COPY ./src /app/src

# SQLiteデータベース用のディレクトリを作成
RUN mkdir -p /app/data

# 環境変数の設定
ENV DB_FILE_PATH=/app/data/sqlite.db
ENV PORT=8080
ENV PYTHONPATH=/app

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

ENTRYPOINT ["uvicorn", "src.sql_app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

