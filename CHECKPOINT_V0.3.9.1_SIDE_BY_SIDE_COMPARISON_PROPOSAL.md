# Checkpoint v0.3.9.1: Side-by-Side Comparison Visualization Proposal

## Date
2026-02-27

## Current State Checkpoint

### ✅ Working Features (v0.3.9)
- **Size-based filtering**: `--min-size` option works perfectly for duplicate filtering
- **Enhanced media support**: `.dv` extension added for digital video files
- **Clean interface**: Removed non-functional post-scan filtering options
- **Focused functionality**: Only functional options available in compare command

### ✅ Current Compare Command
```bash
storage-wizard treemap compare [OPTIONS] LABELS...
```
**Available options:**
- `--min-size, -s SIZE`: Minimum size threshold for duplicates
- `--depth, -d INTEGER`: Max display depth
- `--sparse`: Display only duplicate subtrees
- `--store TEXT`: Override treemap store directory

### ✅ Real-World Testing Results
- **86 duplicate video directories** found across drives
- **All .dv files recognized** with enhanced media support
- **Size filtering working perfectly** (50MB, 100MB, 1GB thresholds tested)
- **Clean, reliable interface** with no broken functionality

## 🎯 Proposed Enhancement: Side-by-Side Comparison Visualization

### 🚨 Current Visualization Problem
The current sparse tree display shows:
- One entire tree at a time
- Colors indicate duplicates but hard to compare
- No clear side-by-side comparison of differences
- Difficult to see exactly where subtrees differ

### 💡 New Visualization Concept

#### **Core Idea:**
For each duplicate group found:
1. **Go up 1 level** on each side until finding different subtrees
2. **Display roots side-by-side** for easy comparison
3. **Show sparse traversal** of paths to differences
4. **Highlight first differing directories** side-by-side

#### **Visual Layout:**
```
╭───────────────────────────────────────────── Duplicate Group 1/86 ─────────────────────────────────────────────╮
│                                                                                                               │
│ 📁 /media/d/Videos/CapturesRsync/2000AugustMacIsland/    📁 /media/e/Videos/RsyncFromCamcorder/Videos/CapturesRsync/2000AugustMacIsland/ │
│ [11.4 GB, 196 files]                               [11.4 GB, 196 files]                               │
│                                                                                                               │
│ 🎯 DIFFERENCES FOUND:                                                                                         │
│                                                                                                               │
│ 📂 Left Tree Path:                              📂 Right Tree Path:                                 │
│ └── goodnames/                                    └── goodnames/                                      │
│     ├── 2000AugustMacIsland2000.08.05_16-07-27.dv     ├── 2000AugustMacIsland2000.08.05_16-07-27.dv         │
│     ├── 2000AugustMacIsland2000.08.05_16-07-38.dv     ├── 2000AugustMacIsland2000.08.05_16-07-38.dv         │
│     🎯 MISSING: 2000AugustMacIsland2000.08.05_16-08-17.dv  🎯 EXTRA: 2000AugustMacIsland2000.08.05_16-08-17.dv      │
│     └── ...                                         └── ...                                             │
│                                                                                                               │
│ 📊 Summary: 195 files match, 1 file difference (missing/extra)                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

#### **Alternative Layout for Directory Differences:**
```
╭───────────────────────────────────────────── Duplicate Group 1/86 ─────────────────────────────────────────────╮
│                                                                                                               │
│ 🎯 FIRST DIFFERENCE FOUND AT:                                                                                 │
│                                                                                                               │
│ 📂 Left:  /media/d/Videos/CapturesRsync/2000SeptBrownsLakebadnames.bad                                        │
│ 📂 Right: /media/e/Videos/RsyncFromCamcorder/Videos/CapturesRsync/2000SeptBrownsLakebadnames.bad              │
│                                                                                                               │
│ 📁 Left Tree Contents:                          📁 Right Tree Contents:                              │
│ └── goodnames/                                    └── goodnames/                                      │
│     ├── 2000SeptBrownsLake_2000.09.16_12-47-25.dv     ├── 2000SeptBrownsLake_2000.09.16_12-47-25.dv         │
│     ├── 2000SeptBrownsLake_2000.09.16_12-47-58.dv     ├── 2000SeptBrownsLake_2000.09.16_12-47-58.dv         │
│     🎯 MISSING: 2000SeptBrownsLake_2000.09.16_12-48-15.dv  🎯 EXTRA: 2000SeptBrownsLake_2000.09.16_12-48-15.dv      │
│     └── ...                                         └── ...                                             │
│                                                                                                               │
│ 📊 Summary: Identical structure, 1 file content difference                                                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### 🔧 Technical Implementation Plan

#### **New Function: `find_first_difference()`**
```python
def find_first_difference(node1: TreeNode, node2: TreeNode) -> Tuple[TreeNode, TreeNode, List[str], List[str]]:
    """Find first differing subtree and return paths to difference."""
    # Traverse both trees simultaneously
    # Find first level where structure or content differs
    # Return the differing nodes and their paths
```

