#!/usr/bin/env bash
# 从备份目录恢复 MySQL 与 data/。用法: ./scripts/restore.sh backups/20260101_120000
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_directory>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$(cd "$1" && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
fi

if [[ -f "$BACKUP_DIR/resume_ai.sql" ]]; then
  echo "[restore] importing database..."
  docker exec -i resume-ai-mysql mysql -u"${MYSQL_USER:-resume}" -p"${MYSQL_PASSWORD:-changeme}" \
    "${MYSQL_DATABASE:-resume_ai}" < "$BACKUP_DIR/resume_ai.sql"
else
  echo "[warn] resume_ai.sql not found in $BACKUP_DIR"
fi

if [[ -f "$BACKUP_DIR/data.tar.gz" ]]; then
  echo "[restore] extracting data/ ..."
  tar -xzf "$BACKUP_DIR/data.tar.gz" -C "$ROOT_DIR"
fi

echo "[restore] done"
