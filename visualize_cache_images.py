#!/usr/bin/env python3
"""
Generate image visualizations from cached treemap data.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np

STORE_DIR = Path.home() / ".storage-wizard" / "treemaps"

def format_size(bytes_val):
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def get_color_for_size(size_bytes, max_size):
    """Get color based on size (gradient from blue to red)."""
    if max_size == 0:
        return 'lightblue'
    
    ratio = size_bytes / max_size
    # Blue to red gradient
    red = ratio
    blue = 1 - ratio
    return (red, 0, blue, 0.7)  # RGBA with transparency

def create_treemap_image(label, output_file=None, max_depth=2, min_size_mb=100):
    """Create a treemap visualization image."""
    treemap_file = STORE_DIR / f"{label}.json"
    
    if not treemap_file.exists():
        print(f"No treemap found for label: {label}")
        return False
    
    data = json.loads(treemap_file.read_text(encoding="utf-8"))
    tree = data['tree']
    
    if not output_file:
        output_file = f"{label}_treemap.png"
    
    # Collect directories for visualization
    directories = []
    
    def collect_directories(node, depth=0):
        if depth > max_depth:
            return
        
        size = node.get('size', 0)
        if depth == 0 or size >= min_size_mb * 1024 * 1024:
            directories.append({
                'name': node['name'],
                'size': size,
                'files': node.get('file_count', 0),
                'depth': depth,
                'path': node.get('path', node['name'])
            })
        
        if 'children' in node:
            for child in sorted(node['children'], key=lambda x: x.get('size', 0), reverse=True):
                collect_directories(child, depth + 1)
    
    collect_directories(tree)
    
    if not directories:
        print("No directories meet size criteria")
        return False
    
    # Create treemap layout
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    fig.suptitle(f'Treemap Visualization: {label.upper()}\n{data["root_path"]}', fontsize=14, fontweight='bold')
    
    # Simple squarified treemap algorithm
    def squarify(items, x, y, width, height):
        if not items:
            return
        
        if len(items) == 1:
            item = items[0]
            color = get_color_for_size(item['size'], directories[0]['size'])
            rect = Rectangle((x, y), width, height, 
                           facecolor=color, edgecolor='white', linewidth=1)
            ax.add_patch(rect)
            
            # Add text label
            if width > 50 and height > 20:  # Only add text if rectangle is big enough
                text = item['name']
                if len(text) > 15:
                    text = text[:12] + '...'
                ax.text(x + width/2, y + height/2, text, 
                       ha='center', va='center', fontsize=8, fontweight='bold')
                size_text = format_size(item['size'])
                ax.text(x + width/2, y + height/2 - 10, size_text, 
                       ha='center', va='center', fontsize=7)
            return
        
        # Split items into two rows
        total_size = sum(item['size'] for item in items)
        mid = len(items) // 2
        
        # First row
        row1_size = sum(item['size'] for item in items[:mid])
        row1_height = height * (row1_size / total_size)
        squarify(items[:mid], x, y, width, row1_height)
        
        # Second row
        row2_size = sum(item['size'] for item in items[mid:])
        row2_height = height * (row2_size / total_size)
        squarify(items[mid:], x, y + row1_height, width, row2_height)
    
    # Generate treemap
    squarify(directories[1:], 0, 0, 100, 100)  # Skip root directory
    
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Add legend
    legend_elements = [
        patches.Patch(color='red', alpha=0.7, label='Large directories'),
        patches.Patch(color='blue', alpha=0.7, label='Small directories')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Treemap image saved: {output_file}")
    return True

def create_pie_chart(label, output_file=None, top_n=10):
    """Create a pie chart of directory sizes."""
    treemap_file = STORE_DIR / f"{label}.json"
    
    if not treemap_file.exists():
        print(f"No treemap found for label: {label}")
        return False
    
    data = json.loads(treemap_file.read_text(encoding="utf-8"))
    tree = data['tree']
    
    if not output_file:
        output_file = f"{label}_pie_chart.png"
    
    # Collect top directories
    directories = []
    
    def collect_directories(node):
        if 'children' in node:
            for child in node['children']:
                directories.append({
                    'name': child['name'],
                    'size': child.get('size', 0),
                    'files': child.get('file_count', 0)
                })
                collect_directories(child)
    
    collect_directories(tree)
    
    # Sort by size and take top N
    directories.sort(key=lambda x: x['size'], reverse=True)
    top_dirs = directories[:top_n]
    
    if not top_dirs:
        print("No directories found")
        return False
    
    # Create pie chart
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    fig.suptitle(f'Directory Size Distribution: {label.upper()}\nTop {top_n} Directories', 
                 fontsize=14, fontweight='bold')
    
    sizes = [d['size'] for d in top_dirs]
    labels = [f"{d['name']}\n{format_size(d['size'])}" for d in top_dirs]
    
    # Generate colors
    colors = plt.cm.Set3(np.linspace(0, 1, len(top_dirs)))
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                      autopct='%1.1f%%', startangle=90)
    
    # Enhance text appearance
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(8)
    
    ax.axis('equal')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Pie chart saved: {output_file}")
    return True

def create_bar_chart(labels, output_file=None):
    """Create a bar chart comparing multiple treemaps."""
    if not output_file:
        output_file = "treemap_comparison.png"
    
    # Load treemap data
    treemaps = {}
    for label in labels:
        treemap_file = STORE_DIR / f"{label}.json"
        if treemap_file.exists():
            data = json.loads(treemap_file.read_text(encoding="utf-8"))
            treemaps[label] = data
    
    if not treemaps:
        print("No valid treemaps found")
        return False
    
    # Create comparison chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle('Treemap Comparison', fontsize=16, fontweight='bold')
    
    # Size comparison
    sizes = [data['tree'].get('size', 0) for data in treemaps.values()]
    size_labels = [format_size(s) for s in sizes]
    
    bars1 = ax1.bar(treemaps.keys(), sizes, color='skyblue', edgecolor='navy')
    ax1.set_title('Total Size by Drive')
    ax1.set_ylabel('Size (bytes)')
    ax1.tick_params(axis='x', rotation=45)
    
    # Add value labels on bars
    for bar, label in zip(bars1, size_labels):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                label, ha='center', va='bottom', fontweight='bold')
    
    # File count comparison
    file_counts = [data['tree'].get('file_count', 0) for data in treemaps.values()]
    
    bars2 = ax2.bar(treemaps.keys(), file_counts, color='lightcoral', edgecolor='darkred')
    ax2.set_title('File Count by Drive')
    ax2.set_ylabel('Number of Files')
    ax2.tick_params(axis='x', rotation=45)
    
    # Add value labels on bars
    for bar, count in zip(bars2, file_counts):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f"{count:,}", ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Comparison chart saved: {output_file}")
    return True

def create_duplicate_heatmap(min_size_gb=0.1, output_file=None):
    """Create a heatmap of duplicate sizes across drives."""
    if not output_file:
        output_file = "duplicate_heatmap.png"
    
    # Collect duplicate data
    hash_info = defaultdict(list)
    
    for file in STORE_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            label = file.stem
            
            def walk_tree(node, path=""):
                current_path = f"{path}/{node['name']}" if path else node['name']
                hash_info[node['hash']].append({
                    'label': label,
                    'path': current_path,
                    'size': node.get('size', 0)
                })
                
                if 'children' in node:
                    for child in node['children']:
                        walk_tree(child, current_path)
            
            walk_tree(data['tree'])
            
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    # Find duplicates
    duplicates = []
    for hash_val, entries in hash_info.items():
        if len(entries) > 1:
            max_size = max(e['size'] for e in entries)
            if max_size >= min_size_gb * 1024**3:
                duplicates.append((hash_val, entries))
    
    if not duplicates:
        print("No duplicates found")
        return False
    
    # Create heatmap data
    drives = set()
    for _, entries in duplicates:
        for entry in entries:
            drives.add(entry['label'])
    
    drives = sorted(list(drives))
    matrix = np.zeros((len(drives), len(drives)))
    
    for _, entries in duplicates:
        for i, drive1 in enumerate(drives):
            for j, drive2 in enumerate(drives):
                if i != j:
                    # Check if these drives share duplicates
                    drive1_entries = [e for e in entries if e['label'] == drive1]
                    drive2_entries = [e for e in entries if e['label'] == drive2]
                    
                    if drive1_entries and drive2_entries:
                        matrix[i][j] += drive1_entries[0]['size'] / (1024**3)  # Convert to GB
    
    # Create heatmap
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    fig.suptitle(f'Duplicate Size Heatmap (≥{min_size_gb}GB)', fontsize=14, fontweight='bold')
    
    im = ax.imshow(matrix, cmap='Reds', aspect='auto')
    
    # Set labels
    ax.set_xticks(range(len(drives)))
    ax.set_yticks(range(len(drives)))
    ax.set_xticklabels(drives, rotation=45)
    ax.set_yticklabels(drives)
    
    # Add text annotations
    for i in range(len(drives)):
        for j in range(len(drives)):
            if matrix[i][j] > 0:
                text = f"{matrix[i][j]:.1f}GB"
                ax.text(j, i, text, ha='center', va='center', 
                       color='white' if matrix[i][j] > matrix.max()/2 else 'black')
    
    ax.set_xlabel('Drives')
    ax.set_ylabel('Drives')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Duplicate Size (GB)')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Duplicate heatmap saved: {output_file}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize_cache_images.py <command> [args]")
        print()
        print("Commands:")
        print("  treemap <label> [output]    - Create treemap visualization")
        print("  pie <label> [output]        - Create pie chart of directories")
        print("  compare <labels> [output]   - Compare multiple treemaps")
        print("  heatmap [size_gb] [output]  - Create duplicate heatmap")
        print()
        print("Examples:")
        print("  python visualize_cache_images.py treemap mediabig")
        print("  python visualize_cache_images.py pie brian brian_pie.png")
        print("  python visualize_cache_images.py compare brian,mediabig")
        print("  python visualize_cache_images.py heatmap 0.5")
        return
    
    command = sys.argv[1]
    
    if command == "treemap":
        if len(sys.argv) < 3:
            print("Usage: python visualize_cache_images.py treemap <label> [output_file]")
            return
        label = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else None
        create_treemap_image(label, output)
    
    elif command == "pie":
        if len(sys.argv) < 3:
            print("Usage: python visualize_cache_images.py pie <label> [output_file]")
            return
        label = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else None
        create_pie_chart(label, output)
    
    elif command == "compare":
        if len(sys.argv) < 3:
            print("Usage: python visualize_cache_images.py compare <label1,label2,...> [output_file]")
            return
        labels = [l.strip() for l in sys.argv[2].split(",")]
        output = sys.argv[3] if len(sys.argv) > 3 else None
        create_bar_chart(labels, output)
    
    elif command == "heatmap":
        min_size = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
        output = sys.argv[3] if len(sys.argv) > 3 else None
        create_duplicate_heatmap(min_size, output)
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
