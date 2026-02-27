# Image Visualization Guide

## Overview

The `visualize_cache_images.py` script provides image-based visualizations for cached treemap data using matplotlib. This complements the existing text-based visualization tools with graphical representations.

## Dependencies

```bash
pip install matplotlib numpy
```

## Available Visualizations

### 1. Treemap Visualization
Creates a squarified treemap showing directory sizes as rectangles.

```bash
python visualize_cache_images.py treemap <label> [output_file]
```

**Features:**
- Rectangle size represents directory size
- Color gradient from blue (small) to red (large)
- Hierarchical layout with nested rectangles
- Configurable depth and minimum size thresholds

**Example:**
```bash
python visualize_cache_images.py treemap mediabig mediabig_treemap.png
```

### 2. Pie Chart Visualization
Shows the distribution of the largest directories as a pie chart.

```bash
python visualize_cache_images.py pie <label> [output_file]
```

**Features:**
- Top N largest directories by size
- Percentage labels for each slice
- Color-coded segments
- File count information

**Example:**
```bash
python visualize_cache_images.py pie brian brian_pie_chart.png
```

### 3. Bar Chart Comparison
Compares multiple treemaps side by side with bar charts.

```bash
python visualize_cache_images.py compare <label1,label2,...> [output_file]
```

**Features:**
- Size comparison across drives
- File count comparison
- Side-by-side layout
- Value labels on bars

**Example:**
```bash
python visualize_cache_images.py compare brian,mediabig,nvme1 drive_comparison.png
```

### 4. Duplicate Heatmap
Creates a heatmap showing duplicate sizes across drives.

```bash
python visualize_cache_images.py heatmap [min_size_gb] [output_file]
```

**Features:**
- Heatmap matrix of duplicate sizes
- Color intensity represents duplicate volume
- Size annotations in cells
- Configurable minimum size threshold

**Example:**
```bash
python visualize_cache_images.py heatmap 0.5 duplicate_heatmap.png
```

## Usage Examples

### Basic Usage
```bash
# Create treemap visualization
python visualize_cache_images.py treemap mediabig

# Create pie chart
python visualize_cache_images.py pie nvme1 nvme1_pie.png

# Compare multiple drives
python visualize_cache_images.py compare brian,mediabig

# Generate duplicate heatmap
python visualize_cache_images.py heatmap 0.1
```

### Advanced Usage
```bash
# Custom output files
python visualize_cache_images.py treemap mediabig /path/to/output.png

# High-resolution output (matplotlib default is 300 DPI)
python visualize_cache_images.py pie brian brian_pie_hd.png

# Batch processing
for label in brian mediabig nvme1; do
    python visualize_cache_images.py treemap $label
    python visualize_cache_images.py pie $label
done
```

## Output Files

### File Naming
- Default naming: `{label}_treemap.png`, `{label}_pie_chart.png`
- Custom naming: Specify output file as second argument
- Format: PNG (recommended for quality)

### Image Quality
- **Resolution**: 300 DPI (print quality)
- **Format**: PNG with transparency support
- **Size**: Varies by visualization type and data complexity

## Customization Options

### Treemap Parameters
```python
# In create_treemap_image function:
max_depth=2          # Maximum directory depth to display
min_size_mb=100      # Minimum directory size (MB) to include
```

### Pie Chart Parameters
```python
# In create_pie_chart function:
top_n=10             # Number of top directories to show
```

### Heatmap Parameters
```python
# In create_duplicate_heatmap function:
min_size_gb=0.1      # Minimum duplicate size (GB) to include
```

## Color Schemes

### Treemap Colors
- **Blue**: Small directories
- **Red**: Large directories
- **Gradient**: Smooth transition between sizes
- **Transparency**: 70% opacity for overlapping visibility

### Pie Chart Colors
- **Matplotlib Set3**: Colorblind-friendly palette
- **Contrast**: White text on colored backgrounds
- **Readability**: Bold fonts for percentages

### Heatmap Colors
- **Reds Colormap**: Intensity shows duplicate volume
- **Annotations**: Text color adapts to background
- **Clarity**: Grid lines for cell separation

## Performance Considerations

