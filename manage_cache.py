#!/usr/bin/env python3
"""
Manage cached treemap files - list, remove, clean up.
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

def list_cache():
    """List all cached treemaps with detailed info."""
    if not STORE_DIR.exists():
        print("No cached treemaps found.")
        return
    
    print("=== CACHED TREEMAPS ===")
    print(f"{'Label':>12} {'Versions':>8} {'Size':>10} {'Files':>8} {'File Size':>10} {'Latest Scan':>19} {'Path'}")
    print("-" * 110)
    
    total_cache_size = 0
    # Group files by label
    label_groups = defaultdict(list)
    
    for file in sorted(STORE_DIR.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            label = data['label']
            label_groups[label].append((file, data))
        except Exception as e:
            print(f"{file.stem:>12} ERROR: {e}")
    
    for label in sorted(label_groups.keys()):
        files = label_groups[label]
        # Sort by timestamp (newest first)
        files.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
        
        # Get latest version
        latest_file, latest_data = files[0]
        file_size = latest_file.stat().st_size
        total_cache_size += file_size
        
        tree_size = latest_data['tree'].get('size', 0)
        file_count = latest_data['tree'].get('file_count', 0)
        scanned = latest_data['scanned_at'][:19]
        path = latest_data['root_path']
        
        version_count = len(files)
        
        print(f"{label:>12} {version_count:>8} {format_size(tree_size):>10} {file_count:>8,} {format_size(file_size):>10} {scanned:>19} {path}")
        
        # Show versions if more than 1
        if version_count > 1:
            for i, (file, data) in enumerate(files[1:3], 1):  # Show next 2 versions
                file_scanned = data['scanned_at'][:19]
                print(f"{'':>12} {'v'+str(i+1):>8} {'':>10} {'':>8} {format_size(file.stat().st_size):>10} {file_scanned:>19} {file.name}")
            if version_count > 3:
                print(f"{'':>12} {'+{} more'.format(version_count-3):>8}")
    
    print("-" * 110)
    print(f"Total cache size: {format_size(total_cache_size)}")

def remove_label(label):
    """Remove a specific label and all its versions from cache."""
    import sys
    from storage_wizard.treemap import get_existing_treemap_versions
    
    # Check for versioned files
    versions = get_existing_treemap_versions(label)
    main_file = STORE_DIR / f"{label}.json"
    
    files_to_remove = []
    
    if main_file.exists():
        files_to_remove.append(main_file)
    
    for timestamp, version_file in versions:
        files_to_remove.append(version_file)
    
    if not files_to_remove:
        print(f"Label '{label}' not found in cache.")
        return False
    
    # Show what will be removed
    total_size = 0
    print(f"Files to remove for label '{label}':")
    for file in files_to_remove:
        size = file.stat().st_size
        total_size += size
        if file == main_file:
            print(f"  - {file.name} (main version)")
        else:
            timestamp_str = file.stem.split("_")[-2:]  # Get timestamp part
            print(f"  - {file.name} (version {'_'.join(timestamp_str)})")
    
    print(f"Total space to be freed: {format_size(total_size)}")
    
    # Confirm removal
    print(f"\n⚠️  This will remove {len(files_to_remove)} file(s) for label '{label}'")
    print("Type 'yes' to confirm: ", end="")
    
    if input().lower() != 'yes':
        print("Cancelled.")
        return False
    
    # Remove files
    removed_count = 0
    for file in files_to_remove:
        try:
            file.unlink()
            removed_count += 1
        except Exception as e:
            print(f"Error removing {file}: {e}")
    
    print(f"✓ Removed {removed_count} files for label '{label}'")
    print(f"✓ Freed {format_size(total_size)} of cache space")
    return True

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
