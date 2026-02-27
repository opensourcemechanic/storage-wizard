"""
Fast metadata-only scanner for quick directory analysis.
Reads directory structure in memory without per-file stat calls.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class FastNode:
    """Lightweight node for fast scanning."""
    name: str
    path: str
    depth: int
    is_dir: bool
    children: List['FastNode'] = None
    parent: Optional['FastNode'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class FastScanner:
    """Ultra-fast directory scanner using minimal metadata."""
    
    def __init__(self, max_depth: Optional[int] = None, include_hidden: bool = False):
        self.max_depth = max_depth
        self.include_hidden = include_hidden
        self.start_time = time.time()
        self.nodes_scanned = 0
        self.errors = []
    
    def scan(self, path: str) -> FastNode:
        """Scan directory structure quickly."""
        root_path = Path(path)
        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        root = FastNode(root_path.name, str(root_path), 0, True)
        self._scan_recursive(root_path, root, 0)
        
        elapsed = time.time() - self.start_time
        print(f"Fast scan completed in {elapsed:.2f}s - {self.nodes_scanned:,} nodes")
        
        return root
    
    def _scan_recursive(self, path: Path, node: FastNode, depth: int):
        """Recursively scan directory structure."""
        if self.max_depth is not None and depth >= self.max_depth:
            return
        
        try:
            entries = list(os.scandir(path))
        except (PermissionError, OSError) as e:
            self.errors.append(f"Permission denied: {path}")
            return
        
        dirs = []
        files = []
        
        for entry in entries:
            self.nodes_scanned += 1
            
            # Skip hidden files if requested
            if not self.include_hidden and entry.name.startswith('.'):
                continue
            
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            
            child_node = FastNode(
                name=entry.name,
                path=entry.path,
                depth=depth + 1,
                is_dir=is_dir,
                parent=node
            )
            
            if is_dir:
                dirs.append(child_node)
                node.children.append(child_node)
            else:
                files.append(child_node)
                node.children.append(child_node)
        
        # Recurse into directories
        for dir_node in dirs:
            dir_path = Path(dir_node.path)
            self._scan_recursive(dir_path, dir_node, depth + 1)
    
    def get_stats(self, root: FastNode) -> Dict:
        """Get basic statistics from fast scan."""
        stats = {
            'total_nodes': 0,
            'total_dirs': 0,
            'total_files': 0,
            'max_depth': 0,
            'errors': len(self.errors),
            'scan_time': time.time() - self.start_time
        }
        
        def count_nodes(node: FastNode, depth: int = 0):
            stats['total_nodes'] += 1
            stats['max_depth'] = max(stats['max_depth'], depth)
            
            if node.is_dir:
                stats['total_dirs'] += 1
            else:
                stats['total_files'] += 1
            
            for child in node.children:
                count_nodes(child, depth + 1)
        
        count_nodes(root)
        return stats
    
    def find_largest_dirs(self, root: FastNode, top_n: int = 20) -> List[Tuple[FastNode, int]]:
        """Find directories with most children (proxy for size)."""
        dir_sizes = []
        
        def count_children(node: FastNode) -> int:
            count = 1  # Count the node itself
            for child in node.children:
                count += count_children(child)
            return count
        
        def collect_dirs(node: FastNode):
            if node.is_dir:
                size = count_children(node)
                dir_sizes.append((node, size))
            
            for child in node.children:
                collect_dirs(child)
        
        collect_dirs(root)
        dir_sizes.sort(key=lambda x: x[1], reverse=True)
        return dir_sizes[:top_n]
    
    def print_tree(self, root: FastNode, max_depth: Optional[int] = None):
        """Print directory tree structure."""
        def print_node(node: FastNode, prefix: str = "", is_last: bool = True, current_depth: int = 0):
            if max_depth is not None and current_depth > max_depth:
                return
            
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "
            
            if node.is_dir:
                print(f"{prefix}{connector}{node.name}/")
            else:
                print(f"{prefix}{connector}{node.name}")
            
            for i, child in enumerate(node.children):
                print_node(child, prefix + extension, i == len(node.children) - 1, current_depth + 1)
        
        print(root.name + "/")
        for child in root.children:
            print_node(child, is_last=(len(root.children) == 1))


def quick_scan(path: str, max_depth: Optional[int] = None, include_hidden: bool = False):
    """Quick scan function for immediate use."""
    scanner = FastScanner(max_depth=max_depth, include_hidden=include_hidden)
    root = scanner.scan(path)
    
    # Print basic stats
    stats = scanner.get_stats(root)
    print(f"\n📊 Quick Scan Results:")
    print(f"   Total nodes: {stats['total_nodes']:,}")
    print(f"   Directories: {stats['total_dirs']:,}")
    print(f"   Files: {stats['total_files']:,}")
    print(f"   Max depth: {stats['max_depth']}")
    print(f"   Errors: {stats['errors']}")
    print(f"   Scan time: {stats['scan_time']:.2f}s")
    
    # Show largest directories
    largest_dirs = scanner.find_largest_dirs(root, top_n=10)
    if largest_dirs:
        print(f"\n📁 Largest directories (by node count):")
        for i, (dir_node, size) in enumerate(largest_dirs, 1):
            depth_indicator = "  " * dir_node.depth
            print(f"   {i:2d}. {depth_indicator}{dir_node.name}/ - {size:,} items")
    
    return root, stats


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fast_scanner.py <path> [max_depth]")
        print("Example: python fast_scanner.py /tmp 3")
        sys.exit(1)
    
    path = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        root, stats = quick_scan(path, max_depth=max_depth)
        
        # Print tree structure (limited depth)
        print(f"\n🌳 Directory Structure (depth limited):")
        scanner = FastScanner()
        scanner.print_tree(root, max_depth=3)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
