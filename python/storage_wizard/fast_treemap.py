"""
Fast treemap scanner with minimal metadata for duplicate detection.
Captures essential metadata without expensive file operations.
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class FastTreemapNode:
    """Lightweight node for fast treemap with duplicate detection."""
    name: str
    path: str
    depth: int
    is_dir: bool
    size: int = 0
    mtime: float = 0
    file_count: int = 0
    children: List['FastTreemapNode'] = None
    parent: Optional['FastTreemapNode'] = None
    hash: str = ""
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def get_total_size(self) -> int:
        """Calculate total size including children."""
        if not self.is_dir:
            return self.size
        return self.size + sum(child.get_total_size() for child in self.children)
    
    def get_total_files(self) -> int:
        """Calculate total files including subdirectories."""
        if not self.is_dir:
            return 1
        return self.file_count + sum(child.get_total_files() for child in self.children)


class FastTreemapScanner:
    """Fast treemap scanner with minimal metadata for duplicate detection."""
    
    def __init__(self, 
                 max_depth: Optional[int] = None,
                 include_hidden: bool = False,
                 min_file_size: int = 1024,  # Skip files < 1KB
                 sample_large_files: bool = True,
                 sample_size: int = 8192):  # First 8KB for hashing
        self.max_depth = max_depth
        self.include_hidden = include_hidden
        self.min_file_size = min_file_size
        self.sample_large_files = sample_large_files
        self.sample_size = sample_size
        self.start_time = time.time()
        self.nodes_scanned = 0
        self.files_sampled = 0
        self.errors = []
    
    def scan(self, path: str) -> FastTreemapNode:
        """Scan directory structure with minimal metadata."""
        root_path = Path(path)
        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        root = FastTreemapNode(root_path.name, str(root_path), 0, True)
        self._scan_recursive(root_path, root, 0)
        
        # Calculate directory hashes
        self._calculate_hashes(root)
        
        elapsed = time.time() - self.start_time
        print(f"Fast treemap scan completed in {elapsed:.2f}s")
        print(f"  Nodes scanned: {self.nodes_scanned:,}")
        print(f"  Files sampled: {self.files_sampled:,}")
        
        return root
    
    def _scan_recursive(self, path: Path, node: FastTreemapNode, depth: int):
        """Recursively scan directory structure with minimal metadata."""
        if self.max_depth is not None and depth >= self.max_depth:
            return
        
        try:
            entries = list(os.scandir(path))
        except (PermissionError, OSError) as e:
            self.errors.append(f"Permission denied: {path}")
            node.hash = "permission-denied"
            return
        
        dirs = []
        files = []
        total_size = 0
        file_count = 0
        
        for entry in entries:
            self.nodes_scanned += 1
            
            # Skip hidden files if requested
            if not self.include_hidden and entry.name.startswith('.'):
                continue
            
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
                stat_info = entry.stat(follow_symlinks=False)
            except (OSError, PermissionError):
                continue
            
            child_node = FastTreemapNode(
                name=entry.name,
                path=entry.path,
                depth=depth + 1,
                is_dir=is_dir,
                size=stat_info.st_size if not is_dir else 0,
                mtime=stat_info.st_mtime if not is_dir else 0,
                parent=node
            )
            
            if is_dir:
                dirs.append(child_node)
                node.children.append(child_node)
            else:
                # Skip very small files (less likely to be important duplicates)
                if stat_info.st_size < self.min_file_size:
                    continue
                
                files.append(child_node)
                node.children.append(child_node)
                total_size += stat_info.st_size
                file_count += 1
                
                # Sample large files for content hashing
                if self.sample_large_files and stat_info.st_size > self.sample_size:
                    child_node.hash = self._sample_file_hash(entry.path)
                    self.files_sampled += 1
                elif stat_info.st_size > 0:
                    # For small files, hash size + mtime + name
                    content = f"{stat_info.st_size}:{stat_info.st_mtime}:{entry.name}"
                    child_node.hash = hashlib.md5(content.encode()).hexdigest()
        
        # Set directory metadata
        node.size = total_size
        node.file_count = file_count
        
        # Recurse into directories
        for dir_node in dirs:
            dir_path = Path(dir_node.path)
            self._scan_recursive(dir_path, dir_node, depth + 1)
    
    def _sample_file_hash(self, file_path: str) -> str:
        """Sample first few KB of file for content hashing."""
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(self.sample_size)
                return hashlib.md5(sample).hexdigest()
        except (OSError, PermissionError):
            # Fallback to size + mtime + name
            try:
                stat_info = os.stat(file_path)
                content = f"{stat_info.st_size}:{stat_info.st_mtime}:{Path(file_path).name}"
                return hashlib.md5(content.encode()).hexdigest()
            except:
                return "error"
    
    def _calculate_hashes(self, node: FastTreemapNode):
        """Calculate directory hashes based on children."""
        if not node.is_dir:
            return
        
        # Build hash from children
        hash_parts = []
        for child in sorted(node.children, key=lambda x: x.name):
            if child.is_dir:
                hash_parts.append((child.name, child.hash))
            else:
                # For files, use name, size, and content hash if available
                file_id = f"{child.name}:{child.size}"
                if child.hash and child.hash != "error":
                    file_id += f":{child.hash}"
                hash_parts.append(file_id)
        
        # Create directory hash
        if hash_parts:
            # Convert all parts to strings
            string_parts = []
            for part in hash_parts:
                if isinstance(part, tuple):
                    string_parts.append(f"{part[0]}:{part[1]}")
                else:
                    string_parts.append(str(part))
            
            hash_content = "|".join(string_parts)
            node.hash = hashlib.md5(hash_content.encode()).hexdigest()
        else:
            node.hash = "empty"
    
    def find_duplicate_subtrees(self, root: FastTreemapNode) -> Dict[str, List[FastTreemapNode]]:
        """Find potentially duplicate subtrees."""
        hash_map = defaultdict(list)
        
        def collect_hashes(node: FastTreemapNode):
            if node.hash and node.hash not in ["permission-denied", "empty", "error"]:
                hash_map[node.hash].append(node)
            
            for child in node.children:
                collect_hashes(child)
        
        collect_hashes(root)
        
        # Return only hashes with multiple occurrences
        return {h: nodes for h, nodes in hash_map.items() if len(nodes) > 1}
    
    def get_stats(self, root: FastTreemapNode) -> Dict:
        """Get comprehensive statistics."""
        stats = {
            'total_nodes': 0,
            'total_dirs': 0,
            'total_files': 0,
            'total_size': 0,
            'max_depth': 0,
            'duplicate_groups': 0,
            'errors': len(self.errors),
            'scan_time': time.time() - self.start_time,
            'files_sampled': self.files_sampled
        }
        
        def count_nodes(node: FastTreemapNode, depth: int = 0):
            stats['total_nodes'] += 1
            stats['max_depth'] = max(stats['max_depth'], depth)
            
            if node.is_dir:
                stats['total_dirs'] += 1
            else:
                stats['total_files'] += 1
                stats['total_size'] += node.size
            
            for child in node.children:
                count_nodes(child, depth + 1)
        
        count_nodes(root)
        
        # Count duplicate groups
        duplicates = self.find_duplicate_subtrees(root)
        stats['duplicate_groups'] = len(duplicates)
        
        return stats
    
    def print_duplicate_analysis(self, root: FastTreemapNode, min_size_mb: float = 10):
        """Print duplicate subtree analysis."""
        duplicates = self.find_duplicate_subtrees(root)
        
        if not duplicates:
            print("🎉 No duplicate subtrees found!")
            return
        
        print(f"\n🔍 Found {len(duplicates)} potential duplicate groups:")
        print(f"   (showing only those > {min_size_mb}MB)\n")
        
        for i, (hash_val, nodes) in enumerate(duplicates.items(), 1):
            # Calculate total size and check threshold
            total_size = sum(node.get_total_size() for node in nodes)
            size_mb = total_size / (1024 * 1024)
            
            if size_mb < min_size_mb:
                continue
            
            print(f"{i}. Duplicate group (hash: {hash_val[:12]}...)")
            print(f"   Total size: {size_mb:.1f}MB × {len(nodes)} copies = {size_mb * len(nodes):.1f}MB")
            print(f"   Potential waste: {size_mb * (len(nodes) - 1):.1f}MB")
            
            for j, node in enumerate(nodes, 1):
                node_size = node.get_total_size() / (1024 * 1024)
                node_files = node.get_total_files()
                depth_indicator = "  " * node.depth
                print(f"   {j}. {depth_indicator}{node.name}/ - {node_size:.1f}MB, {node_files:,} files")
                print(f"      Path: {node.path}")
            
            print()


def fast_treemap_scan(path: str, **kwargs):
    """Convenience function for fast treemap scanning."""
    scanner = FastTreemapScanner(**kwargs)
    root = scanner.scan(path)
    
    # Print statistics
    stats = scanner.get_stats(root)
    print(f"\n📊 Fast Treemap Results:")
    print(f"   Total nodes: {stats['total_nodes']:,}")
    print(f"   Directories: {stats['total_dirs']:,}")
    print(f"   Files: {stats['total_files']:,}")
    print(f"   Total size: {stats['total_size'] / (1024**3):.2f}GB")
    print(f"   Max depth: {stats['max_depth']}")
    print(f"   Duplicate groups: {stats['duplicate_groups']}")
    print(f"   Files sampled: {stats['files_sampled']:,}")
    print(f"   Errors: {stats['errors']}")
    print(f"   Scan time: {stats['scan_time']:.2f}s")
    
    # Show duplicate analysis
    scanner.print_duplicate_analysis(root)
    
    return root, stats


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fast_treemap.py <path> [min_size_mb]")
        print("Example: python fast_treemap.py /media/drive 10")
        sys.exit(1)
    
    path = sys.argv[1]
    min_size_mb = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    try:
        root, stats = fast_treemap_scan(path, min_file_size=1024)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
