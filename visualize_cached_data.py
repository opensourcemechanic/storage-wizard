#!/usr/bin/env python3
"""
Visualize directories and duplicates from cached treemap data.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

STORE_DIR = Path.home() / ".storage-wizard" / "treemaps"

def format_size(bytes_val):
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def list_cached_treemaps():
    """List all cached treemaps with basic info."""
    if not STORE_DIR.exists():
        print("No cached treemaps found.")
        return []
    
    treemaps = []
    for file in STORE_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            size = file.stat().st_size
            treemaps.append({
                'label': file.stem,
                'file': file.name,
                'size': size,
                'scanned_at': data['scanned_at'],
                'root_path': data['root_path'],
                'total_size': data['tree'].get('size', 0),
                'total_files': data['tree'].get('file_count', 0)
            })
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    treemaps.sort(key=lambda x: x['scanned_at'], reverse=True)
    
    print("=== CACHED TREEMAPS ===")
    for tm in treemaps:
        print(f"{tm['label']:>12} {format_size(tm['total_size']):>10} {tm['total_files']:>8,} files {tm['scanned_at'][:19]} {tm['root_path']}")
    
    return treemaps

def visualize_directory_tree(label, max_depth=3, min_size_mb=100):
    """Visualize directory structure from cached treemap."""
    treemap_file = STORE_DIR / f"{label}.json"
    
    if not treemap_file.exists():
        print(f"No treemap found for label: {label}")
        return
    
    data = json.loads(treemap_file.read_text(encoding="utf-8"))
    tree = data['tree']
    
    print(f"\n=== DIRECTORY TREE: {label.upper()} ===")
    print(f"Root: {data['root_path']}")
    print(f"Scanned: {data['scanned_at'][:19]}")
    print(f"Mode: {'SHA-256 content' if data['slow'] else 'metadata'}")
    print(f"Total: {format_size(tree.get('size', 0))} in {tree.get('file_count', 0):,} files")
    print()
    
    def print_tree(node, depth=0, prefix="", is_last=True):
        """Recursively print directory tree."""
        if depth > max_depth:
            return
        
        size = node.get('size', 0)
        files = node.get('file_count', 0)
        name = node['name']
        
        # Skip small directories unless they're at root level
        if depth > 0 and size < min_size_mb * 1024 * 1024:
            return
        
        # Tree formatting
        connector = "└── " if is_last else "├── "
        indent = "    " * depth
        
        size_str = format_size(size)
        files_str = f"{files:,} files"
        
        print(f"{prefix}{indent}{connector}{name}/ [{size_str}, {files_str}]")
        
        # Sort children by size (largest first)
        children = node.get('children', [])
        children.sort(key=lambda x: x.get('size', 0), reverse=True)
        
        for i, child in enumerate(children):
            is_child_last = (i == len(children) - 1)
            child_prefix = prefix + indent + ("    " if is_last else "│   ")
            print_tree(child, depth + 1, child_prefix, is_child_last)
    
    print_tree(tree)

def visualize_file_types(label, top_n=20):
    """Visualize file type distribution from cached treemap."""
    treemap_file = STORE_DIR / f"{label}.json"
    
    if not treemap_file.exists():
        print(f"No treemap found for label: {label}")
        return
    
    data = json.loads(treemap_file.read_text(encoding="utf-8"))
    tree = data['tree']
    
    print(f"\n=== FILE TYPE DISTRIBUTION: {label.upper()} ===")
    
    # Collect file extensions
    extensions = Counter()
    total_files = 0
    
    def collect_extensions(node):
        """Recursively collect file extensions."""
        nonlocal total_files
        
        if 'children' in node:
            for child in node['children']:
                collect_extensions(child)
        else:
            # This is a file (leaf node)
            total_files += 1
            ext = Path(node['name']).suffix.lower()
            if ext:
                extensions[ext] += 1
            else:
                extensions['(no extension)'] += 1
    
    # Note: This is a simplified version - treemap stores directories, not individual files
    # For full file type analysis, you'd need to scan the original directory
    
    print(f"Note: File type analysis requires original directory scanning")
    print(f"Total files in tree: {tree.get('file_count', 0):,}")
    print(f"Use 'storage-wizard scan' for detailed file type analysis")

def visualize_duplicates_across_treemaps(min_size_gb=0.1):
    """Visualize duplicates across all cached treemaps."""
    print(f"\n=== DUPLICATES ACROSS ALL TREEMAPS (≥{min_size_gb}GB) ===")
    
    # Collect all hashes
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
                    'size': node.get('size', 0),
                    'files': node.get('file_count', 0)
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
                total_size = sum(e['size'] for e in entries)
                waste = total_size - max_size
                duplicates.append((waste, hash_val, entries))
    
    duplicates.sort(reverse=True)
    
    if not duplicates:
        print(f"No duplicates found ≥{min_size_gb}GB")
        return
    
    print(f"Found {len(duplicates)} duplicate groups")
    total_waste = sum(w for w, _, _ in duplicates)
    print(f"Total potential savings: {format_size(total_waste)}")
    print()
    
    # Show top duplicates
    for i, (waste, hash_val, entries) in enumerate(duplicates[:10], 1):
        waste_gb = waste / 1024**3
        max_size_gb = max(e['size'] for e in entries) / 1024**3
        
        print(f"{i}. {waste_gb:.2f}GB waste - {max_size_gb:.2f}GB × {len(entries)} copies")
        print()
        
        # Group by treemap with clear labels
        by_label = defaultdict(list)
        for entry in entries:
            by_label[entry['label']].append(entry)
        
        for label, label_entries in sorted(by_label.items()):
            print(f"   📁 {label.upper()} DRIVE:")
            for entry in label_entries:
                size_str = format_size(entry['size'])
                files_str = f"{entry['files']:,} files"
                print(f"      {size_str:>10} {files_str:>15} {entry['path']}")
        print()

def visualize_treemap_comparison(labels):
    """Compare multiple treemaps side by side."""
    print(f"\n=== TREEMAP COMPARISON ===")
    
    treemaps = {}
    for label in labels:
        treemap_file = STORE_DIR / f"{label}.json"
        if treemap_file.exists():
            data = json.loads(treemap_file.read_text(encoding="utf-8"))
            treemaps[label] = data
    
    if not treemaps:
        print("No valid treemaps found for comparison")
        return
    
    # Comparison table
    print(f"{'Label':>12} {'Size':>10} {'Files':>8} {'Scanned':>19} {'Path':>20}")
    print("-" * 80)
    
    for label, data in treemaps.items():
        tree = data['tree']
        size = format_size(tree.get('size', 0))
        files = f"{tree.get('file_count', 0):,}"
        scanned = data['scanned_at'][:19]
        path = data['root_path'][-20:]
        print(f"{label:>12} {size:>10} {files:>8} {scanned:>19} {path:>20}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize_cached_data.py <command> [args]")
        print()
        print("Commands:")
        print("  list                    - List all cached treemaps")
        print("  tree <label> [depth]    - Show directory tree")
        print("  types <label>           - Show file type distribution")
        print("  duplicates [size_gb]    - Show duplicates across all treemaps")
        print("  compare <label1,label2> - Compare multiple treemaps")
        print()
        print("Examples:")
        print("  python visualize_cached_data.py list")
        print("  python visualize_cached_data.py tree brian 2")
        print("  python visualize_cached_data.py duplicates 0.5")
        print("  python visualize_cached_data.py compare brian,mediabig")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_cached_treemaps()
    
    elif command == "tree":
        if len(sys.argv) < 3:
            print("Usage: python visualize_cached_data.py tree <label> [max_depth]")
            return
        label = sys.argv[2]
        max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        visualize_directory_tree(label, max_depth)
    
    elif command == "types":
        if len(sys.argv) < 3:
            print("Usage: python visualize_cached_data.py types <label>")
            return
        label = sys.argv[2]
        visualize_file_types(label)
    
    elif command == "duplicates":
        min_size = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
        visualize_duplicates_across_treemaps(min_size)
    
    elif command == "compare":
        if len(sys.argv) < 3:
            print("Usage: python visualize_cached_data.py compare <label1,label2,...>")
            return
        labels = [l.strip() for l in sys.argv[2].split(",")]
        visualize_treemap_comparison(labels)
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
