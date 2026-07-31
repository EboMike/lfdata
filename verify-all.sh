#!/bin/bash
# Script to verify all TDF files in a directory using lfdata.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="${1:-.}"

export PYTHONPATH="$DIR/src"

VENV_PATHS=(
    "$DIR/venv-wsl/bin/python"
    "$DIR/.venv/bin/python"
    "$DIR/venv/bin/python"
    "$DIR/venv/Scripts/python"
)

PYTHON_EXE=""
for path in "${VENV_PATHS[@]}"; do
    if [ -f "$path" ]; then
        PYTHON_EXE="$path"
        break
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    if command -v python3 &>/dev/null; then
        PYTHON_EXE="python3"
    else
        PYTHON_EXE="python"
    fi
fi

"$PYTHON_EXE" -m lfdata.verify_all "$TARGET_DIR"
