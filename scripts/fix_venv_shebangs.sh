#!/bin/bash
# Scripts shebang path fixer for TideTrading environment.
# Corrects old Vibe-Trading paths to TideTrading in python venv.

set -e

CURRENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "Fixing shebang paths in ${CURRENT_DIR}/.venv/bin/ to point to the correct project directory..."

if [ ! -d "${CURRENT_DIR}/.venv/bin" ]; then
    echo "Error: .venv/bin directory not found at ${CURRENT_DIR}/.venv/bin"
    exit 1
fi

OLD_PATH="/home/skloxo/aho/openclaw/project/Vibe-Trading"
NEW_PATH="${CURRENT_DIR}"

count=0
for file in "${CURRENT_DIR}/.venv/bin"/*; do
    if [ -f "$file" ] && [ ! -L "$file" ]; then
        # Check if the file contains the old path
        if grep -q "$OLD_PATH" "$file"; then
            echo "Repairing shebang in: $(basename "$file")"
            sed -i "s|$OLD_PATH|$NEW_PATH|g" "$file"
            count=$((count + 1))
        fi
    fi
done

echo "Successfully repaired shebang paths in $count scripts!"
