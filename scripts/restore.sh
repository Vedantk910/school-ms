#!/usr/bin/env bash
# restore.sh — restore a school-ms Postgres database from a gzip-compressed SQL dump.
#
# Usage:  bash scripts/restore.sh <path-to-archive.sql.gz>
#
# Decompresses the archive and pipes it into psql inside the running `db`
# service. This OVERWRITES existing data in the target database.
#
# (Backups / operational scheduling; run manually only, never cron it.)
set -euo pipefail

# --- argument handling ---------------------------------------------------------
if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
  echo "Usage: $(basename "$0") <path-to-archive.sql.gz>" >&2
  echo "  Restores the given gzip-compressed SQL dump into the school-ms database." >&2
  echo "  (Create dumps with scripts/backup.sh.)" >&2
  exit 64   # EX_USAGE
fi
archive="$1"

if [ ! -f "$archive" ]; then
  echo "ERROR: archive not found: $archive" >&2
  exit 1
fi
# Refuse to run against a corrupt / truncated stream before touching the DB.
gzip -t "$archive"

# --- locate repo root (parent dir of this script) and run compose from there --
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"   # docker compose must run where docker-compose.yml lives

# --- warning banner + confirmation -------------------------------------------
cat >&2 <<EOF
======================================================================
 WARNING: RESTORE OVERWRITES DATA
----------------------------------------------------------------------
 Target database : ${POSTGRES_DB:-schoolms} (user ${POSTGRES_USER:-schoolms})
 Archive         : $archive
 Command         : gunzip -c | docker compose exec -T db psql
 This replaces the current contents of the database. Existing data
 that is not in the archive will be lost.
======================================================================
EOF
read -r -p "Type 'restore' to confirm, anything else aborts: " confirm
case "$confirm" in
  restore) : ;;
  *) echo "Aborted — no changes were made." >&2; exit 1 ;;
esac

# --- run the restore -----------------------------------------------------------
gunzip -c "$archive" | docker compose exec -T db \
  psql -U "${POSTGRES_USER:-schoolms}" -d "${POSTGRES_DB:-schoolms}"

echo "Restore complete: $archive -> ${POSTGRES_DB:-schoolms}."