### Large Directories
- **Filtering**: Use `min_size_mb` to exclude small directories
- **Depth Limiting**: Use `max_depth` to limit complexity
- **Memory**: Treemap generation is memory-intensive for deep hierarchies

### Many Duplicates
- **Thresholds**: Use `min_size_gb` to filter small duplicates
- **Rendering**: Heatmap performance scales with duplicate count
- **Optimization**: Consider limiting comparison to top drives

## Troubleshooting

### Common Issues

#### ModuleNotFoundError: matplotlib
```bash
pip install matplotlib numpy
```

#### No treemap found for label
```bash
python manage_cache.py list
# Check available labels
```

#### Memory errors with large treemaps
```bash
# Reduce complexity
python visualize_cache_images.py treemap label --max-depth 1 --min-size-mb 500
```

#### Empty or corrupted images
```bash
# Check treemap file integrity
python -c "import json; json.load(open('~/.storage-wizard/treemaps/label.json'))"
```

### Performance Tips

1. **Filter Data**: Use size thresholds to reduce complexity
2. **Limit Depth**: Shallow treemaps render faster
3. **Batch Processing**: Process multiple labels sequentially
4. **Output Size**: Consider image dimensions for large datasets

## Integration with Other Tools

### Combine with Text Analysis
```bash
# Generate both text and image visualizations
python visualize_cached_data.py duplicates 0.1 > duplicate_report.txt
python visualize_cache_images.py heatmap 0.1 duplicate_heatmap.png
```

### Automated Reporting
```bash
#!/bin/bash
# Generate complete visualization package
label="mediabig"

# Text reports
python visualize_cached_data.py tree $label > ${label}_tree.txt
python visualize_cached_data.py duplicates 0.1 > ${label}_duplicates.txt

# Image visualizations
python visualize_cache_images.py treemap $label ${label}_treemap.png
python visualize_cache_images.py pie $label ${label}_pie.png

echo "Visualization package generated for $label"
```

## Best Practices

### Data Preparation
1. **Clean Cache**: Remove old versions before analysis
2. **Size Filtering**: Exclude very small directories for clarity
3. **Label Selection**: Choose meaningful labels for comparison

### Visualization Selection
1. **Treemap**: Best for hierarchical size analysis
2. **Pie Chart**: Best for top-level distribution
3. **Bar Chart**: Best for comparing multiple drives
4. **Heatmap**: Best for duplicate analysis

### Output Management
1. **Consistent Naming**: Use predictable file naming
2. **Organized Storage**: Keep visualizations in dedicated folders
3. **Documentation**: Label visualizations with date and context

## Examples and Templates

### Complete Analysis Workflow
```bash
#!/bin/bash
# Complete storage analysis with visualizations

# 1. List available caches
echo "Available treemaps:"
python manage_cache.py list

# 2. Generate comprehensive analysis
labels="brian,mediabig,nvme1"

# Text analysis
python visualize_cached_data.py compare $labels > comparison_report.txt
python visualize_cached_data.py duplicates 0.1 > duplicate_analysis.txt

# Image visualizations
python visualize_cache_images.py compare $labels drive_comparison.png
python visualize_cache_images.py heatmap 0.1 duplicate_heatmap.png

# Individual drive visualizations
for label in ${labels//,/ }; do
    python visualize_cache_images.py treemap $label ${label}_treemap.png
    python visualize_cache_images.py pie $label ${label}_pie.png
done

echo "Analysis complete. Check generated files."
```

### Monthly Storage Report
```bash
#!/bin/bash
# Monthly storage analysis automation

date=$(date +%Y-%m)
report_dir="storage_report_$date"
mkdir -p $report_dir

# Generate all visualizations
python visualize_cache_images.py compare brian,mediabig,nvme1 $report_dir/monthly_comparison.png
python visualize_cache_images.py heatmap 0.5 $report_dir/duplicate_analysis.png

# Text summaries
python visualize_cached_data.py list > $report_dir/cache_status.txt
python visualize_cached_data.py duplicates 1.0 > $report_dir/large_duplicates.txt

echo "Monthly report generated in $report_dir"
```

---

**This image visualization system provides comprehensive graphical analysis capabilities that complement the existing text-based tools, enabling rich visual insights into storage patterns and duplicate distributions.**
