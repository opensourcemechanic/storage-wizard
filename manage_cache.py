#!/usr/bin/env python3
"""
Manage cached treemap files - list, remove, clean up.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

STORE_DIR = Path.home() / ".storage-wizard" / "treemaps"

def format_size(bytes_val):
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def list_cache():
    """List all cached treemaps with detailed info."""
    if not STORE_DIR.exists():
        print("No cached treemaps found.")
        return
    
    print("=== CACHED TREEMAPS ===")
    print(f"{'Label':>12} {'Size':>10} {'Files':>8} {'File Size':>10} {'Scanned':>19} {'Path'}")
    print("-" * 90)
    
    total_cache_size = 0
    for file in sorted(STORE_DIR.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            label = file.stem
            file_size = file.stat().st_size
            total_cache_size += file_size
            
            tree_size = data['tree'].get('size', 0)
            file_count = data['tree'].get('file_count', 0)
            scanned = data['scanned_at'][:19]
            path = data['root_path']
            
            print(f"{label:>12} {format_size(tree_size):>10} {file_count:>8,} {format_size(file_size):>10} {scanned:>19} {path}")
            
        except Exception as e:
            print(f"{file.stem:>12} ERROR: {e}")
    
    print("-" * 90)
    print(f"Total cache size: {format_size(total_cache_size)}")

def remove_label(label):
    """Remove a specific label from cache."""
    cache_file = STORE_DIR / f"{label}.json"
    
    if not cache_file.exists():
        print(f"Label '{label}' not found in cache.")
        return False
    
    try:
        # Get info before deletion
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        size = data['tree'].get('size', 0)
        files = data['tree'].get('file_count', 0)
        file_size = cache_file.stat().st_size
        
        # Delete the file
        cache_file.unlink()
        
        print(f"✓ Removed label '{label}' from cache")
        print(f"  - Directory: {data['root_path']}")
        print(f"  - Size: {format_size(size)} ({files:,} files)")
        print(f"  - Cache file: {format_size(file_size)}")
        return True
        
    except Exception as e:
        print(f"Error removing label '{label}': {e}")
        return False

def remove_multiple_labels(labels):
    """Remove multiple labels from cache."""
    removed = 0
    failed = 0
    
    for label in labels:
        if remove_label(label):
            removed += 1
        else:
            failed += 1
        print()
    
    print(f"Summary: {removed} removed, {failed} failed")

def clean_old_labels(days_old=30):
    """Remove labels older than specified days."""
    if not STORE_DIR.exists():
        print("No cached treemaps found.")
        return
    
    cutoff_date = datetime.now().timestamp() - (days_old * 24 * 3600)
    removed_count = 0
    total_size_freed = 0
    
    print(f"Removing labels older than {days_old} days...")
    print()
    
    for file in STORE_DIR.glob("*.json"):
        try:
            file_mtime = file.stat().st_mtime
            
            if file_mtime < cutoff_date:
                # Get info before deletion
                data = json.loads(file.read_text(encoding="utf-8"))
                label = file.stem
                file_size = file.stat().st_size
                
                # Delete the file
                file.unlink()
                
                removed_count += 1
                total_size_freed += file_size
                
                print(f"✓ Removed {label} (scanned {data['scanned_at'][:10]})")
                
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    print()
    print(f"Cleaned up {removed_count} old labels")
    print(f"Freed {format_size(total_size_freed)} of cache space")

def clear_cache():
    """Clear all cached treemaps."""
    if not STORE_DIR.exists():
        print("No cached treemaps found.")
        return
    
    print("⚠️  WARNING: This will remove ALL cached treemaps!")
    print("Type 'yes' to confirm: ", end="")
    
    if input().lower() != 'yes':
        print("Cancelled.")
        return
    
    removed_count = 0
    total_size_freed = 0
    
    for file in STORE_DIR.glob("*.json"):
        try:
            file_size = file.stat().st_size
            file.unlink()
            removed_count += 1
            total_size_freed += file_size
        except Exception as e:
            print(f"Error removing {file}: {e}")
    
    print(f"✓ Cleared {removed_count} cached treemaps")
    print(f"✓ Freed {format_size(total_size_freed)} of cache space")

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_cache.py <command> [args]")
        print()
        print("Commands:")
        print("  list                     - List all cached treemaps")
        print("  remove <label>           - Remove specific label")
        print("  remove <label1,label2>   - Remove multiple labels")
        print("  clean [days]              - Remove labels older than N days (default: 30)")
        print("  clear                    - Clear ALL cached treemaps")
        print()
        print("Examples:")
        print("  python manage_cache.py list")
        print("  python manage_cache.py remove cygwin")
        print("  python manage_cache.py remove cygwin,home,etc")
        print("  python manage_cache.py clean 7")
        print("  python manage_cache.py clear")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_cache()
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: python manage_cache.py remove <label>")
            return
        
        labels = [l.strip() for l in sys.argv[2].split(",")]
        if len(labels) == 1:
            remove_label(labels[0])
        else:
            remove_multiple_labels(labels)
    
    elif command == "clean":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        clean_old_labels(days)
    
    elif command == "clear":
        clear_cache()
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
