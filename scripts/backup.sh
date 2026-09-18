#!/usr/bin/env bash
# 备份 MySQL 与 data/ 目录。建议在 cron 中每日执行。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="$BACKUP_DIR/$STAMP"

mkdir -p "$TARGET"

if [[ -f "$ROOT_DIR/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
fi

echo "[backup] writing to $TARGET"

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q '^resume-ai-mysql$'; then
  docker exec resume-ai-mysql mysqldump -u"${MYSQL_USER:-resume}" -p"${MYSQL_PASSWORD:-changeme}" \
    --single-transaction --routines --triggers "${MYSQL_DATABASE:-resume_ai}" \
    > "$TARGET/resume_ai.sql"
else
  echo "[warn] resume-ai-mysql container not found; skip database dump"
fi

if [[ -d "$ROOT_DIR/data" ]]; then
  tar -czf "$TARGET/data.tar.gz" -C "$ROOT_DIR" data
fi

cat > "$TARGET/README.txt" <<EOF
Backup created at $STAMP
- resume_ai.sql: MySQL dump (if container was running)
- data.tar.gz: uploads/reports/extracted files
Restore: see docs/部署指南.md
EOF

echo "[backup] done: $TARGET"
