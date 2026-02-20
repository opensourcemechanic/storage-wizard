# Multi-Path Duplicate Analysis - Usage Guide

## **🎯 New Features Added**

### **1. Multiple Path Support**
```bash
# Analyze multiple directories at once
storage-wizard duplicates /path/to/dir1 /path/to/dir2 /path/to/dir3

# Combine with other options
storage-wizard duplicates /mnt/c/tmp/test1 /mnt/c/tmp/test2 -g -t 50 -d
```

### **2. Set Operations**
```bash
# Union of all files (all unique files across all paths)
storage-wizard duplicates /path/to/dir1 /path/to/dir2 --union union_files.txt

# Intersection (files common to ALL paths)
storage-wizard duplicates /path/to/dir1 /path/to/dir2 --intersection common_files.txt

# Exclusive files (exist in only ONE path)
storage-wizard duplicates /path/to/dir1 /path/to/dir2 --exclusive unique_files.txt

# Combine multiple set operations
storage-wizard duplicates /path/to/dir1 /path/to/dir2 /path/to/dir3 \
  --union all_files.txt \
  --intersection shared_files.txt \
  --exclusive only_one_path.txt
```

### **3. Enhanced Cross-Directory Analysis**
```bash
# Fixed cross-directory duplicate calculation
storage-wizard duplicates /path/to/dir1 /path/to/dir2 --group-by-dir --debug

# Filter by cross-directory duplicate percentage
storage-wizard duplicates /path/to/dir1 /path/to/dir2 -g -t 75
```

---

## **🔧 Bug Fixes**

### **Cross-Directory Duplicate Calculation**
**Before:** Always showed 1/1 (100%) due to incorrect logic
**After:** Correctly calculates files that exist in OTHER directories

**Example Fix:**
```
Directory A: 10 files total
- 8 files are duplicates (within same directory)
- 5 files have duplicates in OTHER directories
- Cross-directory percentage: 5/10 = 50.0% (was incorrectly 100%)
```

### **Multi-Path Hash Merging**
**Before:** Each path analyzed separately
**After:** Combines duplicate groups across all paths using hash-based merging

---

## **📊 Set Operations Explained**

### **Union (--union)**
**What:** All unique files across all specified paths
**Use Case:** Get complete inventory of all files
**Example:**
```
Path1: [file1.txt, file2.txt, file3.txt]
Path2: [file2.txt, file4.txt, file5.txt]
Union: [file1.txt, file2.txt, file3.txt, file4.txt, file5.txt]
```

### **Intersection (--intersection)**
**What:** Files that exist in ALL specified paths (by hash)
**Use Case:** Find truly common files across locations
**Example:**
```
Path1: [file1.txt, file2.txt, file3.txt]
Path2: [file2.txt, file4.txt, file5.txt]
Intersection: [file2.txt] (only if same content)
```

### **Exclusive (--exclusive)**
**What:** Files that exist in only ONE of the specified paths
**Use Case:** Identify unique content per location
**Example:**
```
Path1: [file1.txt, file2.txt, file3.txt]
Path2: [file2.txt, file4.txt, file5.txt]
Exclusive: [file1.txt, file3.txt, file4.txt, file5.txt]
```

---

## **🎯 Practical Use Cases**

### **Use Case 1: Backup Verification**
```bash
# Verify backup completeness
storage-wizard duplicates /original/data /backup/location --intersection backup_check.txt

# Check for missing files
wc -l backup_check.txt
```

### **Use Case 2: Storage Consolidation Planning**
```bash
# Find common files across multiple drives
storage-wizard duplicates /drive1 /drive2 /drive3 --intersection common_files.txt

# Find unique files per drive
storage-wizard duplicates /drive1 /drive2 /drive3 --exclusive unique_per_drive.txt

# Get complete inventory
storage-wizard duplicates /drive1 /drive2 /drive3 --union complete_inventory.txt
```

### **Use Case 3: Duplicate Cleanup**
```bash
# Find directories with high cross-duplication
storage-wizard duplicates /media/photos /media/backup_photos -g -t 60

# Export for visualization
storage-wizard duplicates /media/photos /media/backup_photos --export-data dup_analysis.json
```

