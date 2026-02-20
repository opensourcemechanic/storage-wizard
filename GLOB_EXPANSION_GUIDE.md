# Glob Expansion Guide - Directory Pattern Matching

## **🎯 New Feature Overview**

Storage Wizard now supports **glob pattern expansion** for directory paths with optional **depth control**, making it easy to analyze multiple directories without manually listing each one.

### **Basic Syntax:**
```bash
storage-wizard duplicates <glob-pattern> [options]
storage-wizard duplicates <glob-pattern> --depth <number> [options]
```

---

## **📁 Glob Pattern Examples**

### **1. Basic Wildcard Expansion**
```bash
# Expand to all subdirectories of testdirs
storage-wizard duplicates tests/testdirs/*

# Equivalent to:
storage-wizard duplicates tests/testdirs/nested1 tests/testdirs/nested2 tests/testdirs/nested3 tests/testdirs/parallel1 tests/testdirs/parallel2 tests/testdirs/parallel3
```

### **2. Multiple Patterns**
```bash
# Analyze multiple directory groups
storage-wizard duplicates "photos/*" "backup/*" --group-by-dir

# Mix patterns and specific paths
storage-wizard duplicates "music/*" /special/photos --depth 1
```

### **3. Advanced Patterns**
```bash
# Pattern with specific prefix
storage-wizard duplicates "backup_*/photos"

# Pattern with specific suffix
storage-wizard duplicates "*/photos_*"

# Complex pattern
storage-wizard duplicates "*/[0-9]*" --depth 2
```

---

## **🔧 Depth Control**

### **Depth Levels:**
- **`--depth 0`**: Current directory only
- **`--depth 1`**: Current directory + immediate subdirectories  
- **`--depth 2`**: Current directory + subdirectories + their subdirectories
- **No `--depth`**: Unlimited recursion

### **Depth Examples:**

#### **Depth 0 - Current Directory Only**
```bash
storage-wizard duplicates --depth 0 *

# Structure:
# .
# ├── dir1/          ← Included
# ├── dir2/          ← Included  
# ├── subdir1/       ← NOT included (too deep)
# └── subdir2/       ← NOT included (too deep)
```

#### **Depth 1 - Immediate Subdirectories**
```bash
storage-wizard duplicates --depth 1 *

# Structure:
# .
# ├── dir1/          ← Included
# ├── dir2/          ← Included
# ├── subdir1/       ← Included
# │   └── deep/      ← NOT included (too deep)
# └── subdir2/       ← Included
```

#### **Depth 2 - Two Levels Deep**
```bash
storage-wizard duplicates --depth 2 *

# Structure:
# .
# ├── dir1/          ← Included
# ├── dir2/          ← Included
# ├── subdir1/       ← Included
# │   └── deep/      ← Included
# │       └── very/  ← NOT included (too deep)
# └── subdir2/       ← Included
```

---

## **🎯 Real-World Use Cases**

### **Use Case 1: Photo Library Analysis**
```bash
# Analyze all year-based photo directories
storage-wizard duplicates "photos/20*" --group-by-dir --depth 0

# Analyze photo backups with depth control
storage-wizard duplicates "backup/photos/*" --depth 1 --union all_photos.txt
```

### **Use Case 2: Development Environment Cleanup**
```bash
# Find duplicates across all project directories
storage-wizard duplicates "projects/*" --depth 0 --debug

# Compare node_modules directories (depth limited)
storage-wizard duplicates "*/node_modules" --depth 0 --intersection shared_deps.txt
```

### **Use Case 3: Backup Verification**
```bash
# Compare all backup directories
storage-wizard duplicates "backup/*" --group-by-dir --depth 0

# Find what's missing between primary and backup
storage-wizard duplicates "primary/*" "backup/*" --exclusive missing_files.txt
```

### **Use Case 4: Media Server Organization**
```bash
# Analyze all media directories
storage-wizard duplicates "media/*" --depth 1 --export-data media_analysis.json

# Find duplicate movies across all locations
storage-wizard duplicates "*ovies*" --depth 2 --group-by-dir
```

---

## **📊 Pattern Matching Reference**

### **Supported Wildcards:**

| Wildcard | Description | Example |
|----------|-------------|---------|
| `*` | Match any characters (including none) | `photos/*` matches `photos/2023`, `photos/2023/jan` |
| `?` | Match exactly one character | `photo?` matches `photo1`, `photo2` |
| `[]` | Match any character in brackets | `photo[0-9]` matches `photo1`, `photo2` |
| `[!]` | Match any character NOT in brackets | `photo[!0-9]` matches `photoa`, `photob` |

### **Advanced Patterns:**

#### **Range Patterns:**
```bash
# Match numbered directories
storage-wizard duplicates "backup_[0-9]*"

# Match alphabetic ranges  
storage-wizard duplicates "photos/[a-m]*"
```

#### **Multiple Character Sets:**
```bash
# Match directories with specific prefixes
storage-wizard_duplicates "[0-9]*_*" --depth 1

# Match specific names
storage-wizard duplicates "{photo,video,doc}*" --depth 0
```

---

## **🔍 Debug and Verbose Output**

### **Debug Mode - See Expansion Details**
```bash
storage-wizard duplicates "tests/*" --debug

Output:
Debug: Expanding glob pattern: tests/*
Debug: Added directory: tests/testdirs/nested1
Debug: Added directory: tests/testdirs/nested2  
Debug: Added directory: tests/testdirs/nested3
Debug: Added directory: tests/testdirs/parallel1
Debug: Added directory: tests/testdirs/parallel2
Debug: Added directory: tests/testdirs/parallel3
Found 6 directories to analyze:
  - tests/testdirs/nested1
  - tests/testdirs/nested2
  - tests/testdirs/nested3
  - tests/testdirs/parallel1
  - tests/testdirs/parallel2
  - tests/testdirs/parallel3
```

