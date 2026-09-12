#!/bin/bash
# Script to verify TDF files in a directory or single TDF file using lfdata.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_PATH="${1:-.}"
BOOST_GRACE_PERIOD="$2"

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

EXTRA_ARGS=()
if [ -n "$BOOST_GRACE_PERIOD" ]; then
    if [[ "$BOOST_GRACE_PERIOD" =~ ^[0-9]+$ ]]; then
        EXTRA_ARGS+=("--boost_grace_period_ms" "$BOOST_GRACE_PERIOD")
    else
        shift 1
        EXTRA_ARGS+=("$@")
    fi
fi

"$PYTHON_EXE" -m lfdata.verify_all "$TARGET_PATH" "${EXTRA_ARGS[@]}"

