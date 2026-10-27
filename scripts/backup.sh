#!/usr/bin/env bash
# backup.sh — dump the school-ms Postgres database to a gzip-compressed SQL archive.
#
# Writes $ROOT/backups/schoolms-<TIMESTAMP>.sql.gz, verifies it is a valid,
# non-empty gzip, and prunes older archives so only the newest ${BACKUP_KEEP:-14}
# are kept.
#
# The script resolves its own repo root, so it can be run from any directory.
#
# Sample cron line (daily at 02:00, quiet hours):
#   0 2 * * * /abs/path/to/school-ms/scripts/backup.sh
set -euo pipefail

# --- locate repo root (parent dir of this script) and run compose from there --
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"   # docker compose must run where docker-compose.yml lives

# --- configuration ------------------------------------------------------------
BACKUP_DIR="$ROOT/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
KEEP="${BACKUP_KEEP:-14}"
archive="$BACKUP_DIR/schoolms-$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# --- run the dump -------------------------------------------------------------
# pg_dump writes its progress to stderr, which is forwarded through the
# attached `docker compose exec` and discarded with 2>/dev/null.
docker compose exec -T db \
  pg_dump -U "${POSTGRES_USER:-schoolms}" "${POSTGRES_DB:-schoolms}" 2>/dev/null \
  | gzip > "$archive"

# --- verify the archive --------------------------------------------------------
if ! [ -s "$archive" ]; then
  echo "ERROR: $archive is missing or empty; nothing was backed up." >&2
  rm -f "$archive"
  exit 1
fi
# gzip -t decompresses the whole stream to check integrity (also proves it is
# a real, non-corrupt gzip and not just a zero-byte file).
gzip -t "$archive"

# --- retention: keep the newest $KEEP archives, delete the older ones --------
# Filenames embed a sortable, fixed-width timestamp, so lexicographic order ==
# chronological order. sort -r => newest first; tail -n +KEEP+1 => the oldest
# (total - KEEP) entries to remove.
deleted=0
while IFS= read -r old; do
  [ -n "$old" ] || continue
  rm -f "$old"
  deleted=$((deleted + 1))
done < <(ls -1 "$BACKUP_DIR"/schoolms-*.sql.gz 2>/dev/null | sort -r | tail -n +$((KEEP + 1)))

# --- one-line summary ----------------------------------------------------------
echo "Backup: $archive ($(du -h "$archive" | cut -f1)) | kept ${KEEP} (most recent), pruned ${deleted}."
