#!/usr/bin/env bash

PYTHON_CMD="python3"
if [ -f "venv-wsl/bin/python3" ]; then
    PYTHON_CMD="venv-wsl/bin/python3"
elif [ -f "venv/bin/python3" ]; then
    PYTHON_CMD="venv/bin/python3"
fi

export PYTHONPATH="$(dirname "$0")/src:$PYTHONPATH"

"$PYTHON_CMD" -m lfdata.video.audio_matcher "$@"
