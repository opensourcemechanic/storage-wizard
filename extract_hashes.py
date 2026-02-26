#!/usr/bin/env python3
"""
Extract full hash data from saved treemaps.
Usage: python extract_hashes.py [label]
If no label provided, shows all saved treemaps and extracts hashes from the largest one.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

STORE_DIR = Path.home() / ".storage-wizard" / "treemaps"

def extract_hashes(label):
    """Extract all hashes from a saved treemap."""
    treemap_file = STORE_DIR / f"{label}.json"
    
    if not treemap_file.exists():
        print(f"No treemap found for label: {label}")
        return
    
    print(f"Loading treemap: {label}")
    print(f"File: {treemap_file}")
    print(f"Size: {treemap_file.stat().st_size:,} bytes")
    print()
    
    # Load the treemap data
    data = json.loads(treemap_file.read_text(encoding="utf-8"))
    
    # Extract metadata
    print("=== METADATA ===")
    print(f"Label: {data['label']}")
    print(f"Root Path: {data['root_path']}")
    print(f"Scanned At: {data['scanned_at']}")
    print(f"Mode: {'slow (SHA-256)' if data['slow'] else 'fast (metadata)'}")
    print()
    
    # Extract all hashes from the tree
    hash_map = defaultdict(list)
    
    def walk_tree(node, path=""):
        """Recursively walk the tree and collect hashes."""
        current_path = f"{path}/{node['name']}" if path else node['name']
        hash_map[node['hash']].append(current_path)
        
        if 'children' in node:
            for child in node['children']:
                walk_tree(child, current_path)
    
    # Start from root
    tree = data['tree']
    walk_tree(tree)
    
    print("=== HASH STATISTICS ===")
    print(f"Total unique hashes: {len(hash_map)}")
    print(f"Total directories: {sum(len(paths) for paths in hash_map.values())}")
    print()
    
    # Find duplicates (hashes with >1 paths)
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    
    print("=== DUPLICATE DIRECTORIES ===")
    if duplicates:
        print(f"Found {len(duplicates)} duplicate hash groups:")
        for i, (hash_val, paths) in enumerate(duplicates.items(), 1):
            print(f"\n{i}. Hash: {hash_val[:16]}... ({len(paths)} copies)")
            for path in paths[:5]:  # Show first 5 paths
                print(f"   - {path}")
            if len(paths) > 5:
                print(f"   ... and {len(paths) - 5} more")
    else:
        print("No duplicate directories found.")
    
    print()
    
    # Show empty directories
    empty_hash = "cad5f7fd8c1539fd1d7a2ab6a8a3d3ed9b8c3b5c7d9e1f2a3b4c5d6e7f8a9b0c1d"
    if empty_hash in hash_map:
        print("=== EMPTY DIRECTORIES ===")
        print(f"Found {len(hash_map[empty_hash])} empty directories:")
        for path in hash_map[empty_hash][:10]:  # Show first 10
            print(f"   - {path}")
        if len(hash_map[empty_hash]) > 10:
            print(f"   ... and {len(hash_map[empty_hash]) - 10} more")
    
    print()
    
    # Show largest directories by size
    def get_size(node):
        """Recursively calculate size."""
        total = node.get('size', 0)
        if 'children' in node:
            for child in node['children']:
                total += get_size(child)
        return total
    
    def collect_sizes(node, path="", sizes=None):
        """Collect sizes for all directories."""
        if sizes is None:
            sizes = []
        
        current_path = f"{path}/{node['name']}" if path else node['name']
        size = get_size(node)
        file_count = node.get('file_count', 0)
        sizes.append((current_path, size, file_count, node['hash'][:8]))
        
        if 'children' in node:
            for child in node['children']:
                collect_sizes(child, current_path, sizes)
        
        return sizes
    
    all_sizes = collect_sizes(tree)
    all_sizes.sort(key=lambda x: x[1], reverse=True)
    
    print("=== LARGEST DIRECTORIES ===")
    for path, size, file_count, hash_val in all_sizes[:10]:
        size_str = format_size(size)
        print(f"{size_str:>10} {file_count:>6} files {hash_val} {path}")
    
    return hash_map, duplicates

def format_size(bytes_val):
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def list_treemaps():
    """List all saved treemaps."""
    if not STORE_DIR.exists():
        print("No saved treemaps found.")
        return []
    
    treemaps = []
    for file in STORE_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            size = file.stat().st_size
            treemaps.append({
                'label': data['label'],
                'file': file.name,
                'size': size,
                'scanned_at': data['scanned_at'],
                'root_path': data['root_path']
            })
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    treemaps.sort(key=lambda x: x['scanned_at'], reverse=True)
    
    print("=== SAVED TREEMAPS ===")
    for tm in treemaps:
        print(f"{tm['label']:>12} {tm['size']:>8} bytes {tm['scanned_at'][:19]} {tm['root_path']}")
    
    return treemaps

if __name__ == "__main__":
    if len(sys.argv) > 1:
        label = sys.argv[1]
        extract_hashes(label)
    else:
        treemaps = list_treemaps()
        if treemaps:
            print(f"\nExtracting hashes from largest treemap: {treemaps[0]['label']}")
            extract_hashes(treemaps[0]['label'])
