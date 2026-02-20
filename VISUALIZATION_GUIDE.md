# Storage Wizard - Visualization Guide

## **📊 Data Export Feature**

Storage Wizard now supports exporting machine-readable data for visualization with the `--export-data` option:

```bash
# Export JSON format (comprehensive)
storage-wizard duplicates /path/to/files --export-data analysis.json

# Export CSV format (tabular)
storage-wizard duplicates /path/to/files --export-data analysis.csv

# Combined with other options
storage-wizard duplicates /path/to/files -g -t 50 --export-data viz_data.json
```

---

## **🎯 Export Data Structure**

### **JSON Format - Complete Analysis**
```json
{
  "metadata": {
    "path": "/mnt/c/tmp/test1",
    "command": "duplicates",
    "timestamp": "2026-02-06T19:27:00",
    "total_files": 31,
    "total_directories": 5,
    "duplicate_groups": 10
  },
  "directories": {
    "/mnt/c/tmp/test1/parallel1": {
      "total_files": 9,
      "duplicate_files": ["file1.jpg", "file2.png"],
      "unique_files": ["unique.txt"],
      "total_size": 1048576,
      "duplicate_percentage": 55.6
    }
  },
  "duplicate_groups": [
    {
      "group_id": 1,
      "files": ["/path/to/file1.jpg", "/path/to/file1_copy.jpg"],
      "size": 2,
      "directories": ["/dir1", "/dir2"]
    }
  ],
  "file_matrix": [
    {
      "filename": "image.jpg",
      "/mnt/c/tmp/test1/dir1": true,
      "/mnt/c/tmp/test1/dir2": false,
      "/mnt/c/tmp/test1/dir3": true
    }
  ]
}
```

### **CSV Format - Tabular Data**
```csv
filename,/mnt/c/tmp/test1/dir1,/mnt/c/tmp/test1/dir2,/mnt/c/tmp/test1/dir3
image.jpg,true,false,true
document.pdf,true,true,false
```

---

## **🎨 Visualization Options**

### **1. Venn Diagrams (2-5 Directories)**
**Best for:** Small number of directories with clear overlap patterns

**Tools:** 
- Python: `matplotlib-venn`, `plotly`
- Web: `d3.js`, `venn.js`
- R: `VennDiagram`, `ggvenn`

**Use Case:**
```
Directory A: 100 files (20 unique, 80 shared)
Directory B: 120 files (30 unique, 90 shared)  
Directory C: 80 files (10 unique, 70 shared)
```

**Visualization Shows:**
- Circle sizes represent total files per directory
- Overlaps show shared files
- Numbers in each section show file counts

### **2. Heatmap Matrix (3-10 Directories)**
**Best for:** Multiple directories with complex file sharing patterns

**Tools:**
- Python: `seaborn.heatmap`, `plotly`
- Web: `d3.js` heatmaps
- R: `pheatmap`, `ComplexHeatmap`

**Use Case:**
```
        | Dir1 | Dir2 | Dir3 | Dir4 | Dir5
File1   |  ✓   |  ✓   |  ✗   |  ✓   |  ✗
File2   |  ✗   |  ✓   |  ✓   |  ✗   |  ✓
File3   |  ✓   |  ✓   |  ✓   |  ✓   |  ✓
```

**Visualization Shows:**
- Files as rows, directories as columns
- Color intensity for presence/absence
- Clustering of similar directories
- Patterns of file distribution

### **3. Sankey Diagram (Flow Analysis)**
**Best for:** Showing file flow between directories

**Tools:**
- Python: `plotly`, `pySankey`
- Web: `d3-sankey`
- JavaScript: `google charts`

**Use Case:**
```
Source → Files → Destination
Dir1 → 50 files → Dir2
Dir3 → 30 files → Dir4
Dir5 → 20 files → Dir1
```

**Visualization Shows:**
- File movement between directories
- Width of flows represents file counts
- Identifies major duplication sources

### **4. Tree Maps (Hierarchical View)**
**Best for:** Nested directory structures with size analysis

**Tools:**
- Python: `squarify`, `plotly`
- Web: `d3.js` treemap
- R: `treemapify`

**Use Case:**
```
Root (100MB)
├── Dir1 (40MB)
│   ├── Subdir1 (25MB)
│   └── Subdir2 (15MB)
├── Dir2 (35MB)
└── Dir3 (25MB)
```

**Visualization Shows:**
- Directory sizes as rectangles
- Nested structure preserved
- Color coding for duplicate percentage
- Interactive drill-down capability

### **5. Network Graph (Relationship Mapping)**
**Best for:** Complex directory relationships and file sharing

**Tools:**
- Python: `networkx`, `plotly`
- Web: `d3.js` force-directed
- Gephi: Professional network analysis

**Use Case:**
```
Nodes: Directories
Edges: Shared files
Edge weight: Number of shared files
```

**Visualization Shows:**
- Directories as nodes
- Edge thickness shows sharing intensity
- Clusters of similar directories
- Isolated directories with unique content

### **6. Parallel Coordinates (Multi-dimensional)**
**Best for:** Comparing multiple metrics across directories

**Tools:**
- Python: `plotly`, `pandas`
- Web: `d3.js` parallel coordinates
- R: `GGally`

