#!/bin/bash
# Script to verify all TDF files in the current directory using lfdata.

# Directory where this script resides (lfdata repository root)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Current working directory where the script was called from
CALL_DIR="$(pwd)"

FAILED=0

# Enable case-insensitive globbing and handle empty matches gracefully
shopt -s nullglob
shopt -s nocaseglob

# First, find the TDF files in the current directory
files=(*.tdf)

if [ ${#files[@]} -eq 0 ]; then
    echo "No TDF files found in the current directory."
    exit 0
fi

# Change directory to the repository root so lfdata can find assets and fonts
cd "$DIR" || { echo "Failed to change directory to $DIR"; exit 1; }

for file in "${files[@]}"; do
    abs_file="$CALL_DIR/$file"
    echo "========================================================================"
    echo "Verifying: $file"
    echo "========================================================================"
    if ! ./run.sh --input_tdf "$abs_file" --verify_tdf_replay; then
        echo "FAIL: $file verification failed"
        FAILED=1
    else
        echo "PASS: $file verification passed"
    fi
    echo ""
done

# Go back to the original directory
cd "$CALL_DIR" || exit 1

if [ $FAILED -ne 0 ]; then
    echo "Verification complete. One or more files failed verification."
    exit 1
else
    echo "Verification complete. All files passed verification."
    exit 0
fi
