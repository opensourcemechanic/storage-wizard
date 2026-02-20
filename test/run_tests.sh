#!/bin/bash

# Storage Wizard Test Script
# This script demonstrates various testing scenarios using the test directories

echo "=== Storage Wizard Test Scenarios ==="
echo

# Set the test directory path
TEST_DIR="test/dirs"

echo "Test Directory Structure:"
echo "├── dir1/"
echo "│   ├── photos/"
echo "│   │   ├── img001.jpg (duplicate)"
echo "│   │   ├── img002.jpg (duplicate)"
echo "│   │   └── unique1.jpg (unique to dir1)"
echo "│   └── documents/"
echo "│       └── report.pdf (duplicate v1)"
echo "├── dir2/"
echo "│   ├── photos/"
echo "│   │   ├── img001.jpg (duplicate)"
echo "│   │   ├── img002.jpg (duplicate)"
echo "│   │   └── unique2.jpg (unique to dir2)"
echo "│   └── documents/"
echo "│       └── report.pdf (duplicate v1)"
echo "├── dir3/"
echo "│   ├── photos/"
echo "│   │   ├── img001.jpg (duplicate)"
echo "│   │   └── img003.jpg (duplicate with dir4)"
echo "│   └── documents/"
echo "│       └── report.pdf (different content - v2)"
echo "└── dir4/"
echo "    ├── photos/"
echo "    │   ├── img001.jpg (duplicate)"
echo "    │   ├── img002.jpg (duplicate)"
echo "    │   └── img003.jpg (duplicate with dir3)"
echo "    └── documents/"
echo "        └── report.pdf (duplicate v1)"
echo

echo "=== Test Commands ==="
echo

echo "1. Basic scan of all test directories:"
echo "   storage-wizard scan $TEST_DIR"
echo

echo "2. Find all duplicates (regular mode):"
echo "   storage-wizard duplicates $TEST_DIR"
echo

echo "3. Find directories with 100% duplicates:"
echo "   storage-wizard duplicates $TEST_DIR --group-by-dir --percent-dup-threshold=100"
echo

echo "4. Find directories with 75%+ duplicates (shows partial duplicates):"
echo "   storage-wizard duplicates $TEST_DIR --group-by-dir --percent-dup-threshold=75"
echo

echo "5. Find directories with 50%+ duplicates:"
echo "   storage-wizard duplicates $TEST_DIR --group-by-dir --percent-dup-threshold=50"
echo

echo "6. Generate consolidation commands:"
echo "   storage-wizard generate $TEST_DIR --output consolidate_test.sh"
echo

echo "7. Full analysis with JSON output:"
echo "   storage-wizard analyze $TEST_DIR --output analysis.json --format json"
echo

echo "8. Test individual directories:"
echo "   storage-wizard duplicates $TEST_DIR/dir1 --group-by-dir"
echo "   storage-wizard duplicates $TEST_DIR/dir2 --group-by-dir"
echo

echo "=== Expected Results ==="
echo
echo "- img001.jpg: Should appear in all 4 directories (100% duplicate)"
echo "- img002.jpg: Should appear in dir1, dir2, dir4 (missing from dir3)"
echo "- img003.jpg: Should appear in dir3, dir4 (missing from dir1, dir2)"
echo "- report.pdf: v1 in dir1, dir2, dir4; v2 in dir3 (different content)"
echo "- unique1.jpg: Only in dir1"
echo "- unique2.jpg: Only in dir2"
echo

echo "=== Running Tests ==="
echo

# Activate virtual environment and run tests
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "Virtual environment not found. Please activate it first."
    exit 1
fi

echo "Testing basic scan..."
storage-wizard scan $TEST_DIR
echo

echo "Testing duplicates with 100% threshold..."
storage-wizard duplicates $TEST_DIR --group-by-dir --percent-dup-threshold=100
echo

echo "Testing duplicates with 75% threshold..."
storage-wizard duplicates $TEST_DIR --group-by-dir --percent-dup-threshold=75
echo

echo "Testing duplicates with 50% threshold..."
storage-wizard duplicates $TEST_DIR --group-by-dir --percent-dup-threshold=50
echo

echo "=== Test Complete ==="
