# Storage Wizard Test Scenarios

## Test Directory Structure

```
tests/testdirs/
├── parallel1/                    # 4 files: 1 unique, 3 shared
│   ├── file1.txt                 # UNIQUE: only in parallel1
│   ├── file2.txt                 # 2-WAY: shared with parallel2
│   ├── file3.txt                 # 3-WAY: shared with parallel2 & parallel3
│   └── file4.txt                 # 2-WAY: shared with parallel3 only
├── parallel2/                    # 3 files: 1 unique, 2 shared
│   ├── file2.txt                 # 2-WAY: shared with parallel1
│   ├── file3.txt                 # 3-WAY: shared with parallel1 & parallel3
│   └── file5.txt                 # UNIQUE: only in parallel2
├── parallel3/                    # 3 files: 1 unique, 2 shared
│   ├── file3.txt                 # 3-WAY: shared with parallel1 & parallel2
│   ├── file4.txt                 # 2-WAY: shared with parallel1 only
│   └── file6.txt                 # UNIQUE: only in parallel3
├── nested1/                      # 2 files in subdirs: both shared
│   ├── subdir1/
│   │   └── shared_2way_nested.txt    # 2-WAY NESTED: shared with nested2
│   └── subdir2/
│       └── shared_3way_nested.txt    # 3-WAY NESTED: shared with nested2 & nested3
├── nested2/                      # 2 files: both shared
│   ├── shared_2way_nested.txt    # 2-WAY NESTED: shared with nested1/subdir1
│   └── subdir/
│       └── shared_3way_nested.txt    # 3-WAY NESTED: shared with nested1/subdir2 & nested3/deep/nested
└── nested3/                      # 1 file: shared
    └── deep/
        └── nested/
            └── shared_3way_nested.txt    # 3-WAY NESTED: shared with nested1/subdir2 & nested2/subdir
```

## Expected Results

### Cross-Directory Duplicate Percentages:

**parallel1/** (6 files total):
- file1.txt: 0% cross-dup (unique)
- file2.txt: 100% cross-dup (exists in parallel2)
- file3.txt: 100% cross-dup (exists in parallel2 & parallel3)
- file4.txt: 100% cross-dup (exists in parallel3)
- extra1.txt: 0% cross-dup (unique)
- extra2.txt: 0% cross-dup (unique)
- **Expected: 50.0%** (3/6 files have cross-duplicates)

**parallel2/** (5 files total):
- file2.txt: 100% cross-dup (exists in parallel1)
- file3.txt: 100% cross-dup (exists in parallel1 & parallel3)
- file5.txt: 0% cross-dup (unique)
- extra3.txt: 0% cross-dup (unique)
- extra4.txt: 0% cross-dup (unique)
- **Expected: 40.0%** (2/5 files have cross-duplicates)

**parallel3/** (5 files total):
- file3.txt: 100% cross-dup (exists in parallel1 & parallel2)
- file4.txt: 100% cross-dup (exists in parallel1)
- file6.txt: 0% cross-dup (unique)
- extra5.txt: 0% cross-dup (unique)
- extra6.txt: 0% cross-dup (unique)
- **Expected: 40.0%** (2/5 files have cross-duplicates)

**nested1/subdir1/** (1 file total):
- shared_2way_nested.txt: 100% cross-dup (exists in nested2)
- **Expected: 100%** (1/1 files have cross-duplicates)

**nested1/subdir2/** (1 file total):
- shared_3way_nested.txt: 100% cross-dup (exists in nested2/subdir & nested3/deep/nested)
- **Expected: 100%** (1/1 files have cross-duplicates)

**nested2/** (2 files total):
- shared_2way_nested.txt: 100% cross-dup (exists in nested1/subdir1)
- subdir/shared_3way_nested.txt: 100% cross-dup (exists in nested1/subdir2 & nested3/deep/nested)
- **Expected: 100%** (2/2 files have cross-duplicates)

**nested2/subdir/** (1 file total):
- shared_3way_nested.txt: 100% cross-dup (exists in nested1/subdir2 & nested3/deep/nested)
- **Expected: 100%** (1/1 files have cross-duplicates)

**nested3/deep/nested/** (1 file total):
- shared_3way_nested.txt: 100% cross-dup (exists in nested1/subdir2 & nested2/subdir)
- **Expected: 100%** (1/1 files have cross-duplicates)

## Special Test Case: Missing File Scenario

The file4.txt demonstrates the case where a file exists in parallel1 and parallel3 but is missing from parallel2:
- parallel1/file4.txt: ✓ (exists)
- parallel2/file4.txt: ✗ (missing)
- parallel3/file4.txt: ✓ (exists)

This should show up clearly in the vimdiff-style comparison.

## Test Commands

```bash
# Test with 75% threshold (should show parallel1, parallel2, and all nested dirs)
storage-wizard duplicates tests/testdirs --group-by-dir --percent-dup-threshold=75

# Test with 50% threshold (should show all directories)
storage-wizard duplicates tests/testdirs --group-by-dir --percent-dup-threshold=50

# Test with 100% threshold (should show only nested directories)
storage-wizard duplicates tests/testdirs --group-by-dir --percent-dup-threshold=100
```

## Expected Output by Threshold

**75% threshold:**
- parallel1 (66.7%) - should NOT show (below 75%)
- parallel2 (66.7%) - should NOT show (below 75%)
- parallel3 (50.0%) - should NOT show (below 75%)
- All nested directories (100%) - should show

**50% threshold:**
- parallel1 (66.7%) - should show
- parallel2 (66.7%) - should show
- parallel3 (50.0%) - should show
- All nested directories (100%) - should show

**100% threshold:**
- parallel1 (66.7%) - should NOT show
- parallel2 (66.7%) - should NOT show
- parallel3 (50.0%) - should NOT show
- All nested directories (100%) - should show