**Use Case:**
```
Metrics: Total Files, Duplicates, Size, Percentage
Dimensions: Directory 1, Directory 2, Directory 3...
```

**Visualization Shows:**
- Each directory as a line
- Vertical axes for different metrics
- Patterns across multiple dimensions
- Outliers and clusters

### **7. Bubble Charts (Size + Overlap)**
**Best for:** Showing directory sizes with duplicate relationships

**Tools:**
- Python: `matplotlib`, `plotly`
- Web: `d3.js` bubble chart
- Tableau: Professional viz

**Use Case:**
```
X-axis: Total files
Y-axis: Duplicate percentage
Bubble size: Directory size (MB)
Color: Duplicate intensity
```

**Visualization Shows:**
- Directory size and duplication in one view
- Identifies large directories with high duplication
- Color coding for quick insights

---

## **📈 Scenario-Based Recommendations**

### **Scenario 1: 2-3 Directories, Simple Analysis**
**Recommended:** Venn Diagram
- Clear overlap visualization
- Easy to understand
- Good for presentations

### **Scenario 2: 4-6 Directories, Complex Patterns**
**Recommended:** Heatmap Matrix
- Handles complexity well
- Shows detailed patterns
- Good for analysis

### **Scenario 3: 7-10 Directories, Large Scale**
**Recommended:** Network Graph + Tree Map
- Network for relationships
- Tree Map for size analysis
- Interactive exploration

### **Scenario 4: Nested Directory Structures**
**Recommended:** Tree Map with Sankey
- Hierarchical view
- Flow analysis
- Size distribution

### **Scenario 5: Multi-Metric Comparison**
**Recommended:** Parallel Coordinates
- Multiple dimensions
- Pattern detection
- Statistical analysis

---

## **🛠️ Implementation Examples**

### **Python Venn Diagram Example**
```python
import matplotlib.pyplot as plt
from matplotlib_venn import venn3
import json

# Load exported data
with open('analysis.json') as f:
    data = json.load(f)

# Extract directory sets
dirs = list(data['directories'].keys())
sets = []
for dir_path in dirs:
    files = set(data['directories'][dir_path]['duplicate_files'])
    sets.append(files)

# Create venn diagram
venn3(sets, tuple(dirs[:3]))
plt.title('Directory File Overlaps')
plt.show()
```

### **Python Heatmap Example**
```python
import seaborn as sns
import pandas as pd
import json

# Load data
with open('analysis.json') as f:
    data = json.load(f)

# Create matrix from file_matrix data
df = pd.DataFrame(data['file_matrix'])
df.set_index('filename', inplace=True)

# Create heatmap
plt.figure(figsize=(12, 8))
sns.heatmap(df, cmap='RdYlBu_r', cbar=True)
plt.title('File Presence Matrix')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### **D3.js Network Graph Example**
```javascript
// Load JSON data
d3.json('analysis.json').then(function(data) {
    // Create nodes from directories
    const nodes = Object.keys(data.directories).map(dir => ({
        id: dir,
        size: data.directories[dir].total_files
    }));
    
    // Create edges from duplicate groups
    const edges = [];
    data.duplicate_groups.forEach(group => {
        const dirs = group.directories;
        for (let i = 0; i < dirs.length; i++) {
            for (let j = i + 1; j < dirs.length; j++) {
                edges.push({
                    source: dirs[i],
                    target: dirs[j],
                    weight: group.size
                });
            }
        }
    });
    
    // Create network visualization
    // ... D3.js network code
});
```

---

## **🎯 Best Practices**

### **Data Preparation**
1. **Filter large datasets** - Limit to top 1000 files for performance
2. **Aggregate small directories** - Group directories with <10 files
3. **Normalize metrics** - Use percentages for fair comparison
4. **Handle missing data** - Decide on NA/zero handling

### **Visual Design**
1. **Color schemes** - Use colorblind-friendly palettes
2. **Interactive elements** - Add tooltips, zoom, filtering
3. **Responsive design** - Works on different screen sizes
4. **Export options** - PNG, SVG, PDF for reports

### **Performance**
1. **Lazy loading** - Load data on demand
2. **Web workers** - Process data in background
3. **Caching** - Store computed results
4. **Progressive rendering** - Show partial results

---

## **📚 Tool Recommendations**

### **Python Ecosystem**
- **Plotly**: Interactive web-based visualizations
- **Matplotlib**: Static, publication-quality plots
- **Seaborn**: Statistical data visualization
- **NetworkX**: Complex network analysis

### **Web Technologies**
- **D3.js**: Custom interactive visualizations
- **Chart.js**: Simple, responsive charts
- **Three.js**: 3D visualizations
- **Observable**: Notebooks with live data

### **Professional Tools**
- **Tableau**: Business intelligence platform
- **Power BI**: Microsoft analytics tool
- **Gephi**: Network analysis software
- **RStudio**: Statistical computing environment

---

## **🚀 Getting Started**

1. **Export your data:**
   ```bash
   storage-wizard duplicates /path/to/files --export-data analysis.json
   ```

2. **Choose visualization type** based on your needs

3. **Use provided examples** or adapt to your tools

4. **Iterate and refine** based on insights

---

**Storage Wizard Visualization Guide** - Transform your duplicate analysis into actionable insights! 🎨📊
