#!/usr/bin/env python3
"""
Search scan cache for large duplicate directories across all saved treemaps.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

STORE_DIR = Path.home() / ".storage-wizard" / "treemaps"

def format_size(bytes_val):
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def load_all_treemaps():
    """Load all saved treemaps."""
    treemaps = {}
    
    if not STORE_DIR.exists():
        print("No saved treemaps found.")
        return treemaps
    
    for file in STORE_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            label = file.stem
            treemaps[label] = data
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    return treemaps

def collect_all_hashes(treemaps):
    """Collect all hashes across all treemaps with size info."""
    hash_info = defaultdict(list)
    
    for label, data in treemaps.items():
        tree = data['tree']
        
        def walk_tree(node, path=""):
            """Recursively walk the tree and collect hashes with sizes."""
            current_path = f"{path}/{node['name']}" if path else node['name']
            
            hash_info[node['hash']].append({
                'label': label,
                'path': current_path,
                'size': node.get('size', 0),
                'files': node.get('file_count', 0),
                'scanned_at': data['scanned_at']
            })
            
            if 'children' in node:
                for child in node['children']:
                    walk_tree(child, current_path)
        
        walk_tree(tree)
    
    return hash_info

def find_large_duplicates(hash_info, min_size_gb=1.0):
    """Find duplicate directories larger than min_size_gb."""
    duplicates = {}
    
    for hash_val, entries in hash_info.items():
        if len(entries) > 1:  # Has duplicates
            # Calculate total size of all duplicates
            total_size = sum(entry['size'] for entry in entries)
            
            # Get the size of the largest duplicate
            max_size = max(entry['size'] for entry in entries)
            
            if max_size >= (min_size_gb * 1024**3):  # Convert GB to bytes
                duplicates[hash_val] = {
                    'entries': entries,
                    'total_size': total_size,
                    'max_size': max_size,
                    'count': len(entries)
                }
    
    return duplicates

def analyze_duplicates(duplicates):
    """Analyze and report on duplicate directories."""
    if not duplicates:
        print("No large duplicate directories found.")
        return
    
    # Sort by total size (largest waste first)
    sorted_duplicates = sorted(
        duplicates.items(),
        key=lambda x: x[1]['total_size'],
        reverse=True
    )
    
    print("=== LARGE DUPLICATE DIRECTORIES ===")
    print(f"Found {len(sorted_duplicates)} duplicate groups with directories ≥1GB")
    print()
    
    total_waste = 0
    for i, (hash_val, info) in enumerate(sorted_duplicates, 1):
        entries = info['entries']
        total_size = info['total_size']
        max_size = info['max_size']
        count = info['count']
        
        # Calculate waste (total - keep one copy)
        waste = total_size - max_size
        total_waste += waste
        
        print(f"{i}. Hash: {hash_val[:16]}...")
        print(f"   Size: {format_size(max_size)} each × {count} copies = {format_size(total_size)} total")
        print(f"   Waste: {format_size(waste)} (could delete {count-1} copies)")
        print()
        
        # Group by treemap for cleaner display
        by_label = defaultdict(list)
        for entry in entries:
            by_label[entry['label']].append(entry)
        
        for label, label_entries in by_label.items():
            print(f"   {label}:")
            for entry in sorted(label_entries, key=lambda x: x['size'], reverse=True):
                size_str = format_size(entry['size'])
                files_str = f"{entry['files']:,} files"
                print(f"     - {size_str:>8} {files_str:>12} {entry['path']}")
        print()
        
        if i >= 10:  # Limit output to top 10
            remaining = len(sorted_duplicates) - 10
            if remaining > 0:
                print(f"... and {remaining} more duplicate groups")
            break
    
    print(f"=== SUMMARY ===")
    print(f"Total potential space savings: {format_size(total_waste)}")
    print(f"Duplicate groups analyzed: {len(sorted_duplicates)}")

def find_cross_treemap_duplicates(hash_info):
    """Find duplicates that appear across different treemaps (different drives)."""
    cross_duplicates = {}
    
    for hash_val, entries in hash_info.items():
        if len(entries) > 1:
            # Check if entries are from different treemaps
            labels = set(entry['label'] for entry in entries)
            if len(labels) > 1:  # Cross-treemap duplicates
                cross_duplicates[hash_val] = entries
    
    return cross_duplicates

def main():
    if len(sys.argv) > 1:
        try:
            min_size_gb = float(sys.argv[1])
        except ValueError:
            print("Usage: python find_large_duplicates.py [min_size_gb]")
            print("Example: python find_large_duplicates.py 0.5  # Find duplicates ≥500MB")
            return
    else:
        min_size_gb = 1.0  # Default to 1GB
    
    print("Loading all saved treemaps...")
    treemaps = load_all_treemaps()
    print(f"Loaded {len(treemaps)} treemaps")
    print()
    
    if not treemaps:
        return
    
    print("Collecting hash information...")
    hash_info = collect_all_hashes(treemaps)
    print(f"Found {len(hash_info)} unique directory hashes")
    print()
    
    print(f"Finding duplicates ≥{min_size_gb}GB...")
    duplicates = find_large_duplicates(hash_info, min_size_gb)
    analyze_duplicates(duplicates)
    
    print()
    print("=== CROSS-TREEMAP DUPLICATES ===")
    cross_duplicates = find_cross_treemap_duplicates(hash_info)
    
    if cross_duplicates:
        print(f"Found {len(cross_duplicates)} duplicate groups across different drives:")
        for hash_val, entries in list(cross_duplicates.items())[:5]:  # Show top 5
            labels = [entry['label'] for entry in entries]
            size = format_size(entries[0]['size'])
            print(f"  {size} {hash_val[:16]}... in {', '.join(labels)}")
    else:
        print("No duplicates found across different drives.")

if __name__ == "__main__":
    main()
