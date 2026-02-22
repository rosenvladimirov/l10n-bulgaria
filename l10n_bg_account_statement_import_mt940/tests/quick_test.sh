#!/bin/bash
# Quick test script for all MT940 files in Telegram Desktop folder

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="${SCRIPT_DIR}/test_parser_standalone.py"
TELEGRAM_DIR="${HOME}/Свалени/Telegram Desktop"

echo "========================================="
echo "MT940 Parser Quick Test"
echo "========================================="
echo ""

# Find all MT940 files
echo "Searching for MT940 files in: ${TELEGRAM_DIR}"
echo ""

# Test each file
count=0
for file in "${TELEGRAM_DIR}"/*.txt "${TELEGRAM_DIR}"/*.940; do
    if [ -f "$file" ]; then
        count=$((count + 1))
        echo ""
        echo "[$count] Testing: $(basename "$file")"
        echo "----------------------------------------"

        # Run test and show only summary
        python3 "$TEST_SCRIPT" "$file" 2>&1 | grep -E "(Bank Format|Account|Statement Number|Opening Balance|Closing Balance|TRANSACTIONS|✓|✗)" | head -10

        echo ""
    fi
done

if [ $count -eq 0 ]; then
    echo "No MT940 files found in ${TELEGRAM_DIR}"
else
    echo ""
    echo "========================================="
    echo "Tested $count file(s)"
    echo "========================================="
fi
