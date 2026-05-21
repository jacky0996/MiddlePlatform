#!/bin/sh
# Cloud Run 生產環境啟動腳本
#
# Cloud Run container 啟動時做:
#   1. 跑 Django migrations(讓 DB schema 跟 code 同步)
#   2. 啟動 gunicorn
#
# 注意:多副本同時啟動會競爭 migrate,個人 portfolio min-instances=0 一次只一個沒問題;
# 真實生產建議改用獨立的 Cloud Run Job 跑 migrate,部署 web 不再做 schema 變更。

set -e

echo "[entrypoint] Running Django migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Starting gunicorn on port ${PORT:-8080}..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --threads 4 \
    --timeout 0 \
    --access-logfile - \
    --error-logfile -