### **Verbose Mode - Summary Information**
```bash
storage-wizard duplicates "photos/*" --verbose

Output:
Found 12 directories to analyze:
  - photos/2020
  - photos/2021
  - photos/2022
  - photos/2023
  - photos/2024
  - photos/travel
  - photos/family
  - photos/work
  - photos/projects
  - photos/archive
  - photos/backup
  - photos/temp
```

---

## **⚡ Performance Considerations**

### **Depth Impact:**
```bash
# Fast - Limited scope
storage-wizard duplicates "*" --depth 0

# Medium - Moderate scope  
storage-wizard duplicates "*" --depth 1

# Slow - Large scope (use carefully)
storage-wizard duplicates "*" --depth 3

# Very Slow - Unlimited scope (avoid on large trees)
storage-wizard duplicates "*"
```

### **Pattern Optimization:**
```bash
# Good - Specific patterns
storage-wizard duplicates "photos/20*" --depth 0

# Better - More specific
storage-wizard_duplicates "photos/202[0-3]*" --depth 0

# Best - Most specific
storage-wizard duplicates "photos/202[0-3]/[a-z]*" --depth 0
```

---

## **🚀 Advanced Combinations**

### **Pattern + Set Operations**
```bash
# Union of all files in matching directories
storage-wizard duplicates "backup/*" --union all_backup_files.txt

# Intersection across multiple pattern groups
storage-wizard duplicates "photos/*" "backup/photos/*" --intersection common_photos.txt

# Exclusive files from pattern matches
storage-wizard_duplicates "temp/*" --exclusive temp_only_files.txt
```

### **Pattern + Export + Analysis**
```bash
# Comprehensive analysis with visualization data
storage-wizard duplicates "media/*" --depth 1 --group-by-dir --export-data media_report.json --output media_analysis.txt

# Debug analysis with depth control
storage-wizard duplicates "projects/*" --depth 2 --debug --group-by-dir --percent-dup-threshold 25
```

### **Multiple Patterns with Different Depths**
```bash
# Note: Each pattern uses the same depth setting
storage-wizard duplicates "photos/*" "videos/*" --depth 1

# For different depths, run separate commands:
storage-wizard duplicates "photos/*" --depth 0 --union photos_shallow.txt
storage-wizard duplicates "videos/*" --depth 2 --union videos_deep.txt
```

---

## **🎯 Practical Examples**

### **Example 1: Home Directory Cleanup**
```bash
# Find duplicates in all user directories
storage-wizard duplicates "/home/*" --depth 1 --group-by-dir

# Focus on document directories only
storage-wizard_duplicates "/home/*/Documents" --depth 0 --union all_docs.txt
```

### **Example 2: Server Storage Analysis**
```bash
# Analyze all user home directories
storage-wizard duplicates "/home/user*" --depth 0 --export-data user_storage.json

# Check shared directories
storage-wizard duplicates "/shared/*" --depth 1 --intersection shared_files.txt
```

### **Example 3: Development Project Analysis**
```bash
# Compare all project directories
storage-wizard_duplicates "projects/*" --depth 0 --group-by-dir

# Find duplicate dependencies
storage-wizard duplicates "*/node_modules" --depth 0 --intersection shared_deps.txt

# Analyze source code directories
storage-wizard duplicates "*/src" --depth 1 --exclusive unique_code.txt
```

---

## **🔧 Troubleshooting**

### **Common Issues:**

#### **No Directories Found:**
```bash
# Problem
storage-wizard duplicates "nonexistent/*"
# Output: No valid directories found to analyze

# Solution - Check pattern and path
storage-wizard_duplicates "nonexistent/*" --debug
```

#### **Too Many Directories:**
```bash
# Problem - Performance issues
storage-wizard duplicates "*"  # May match thousands of directories

# Solution - Use depth limit
storage-wizard duplicates "*" --depth 1
```

#### **Pattern Not Matching:**
```bash
# Problem
storage-wizard duplicates "photos/202*" --depth 0
# Expected: photos/2020, photos/2021, etc.
# Got: No matches

# Solution - Check actual directory names
storage-wizard duplicates "photos/*" --debug  # See what's available
```

---

## **💡 Best Practices**

### **1. Start with Debug Mode**
```bash
# Always test patterns with debug first
storage-wizard duplicates "your_pattern" --debug --depth 0
```

### **2. Use Depth Limits**
```bash
# Default to depth 0 for performance
storage-wizard_duplicates "pattern" --depth 0

# Increase depth only when needed
storage-wizard duplicates "pattern" --depth 1
```

### **3. Combine with Set Operations**
```bash
# Get comprehensive file lists
storage-wizard duplicates "pattern" --union all_files.txt --intersection common_files.txt --exclusive unique_files.txt
```

### **4. Export for Large Analysis**
```bash
# Save results for later analysis
storage-wizard duplicates "pattern" --export-data analysis.json --output analysis.txt
```

---

## **🎉 Summary**

Glob expansion with depth control transforms Storage Wizard from requiring **manual directory listing** to supporting **intelligent pattern matching**:

- **`*` patterns** - Match multiple directories automatically
- **`--depth` control** - Limit recursion for performance
- **Debug mode** - See exactly what's being matched
- **Set operations** - Work with expanded directory lists
- **Export capabilities** - Save comprehensive results

**Result:** Analyze dozens or hundreds of directories with a single command! 🚀
