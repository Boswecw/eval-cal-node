#!/usr/bin/env bash
set -euo pipefail

PARTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PARTS_DIR/../.." && pwd)"
ASSEMBLED_OUTPUT="${1:-$ROOT_DIR/doc/ECNSYSTEM.md}"

require_contains() {
  if ! grep -Fq -- "$2" "$1"; then
    echo "snapshot validation failed: $3 missing in $1" >&2; echo "expected: $2" >&2; exit 1
  fi
}
require_absent() {
  if grep -Fq -- "$2" "$1"; then
    echo "snapshot validation failed: $3 still present in $1" >&2; echo "unexpected: $2" >&2; exit 1
  fi
}

require_contains "$PARTS_DIR/_index.md" "Primary output: \`doc/ECNSYSTEM.md\`" "index primary output"
require_absent  "$PARTS_DIR/_index.md" "Primary output: \`doc/SYSTEM.md\`" "index legacy primary output"

test -f "$ASSEMBLED_OUTPUT"
require_contains "$ASSEMBLED_OUTPUT" "Document version" "assembled document version header"
require_contains "$ASSEMBLED_OUTPUT" "Primary output: \`doc/ECNSYSTEM.md\`" "assembled primary output"

echo "snapshot validation passed: $ASSEMBLED_OUTPUT"
