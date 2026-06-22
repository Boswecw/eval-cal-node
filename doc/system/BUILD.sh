#!/usr/bin/env bash
set -euo pipefail

# Assembles the compiled system reference (designation ECN).
# Fail-closed: missing structure, designation/output mismatch, or snapshot
# validation failure aborts the build with BUILD_FAILED on stderr.

PARTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PARTS_DIR/../.." && pwd)"
DESIGNATION="ECN"
OUTPUT="${OUTPUT:-doc/ECNSYSTEM.md}"
VALIDATOR="$PARTS_DIR/validate_snapshots.sh"
COMPATIBILITY_OUTPUTS=()

fail() { echo "BUILD_FAILED: $1" >&2; exit 1; }

case "$OUTPUT" in
  *"${DESIGNATION}SYSTEM.md") ;;
  *) fail "output path '$OUTPUT' does not match designation ${DESIGNATION}" ;;
esac

[ -f "$PARTS_DIR/_index.md" ] || fail "missing $PARTS_DIR/_index.md"
REQUIRED_DIRS=(00_overview 10_service-contract 20_runtime 30_dependencies 40_governance 50_operations 99_appendices)
for dir in "${REQUIRED_DIRS[@]}"; do
  [ -d "$PARTS_DIR/$dir" ] || fail "missing required folder doc/system/$dir"
  found=0
  for part in "$PARTS_DIR/$dir"/[0-9][0-9]-*.md; do [ -e "$part" ] && found=1 && break; done
  [ "$found" -eq 1 ] || fail "no numbered chapters in doc/system/$dir"
done

mkdir -p "$(dirname "$ROOT_DIR/$OUTPUT")"
TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT
cat "$PARTS_DIR/_index.md" > "$TMP_OUTPUT"
PART_COUNT=0
while IFS= read -r part; do
  { echo ""; echo "---"; echo ""; cat "$part"; } >> "$TMP_OUTPUT"
  PART_COUNT=$((PART_COUNT + 1))
done < <(find "$PARTS_DIR" -mindepth 2 -maxdepth 2 -type f -name '[0-9][0-9]-*.md' | sort)
[ "$PART_COUNT" -ge 7 ] || fail "expected at least 7 chapters, found $PART_COUNT"
if [ -f "$VALIDATOR" ]; then bash "$VALIDATOR" "$TMP_OUTPUT" || fail "snapshot validation failed"; else fail "missing validator $VALIDATOR"; fi
cp "$TMP_OUTPUT" "$ROOT_DIR/$OUTPUT"
chmod 664 "$ROOT_DIR/$OUTPUT"
for compatibility_output in "${COMPATIBILITY_OUTPUTS[@]}"; do
  [ -n "$compatibility_output" ] || continue
  [ "$compatibility_output" = "$OUTPUT" ] && continue
  mkdir -p "$(dirname "$ROOT_DIR/$compatibility_output")"
  cp "$TMP_OUTPUT" "$ROOT_DIR/$compatibility_output"
  chmod 664 "$ROOT_DIR/$compatibility_output"
done
LINE_COUNT=$(wc -l < "$ROOT_DIR/$OUTPUT")
echo "BUILD_OK designation=${DESIGNATION} output=${OUTPUT} parts=${PART_COUNT} lines=${LINE_COUNT}"
