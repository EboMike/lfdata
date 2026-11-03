#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
export PYTHONPATH="$DIR/src:$PYTHONPATH"
if [ -f "$DIR/venv/bin/python" ]; then
    "$DIR/venv/bin/python" -m lflive "$@"
else
    python3 -m lflive "$@"
fi

