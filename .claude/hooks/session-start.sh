#!/bin/bash
# SessionStart hook for eval-cal-node.
#
# eval-cal-node requires Python >= 3.12 (see pyproject.toml), but the
# container's default `python`/`python3` may be older (e.g. 3.11). This hook
# provisions a dedicated 3.12 virtualenv, installs the package with its test
# dependencies, and makes that interpreter the default for the rest of the
# session so tests run without manual setup.
set -euo pipefail

# Only run in Claude Code on the web / remote environments.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Locate a Python 3.12 interpreter.
PYTHON_BIN="$(command -v python3.12 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "session-start: python3.12 not found on PATH" >&2
  exit 1
fi

# Create the project venv on 3.12 (idempotent — reused if already present).
if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

# Install the package with its test dependencies.
./.venv/bin/python -m pip install --quiet --upgrade pip
./.venv/bin/python -m pip install --quiet -e ".[test]"

# Make the 3.12 venv the default interpreter for the rest of the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export VIRTUAL_ENV=\"$CLAUDE_PROJECT_DIR/.venv\""
    echo "export PATH=\"$CLAUDE_PROJECT_DIR/.venv/bin:\$PATH\""
  } >> "$CLAUDE_ENV_FILE"
fi

echo "session-start: ready on $(./.venv/bin/python --version)"
