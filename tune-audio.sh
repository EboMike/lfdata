#!/usr/bin/env bash

PYTHON_CMD="python3"
for candidate in "venv-wsl/bin/python3" "venv/bin/python3" "python3" "python"; do
    if command -v "$candidate" >/dev/null 2>&1 || [ -f "$candidate" ]; then
        if "$candidate" -c "import cv2, scipy, numpy, yaml" 2>/dev/null; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

export PYTHONPATH="$(dirname "$0")/src:$PYTHONPATH"

"$PYTHON_CMD" -m lfdata.video.audio_benchmark "$@"