### **Use Case 4: Migration Planning**
```bash
# Before migration, identify what needs to be moved
storage-wizard duplicates /old/location /new/location --exclusive files_to_move.txt

# Check what's already there
storage-wizard duplicates /old/location /new/location --intersection already_migrated.txt
```

---

## **📈 Output Examples**

### **Multi-Path Analysis Output**
```
Finding duplicates in: /mnt/c/tmp/test1, /mnt/c/tmp/test2

Found 3 directories with >= 50.0% duplicates

Directory 1: /mnt/c/tmp/test1/parallel1
  Cross-directory duplicates: 5/9 (55.6%)
  Non-duplicate files (4):
    /mnt/c/tmp/test1/parallel1/unique1.txt
    /mnt/c/tmp/test1/parallel1/unique2.txt
    /mnt/c/tmp/test1/parallel1/unique3.txt
    /mnt/c/tmp/test1/parallel1/unique4.txt

Directory 2: /mnt/c/tmp/test2/parallel2
  Cross-directory duplicates: 3/8 (37.5%)

Directory 3: /mnt/c/tmp/test1/nested
  Cross-directory duplicates: 2/5 (40.0%)
```

### **Set Operation Output**
```
Union (156 files) saved to: union_files.txt
Intersection (23 files) saved to: intersection_files.txt
Exclusive (133 files) saved to: exclusive_files.txt
```

### **File Format Examples**

**union_files.txt:**
```
/mnt/c/tmp/test1/file1.txt
/mnt/c/tmp/test1/file2.txt
/mnt/c/tmp/test2/file3.txt
/mnt/c/tmp/test2/file4.txt
```

**intersection_files.txt:**
```
/mnt/c/tmp/test1/file2.txt
/mnt/c/tmp/test2/file2.txt
```

**exclusive_files.txt:**
```
/mnt/c/tmp/test1/file1.txt
/mnt/c/tmp/test1/file3.txt
/mnt/c/tmp/test2/file3.txt
/mnt/c/tmp/test2/file5.txt
```

---

## **🔍 Advanced Usage**

### **Combining All Features**
```bash
# Comprehensive analysis with all outputs
storage-wizard duplicates \
  /path/to/dir1 /path/to/dir2 /path/to/dir3 \
  --group-by-dir \
  --percent-dup-threshold=40 \
  --debug \
  --output analysis_output.txt \
  --export-data visualization_data.json \
  --union all_files.txt \
  --intersection common_files.txt \
  --exclusive unique_files.txt
```

### **Performance Tips**
1. **Limit paths**: Use 3-5 paths for best performance
2. **Use thresholds**: Filter with `--percent-dup-threshold` to reduce output
3. **Export selectively**: Use specific set operations instead of all
4. **Debug mode**: Use `--debug` to understand processing

### **Large Dataset Handling**
```bash
# For large directories, use higher threshold
storage-wizard duplicates /large/dir1 /large/dir2 -g -t 80

# Export data for external processing
storage-wizard duplicates /large/dir1 /large/dir2 --export-data large_analysis.json

# Use set operations for file lists
storage-wizard duplicates /large/dir1 /large/dir2 --union large_union.txt
```

---

## **🚀 Getting Started**

### **Basic Multi-Path Test**
```bash
# Test with multiple paths
storage-wizard duplicates tests/testdirs/parallel1 tests/testdirs/parallel2 -g -d

# Test set operations
storage-wizard duplicates tests/testdirs/parallel1 tests/testdirs/parallel2 \
  --union test_union.txt \
  --intersection test_intersection.txt \
  --exclusive test_exclusive.txt
```

### **Verify Bug Fix**
```bash
# Should show realistic percentages, not 100%
storage-wizard duplicates /path/to/multiple/dirs --group-by-dir --debug
```

---

**Multi-Path Duplicate Analysis** - Now with accurate cross-directory calculations and comprehensive set operations! 🎯
