#!/usr/bin/env bash

set -euo pipefail

# Recombine split Postgres dump parts into a single file.
PART_PREFIX="backups/insightsync_postgres_2026-05-06_curated_snapshot.dump.part."
OUTPUT="backups/insightsync_postgres_2026-05-06_curated_snapshot.dump"

if [[ -f "$OUTPUT" ]]; then
  echo "Output file already exists: $OUTPUT"
  echo "Please remove it first if you want to regenerate." >&2
  exit 1
fi

if ! ls ${PART_PREFIX}* >/dev/null 2>&1; then
  echo "No part files found with prefix: $PART_PREFIX" >&2
  exit 1
fi

cat ${PART_PREFIX}* > "$OUTPUT"

ls -lh "$OUTPUT"
echo "Recreated $OUTPUT"