#### **New Function: `display_side_by_side_comparison()`**
```python
def display_side_by_side_comparison(
    dup_groups: List[Tuple], 
    max_depth: Optional[int] = None,
    min_size: Optional[int] = None
) -> None:
    """Display duplicate groups in side-by-side format."""
    for i, (hash_val, entries) in enumerate(dup_groups, 1):
        if len(entries) >= 2:  # At least two trees to compare
            left_entry, right_entry = entries[0], entries[1]
            left_node, right_node = left_entry[1], right_entry[1]
            
            # Find first difference
            left_diff, right_diff, left_path, right_path = find_first_difference(left_node, right_node)
            
            # Display side-by-side comparison
            display_comparison_panel(i, len(dup_groups), left_entry, right_entry, left_diff, right_diff)
```

#### **Enhanced Tree Traversal**
```python
def sparse_traversal_to_difference(node: TreeNode, target_path: List[str]) -> List[str]:
    """Generate sparse traversal showing path to difference."""
    # Show only directories along the path to the difference
    # Highlight the exact point of difference
    # Show file-level differences at the target
```

### 📊 Comparison Types to Handle

#### **1. Identical Subtrees**
```
🎯 IDENTICAL SUBTREES
📁 Both: /path/to/identical/directory/
📊 Summary: 100% match, 196 files, 11.4 GB each
```

#### **2. Missing/Extra Files**
```
🎯 FILE COUNT DIFFERENCE
📁 Left: 195 files, 📁 Right: 196 files
🎯 MISSING: filename.dv (left side)
🎯 EXTRA: filename.dv (right side)
```

#### **3. Different Directory Structure**
```
🎯 STRUCTURE DIFFERENCE
📂 Left: missing_subdir/
📂 Right: extra_subdir/
📊 Summary: Different directory organization
```

#### **4. Content Differences (if using slow hashing)**
```
🎯 CONTENT DIFFERENCE
📁 File: same_name.dv
🎯 LEFT HASH: abc123...
🎯 RIGHT HASH: def456...
📊 Summary: Same filename, different content
```

### 🎨 Visual Design Elements

#### **Icons and Symbols:**
- 📁 Directory root
- 📂 Subdirectory
- 🎯 Difference point
- 📊 Summary information
- ➡️ Path direction
- ❌ Missing item
- ➕ Extra item

#### **Color Coding:**
- 🟢 Identical content
- 🔴 Missing/extra differences
- 🟡 Structural differences
- 🔵 Path information
- ⚪ Summary information

#### **Layout Structure:**
1. **Group header**: "Duplicate Group X/Y"
2. **Comparison overview**: Side-by-side root paths
3. **Difference location**: Where the first difference was found
4. **Detailed comparison**: Side-by-side content
5. **Summary statistics**: What was found

### 🚀 Implementation Steps

#### **Phase 1: Core Difference Detection**
1. Implement `find_first_difference()` function
2. Create path traversal utilities
3. Add difference type classification

#### **Phase 2: Side-by-Side Display**
1. Design comparison panel layout
2. Implement sparse traversal display
3. Add visual indicators and icons

#### **Phase 3: Enhanced User Experience**
1. Add progress indication for multiple groups
2. Implement filtering for difference types
3. Add export functionality for comparison results

#### **Phase 4: Advanced Features**
1. Interactive difference navigation
2. File-level content comparison
3. Batch comparison reporting

### 📈 Expected Benefits

#### **Improved Usability:**
- **Clear visual comparison**: Side-by-side layout
- **Focused differences**: Shows exactly what differs
- **Intuitive navigation**: Easy to understand differences
- **Actionable insights**: Clear what needs attention

#### **Better Analysis:**
- **Precise difference location**: Know exactly where differences are
- **Difference classification**: Understand type of differences
- **Summary statistics**: Quick overview of comparison results
- **Export capability**: Save comparison results

#### **Enhanced Workflow:**
- **Faster decision making**: Clear differences visible
- **Better cleanup planning**: Know what to keep/remove
- **Validation verification**: Confirm backup integrity
- **Documentation**: Record of differences

### 🎯 Use Cases Enabled

#### **Backup Verification:**
```bash
storage-wizard treemap compare backup_primary backup_secondary --side-by-side
```
Shows exactly which files differ between backups

#### **Storage Cleanup:**
```bash
storage-wizard treemap compare drive1 drive2 --side-by-side --min-size 100MB
```
Shows large duplicates and their differences for cleanup decisions

#### **Media Organization:**
```bash
storage-wizard treemap compare photos_2023 photos_2024 --side-by-side
```
Shows differences between photo collections across years

#### **System Migration:**
```bash
storage-wizard treemap compare old_system new_system --side-by-side --ignore-system
```
Shows what's different after system migration

### 🔧 Technical Considerations

#### **Performance:**
- **Efficient traversal**: Stop at first difference for speed
- **Memory usage**: Minimal additional memory for comparison
- **Large datasets**: Handle thousands of differences efficiently

#### **Compatibility:**
- **Existing treemaps**: Works with all saved treemap formats
- **Size filtering**: Integrates with existing size filters
- **Output options**: Both terminal and export formats

#### **Error Handling:**
- **Missing files**: Graceful handling of missing content
- **Path differences**: Handle different directory structures
- **Hash differences**: Content comparison when available

---

**This checkpoint captures the current working state and proposes a major enhancement to make duplicate comparison much more intuitive and actionable with side-by-side visualization of differences.**
