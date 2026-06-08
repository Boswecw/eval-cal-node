#!/usr/bin/env bash
set -euo pipefail

PARTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PARTS_DIR/../.." && pwd)"
OUTPUT="${OUTPUT:-doc/ECNSYSTEM.md}"
VALIDATOR="$PARTS_DIR/validate_snapshots.sh"

mkdir -p "$(dirname "$ROOT_DIR/$OUTPUT")"
TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

if [ -f "$PARTS_DIR/_index.md" ]; then
  cat "$PARTS_DIR/_index.md" > "$TMP_OUTPUT"
fi

shopt -s nullglob
for part in "$PARTS_DIR"/[0-9][0-9]-*.md; do
  echo "" >> "$TMP_OUTPUT"
  echo "---" >> "$TMP_OUTPUT"
  echo "" >> "$TMP_OUTPUT"
  cat "$part" >> "$TMP_OUTPUT"
done
shopt -u nullglob

if [ -x "$VALIDATOR" ]; then
  bash "$VALIDATOR" "$TMP_OUTPUT"
fi

cp "$TMP_OUTPUT" "$ROOT_DIR/$OUTPUT"
chmod 664 "$ROOT_DIR/$OUTPUT"
echo "$OUTPUT assembled: $(wc -l < "$ROOT_DIR/$OUTPUT") lines"
