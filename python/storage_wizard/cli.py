"""
Command-line interface for Storage Wizard.
All commands are read-only by default.
"""

import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from .core import StorageIndexer, MediaConsolidator, DuplicateDetector, OutputGenerator
from . import treemap as _treemap
from . import fast_scanner as _fast_scanner
from . import fast_treemap as _fast_treemap

app = typer.Typer(
    name="storage-wizard",
    help="Read-only storage indexing and optimization tool",
    no_args_is_help=True,
)

console = Console()
logger = logging.getLogger(__name__)


def _parse_size_string(size_str: str) -> int:
    """Parse size string like '100MB', '1GB', '500KB' into bytes."""
    size_str = size_str.upper().strip()
    
    # Extract number and unit
    import re
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)?$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}. Use formats like 100MB, 1GB, 500KB")
    
    number = float(match.group(1))
    unit = match.group(2) or 'B'  # Default to bytes if no unit
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
    }
    
    return int(number * multipliers[unit])


def _find_first_difference(node1, node2, path1=None, path2=None):
    """Find first differing subtree between two nodes."""
    if path1 is None:
        path1 = []
    if path2 is None:
        path2 = []
    
    # Check for content differences first (same name, different content)
    if node1.name == node2.name:
        if node1.file_count != node2.file_count or node1.size != node2.size:
            return node1, node2, path1, path2, "content"
    
    # Check if nodes are different at this level
    if len(node1.children) != len(node2.children):
        return node1, node2, path1, path2, "structure"
    
    # Sort children by name for consistent comparison
    children1 = sorted(node1.children, key=lambda x: x.name.lower())
    children2 = sorted(node2.children, key=lambda x: x.name.lower())
    
    # Check for differences in child names
    names1 = {c.name for c in children1}
    names2 = {c.name for c in children2}
    
    if names1 != names2:
        return node1, node2, path1, path2, "structure"
    
    # Recursively check children
    for child1, child2 in zip(children1, children2):
        if child1.hash != child2.hash:
            # Found difference, go deeper
            result = _find_first_difference(
                child1, child2, 
                path1 + [child1.name], 
                path2 + [child2.name]
            )
            if result:
                return result
    
    # No differences found
    return None


def _display_side_by_side_comparison(trees, dup_map, max_depth=None):
    """Display duplicate groups in side-by-side comparison format."""
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.columns import Columns
    from rich.align import Align
    
    console = Console()
    
    # Find the common root for all trees
    common_root = _find_common_root([tree[1] for tree in trees])
    
    # Create comparison of the common root
    _display_root_comparison(trees, common_root, dup_map, console)
    
    # Check for root-level content differences
    _display_root_content_differences(trees, console)
    
    # Show only the differences
    _display_differences_only(trees, dup_map, console)


def _diff_text(file_diff, size_diff):
    """Format a compact delta string for the middle column."""
    parts = []
    if file_diff != 0:
        sign = "+" if file_diff > 0 else "−"
        parts.append(f"{sign}{abs(file_diff):,} files")
    if size_diff != 0:
        sign = "+" if size_diff > 0 else "−"
        parts.append(f"{sign}{_format_size(abs(size_diff))}")
    return "\n".join(parts) if parts else "identical"


def _display_root_content_differences(trees, console):
    """Display content differences at the root level."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    
    if len(trees) < 2:
        return
    
    # Check first two trees for content differences
    left_label, left_node = trees[0]
    right_label, right_node = trees[1]
    
    # Check if root nodes have different content
    if left_node.file_count != right_node.file_count or left_node.size != right_node.size:
        header_text = Text("🔍 Root Content Differences", style="bold yellow")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Left", style="cyan", no_wrap=False)
        table.add_column("Δ", style="bold white", no_wrap=True, justify="center")
        table.add_column("Right", style="magenta", no_wrap=False)
        
        left_size = _format_size(left_node.size)
        right_size = _format_size(right_node.size)
        file_diff = left_node.file_count - right_node.file_count
        size_diff = left_node.size - right_node.size
        
        left_info = f"📁 {left_label}\n{left_node.path}\n {left_size}, {left_node.file_count:,} files"
        right_info = f"📁 {right_label}\n{right_node.path}\n {right_size}, {right_node.file_count:,} files"
        delta = _diff_text(file_diff, size_diff)
        
        table.add_row(left_info, delta, right_info)
        
        panel = Panel(
            table,
            title=header_text,
            border_style="bright_yellow",
            padding=(1, 2)
        )
        
        console.print(panel)
        console.print()
        
        # Show specific subdirectories that differ
        _show_differing_subdirectories(left_node, right_node, left_label, right_label, console)


def _show_differing_subdirectories(left_node, right_node, left_label, right_label, console):
    """Show specific subdirectories that have content differences."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    
    # Create header
    header_text = Text("📂 Subdirectories with Content Differences", style="bold yellow")
    
    # Create table for differing subdirectories
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Left", style="cyan", no_wrap=False)
    table.add_column("Δ", style="bold white", no_wrap=True, justify="center")
    table.add_column("Right", style="magenta", no_wrap=False)
    
    # Find all child directories with same name but different content
    left_children = {c.name: c for c in left_node.children}
    right_children = {c.name: c for c in right_node.children}
    
    # Find common names with different content
    common_names = set(left_children.keys()) & set(right_children.keys())
    differing_dirs = []
    
    for name in common_names:
        left_child = left_children[name]
        right_child = right_children[name]
        
        # Check if content differs (different file count or size)
        if (left_child.file_count != right_child.file_count or 
            left_child.size != right_child.size or
            left_child.hash != right_child.hash):
            differing_dirs.append((name, left_child, right_child))
    
    # Sort by size difference (largest first)
    differing_dirs.sort(key=lambda x: abs(x[1].size - x[2].size), reverse=True)
    
    # Show top 10 differing directories
    for i, (name, left_child, right_child) in enumerate(differing_dirs[:10]):
        left_size = _format_size(left_child.size)
        right_size = _format_size(right_child.size)
        file_diff = left_child.file_count - right_child.file_count
        size_diff = left_child.size - right_child.size
        
        left_info = f"📂 {name}/\n📊 {left_size}, {left_child.file_count:,} files"
        right_info = f"📂 {name}/\n📊 {right_size}, {right_child.file_count:,} files"
        delta = _diff_text(file_diff, size_diff)
        
        table.add_row(left_info, delta, right_info)
    
    if differing_dirs:
        # Create panel
        panel = Panel(
            table,
            title=header_text,
            border_style="bright_red",
            padding=(1, 2)
        )
        
        console.print(panel)
        
        if len(differing_dirs) > 10:
            console.print(f"[dim]... and {len(differing_dirs) - 10} more differing subdirectories[/dim]")
    else:
        console.print("[green]✅ No subdirectories with content differences found[/green]")
    
    console.print()


def _find_common_root(nodes):
    """Find the common root path among multiple nodes."""
    if not nodes:
        return None
    
    # Get all paths
    paths = [node.path for node in nodes]
    
    # Find common prefix
    common_parts = None
    for path in paths:
        parts = Path(path).parts
        if common_parts is None:
            common_parts = parts
        else:
            # Find common prefix
            common_parts = [a for a, b in zip(common_parts, parts) if a == b]
    
    return Path(*common_parts) if common_parts else Path("/")


def _display_root_comparison(trees, common_root, dup_map, console):
    """Display comparison of the common root directory."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    
    # Create header
    header_text = Text(f"🎯 Root Comparison: {common_root}", style="bold yellow")
    
    # Create comparison table
    table = Table(show_header=False, box=None, padding=0)
    table.add_column("Tree", style="cyan", width=80)
    table.add_column("Tree", style="magenta", width=80)
    
    # Add tree information
    for i in range(0, len(trees), 2):
        if i + 1 < len(trees):
            left_label, left_node = trees[i]
            right_label, right_node = trees[i + 1]
            
            left_size = _format_size(left_node.size)
            right_size = _format_size(right_node.size)
            
            left_info = f"📁 {left_label}\n{left_node.path}\n📊 {left_size}, {left_node.file_count:,} files"
            right_info = f"📁 {right_label}\n{right_node.path}\n📊 {right_size}, {right_node.file_count:,} files"
            
            table.add_row(left_info, right_info)
        elif i < len(trees):
            # Handle odd number of trees
            left_label, left_node = trees[i]
            left_size = _format_size(left_node.size)
            left_info = f"📁 {left_label}\n{left_node.path}\n📊 {left_size}, {left_node.file_count:,} files"
            table.add_row(left_info, "")
    
    # Create panel
    panel = Panel(
        table,
        title=header_text,
        border_style="bright_blue",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_differences_only(trees, dup_map, console):
    """Display only the differences between trees."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    
    if not dup_map:
        console.print("[green]✅ No differences found - trees are identical[/green]")
        return
    
    # Get common root for relative paths
    common_root = _find_common_root([tree[1] for tree in trees])
    
    # Filter to show only actual differences, not identical subtrees
    actual_differences = {}
    for hash_val, entries in dup_map.items():
        if len(entries) < 2:
            continue
            
        # Take first two entries for comparison
        left_label, left_node = entries[0]
        right_label, right_node = entries[1]
        
        # Find first difference
        diff_result = _find_first_difference(left_node, right_node)
        
        # Only include if there's an actual difference
        if diff_result:
            actual_differences[hash_val] = entries
    
    if not actual_differences:
        console.print("[green]✅ No structural differences found - all subtrees are identical[/green]")
        return
    
    # Create header
    header_text = Text(f"🔍 Structural Differences Found ({len(actual_differences)} groups)", style="bold yellow")
    
    # Create table for differences
    table = Table(show_header=False, box=None, padding=0)
    table.add_column("Left Tree", style="cyan", width=80)
    table.add_column("Right Tree", style="magenta", width=80)
    
    for hash_val, entries in actual_differences.items():
        # Take first two entries for comparison
        left_label, left_node = entries[0]
        right_label, right_node = entries[1]
        
        # Find relative paths from common root
        try:
            left_rel_path = str(Path(left_node.path).relative_to(common_root))
        except ValueError:
            left_rel_path = left_node.path
            
        try:
            right_rel_path = str(Path(right_node.path).relative_to(common_root))
        except ValueError:
            right_rel_path = right_node.path
        
        # Find first difference
        diff_result = _find_first_difference(left_node, right_node)
        
        if diff_result:
            diff_left, diff_right, path_left, path_right, diff_type = diff_result
            
            if diff_type == "structure":
                # Show path to structural difference
                left_path_display = " → ".join(path_left[-3:] if len(path_left) > 3 else path_left)
                right_path_display = " → ".join(path_right[-3:] if len(path_right) > 3 else path_right)
                
                left_info = f"📂 {left_label}\n{left_rel_path}\n📍 {left_path_display}"
                right_info = f"📂 {right_label}\n{right_rel_path}\n📍 {right_path_display}"
                
                # Show missing/extra details
                left_children = sorted(diff_left.children, key=lambda x: x.name.lower())
                right_children = sorted(diff_right.children, key=lambda x: x.name.lower())
                
                left_names = {c.name for c in left_children}
                right_names = {c.name for c in right_children}
                
                missing_in_left = right_names - left_names
                extra_in_left = left_names - right_names
                
                if missing_in_left:
                    missing_text = "❌ Missing: " + ", ".join(sorted(list(missing_in_left))[:3])
                    if len(missing_in_left) > 3:
                        missing_text += f" (+{len(missing_in_left)-3} more)"
                    left_info += f"\n{missing_text}"
                
                if extra_in_left:
                    extra_text = "➕ Extra: " + ", ".join(sorted(list(extra_in_left))[:3])
                    if len(extra_in_left) > 3:
                        extra_text += f" (+{len(extra_in_left)-3} more)"
                    right_info += f"\n{extra_text}"
            else:
                # Content difference - show summary statistics
                left_size = _format_size(left_node.size)
                right_size = _format_size(right_node.size)
                file_diff = left_node.file_count - right_node.file_count
                size_diff = left_node.size - right_node.size
                
                left_info = f"📂 {left_label}\n{left_rel_path}\n🔍 Content difference\n📊 {left_size}, {left_node.file_count:,} files"
                right_info = f"📂 {right_label}\n{right_rel_path}\n🔍 Content difference\n📊 {right_size}, {right_node.file_count:,} files"
                
                # Add difference summary
                if file_diff != 0:
                    if file_diff > 0:
                        left_info += f"\n➕ {file_diff:,} more files"
                        right_info += f"\n➖ {abs(file_diff):,} fewer files"
                    else:
                        left_info += f"\n➖ {abs(file_diff):,} fewer files"
                        right_info += f"\n➕ {abs(file_diff):,} more files"
                
                if size_diff != 0:
                    size_diff_str = _format_size(abs(size_diff))
                    if size_diff > 0:
                        left_info += f"\n➕ {size_diff_str} larger"
                        right_info += f"\n➖ {size_diff_str} smaller"
                    else:
                        left_info += f"\n➖ {size_diff_str} smaller"
                        right_info += f"\n➕ {size_diff_str} larger"
        
        table.add_row(left_info, right_info)
    
    # Create panel
    panel = Panel(
        table,
        title=header_text,
        border_style="bright_red",
        padding=(1, 2)
    )
    
    console.print(panel)


def _create_comparison_panel(group_num, total_groups, left_label, left_node, right_label, right_node, diff_result):
    """Create a single comparison panel for one duplicate group."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.columns import Columns
    from rich.align import Align
    
    # Header
    header_text = Text(f"🎯 Duplicate Group {group_num}/{total_groups}", style="bold yellow")
    
    # Create comparison table
    table = Table(show_header=False, box=None, padding=0)
    table.add_column("Left", style="cyan", width=80)
    table.add_column("Right", style="magenta", width=80)
    
    # Add root paths
    left_root = f"📁 {left_label}\n{left_node.path}"
    right_root = f"📁 {right_label}\n{right_node.path}"
    table.add_row(left_root, right_root)
    
    # Add size information
    left_size = _format_size(left_node.size)
    right_size = _format_size(right_node.size)
    left_info = f"📊 {left_size}, {left_node.file_count:,} files"
    right_info = f"📊 {right_size}, {right_node.file_count:,} files"
    table.add_row(left_info, right_info)
    
    # Add difference information
    if diff_result:
        diff_left, diff_right, path_left, path_right, diff_type = diff_result
        
        if diff_type == "structure":
            diff_text = "🔍 STRUCTURE DIFFERENCE FOUND"
            table.add_row(diff_text, diff_text)
            
            # Show paths to difference
            left_path = " → ".join(path_left[-3:] if len(path_left) > 3 else path_left) if path_left else "Root"
            right_path = " → ".join(path_right[-3:] if len(path_right) > 3 else path_right) if path_right else "Root"
            table.add_row(f"📍 Left path: {left_path}", f"📍 Right path: {right_path}")
            
            # Show children details
            left_children = sorted(diff_left.children, key=lambda x: x.name.lower())
            right_children = sorted(diff_right.children, key=lambda x: x.name.lower())
            
            left_names = {c.name for c in left_children}
            right_names = {c.name for c in right_children}
            
            # Show missing/extra children
            missing_in_left = right_names - left_names
            extra_in_left = left_names - right_names
            
            if missing_in_left:
                missing_text = "❌ Missing: " + ", ".join(sorted(list(missing_in_left))[:3])
                if len(missing_in_left) > 3:
                    missing_text += f" (+{len(missing_in_left)-3} more)"
                table.add_row(missing_text, "")
            
            if extra_in_left:
                extra_text = "➕ Extra: " + ", ".join(sorted(list(extra_in_left))[:3])
                if len(extra_in_left) > 3:
                    extra_text += f" (+{len(extra_in_left)-3} more)"
                table.add_row(extra_text, "")
                
        else:
            diff_text = "🔍 CONTENT DIFFERENCE FOUND"
            table.add_row(diff_text, diff_text)
    else:
        diff_text = "✅ IDENTICAL SUBTREES"
        table.add_row(diff_text, diff_text)
        
        # Show some sample content for identical subtrees
        if left_node.children:
            sample_children = sorted(left_node.children, key=lambda x: x.size, reverse=True)[:3]
            sample_text = "📁 Sample: " + ", ".join([f"{c.name}/ ({_format_size(c.size)})" for c in sample_children])
            table.add_row(sample_text, sample_text)
    
    # Create panel
    panel = Panel(
        table,
        title=header_text,
        border_style="bright_blue",
        padding=(1, 2)
    )
    
    return panel


def _format_size(size_bytes):
    """Format bytes into human readable string."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


@app.command("fast-treemap")
def fast_treemap(
    paths: List[str] = typer.Argument(..., help="Directories to scan for duplicate analysis"),
    max_depth: Optional[int] = typer.Option(None, "--depth", "-d", 
        help="Maximum directory depth to scan"),
    include_hidden: bool = typer.Option(False, "--hidden", 
        help="Include hidden files and directories"),
    min_file_size: int = typer.Option(1024, "--min-size", "-s", 
        help="Minimum file size to consider (bytes)"),
    min_duplicate_size: float = typer.Option(10.0, "--min-duplicate", "-m",
        help="Minimum duplicate size to report (MB)"),
    sample_size: int = typer.Option(8192, "--sample-size",
        help="Sample size for file hashing (bytes)"),
) -> None:
    """Fast treemap scan with duplicate detection using minimal metadata."""
    console.print(f"[bold blue]🚀 Fast Treemap Scan[/bold blue]")
    console.print(f"Scanning: [cyan]{', '.join(paths)}[/cyan]")
    console.print(f"Mode: Metadata-only with content sampling for duplicates")
    
    try:
        all_nodes = []
        all_stats = []
        total_duplicates = {}
        
        # Scan each path
        for i, path in enumerate(paths, 1):
            console.print(f"\n[yellow]Scanning path {i}/{len(paths)}: {path}[/yellow]")
            
            scanner = _fast_treemap.FastTreemapScanner(
                max_depth=max_depth,
                include_hidden=include_hidden,
                min_file_size=min_file_size,
                sample_size=sample_size
            )
            root = scanner.scan(path)
            stats = scanner.get_stats(root)
            
            all_nodes.append(root)
            all_stats.append(stats)
            
            # Collect duplicates from this path
            path_duplicates = scanner.find_duplicate_subtrees(root)
            
            # Merge duplicates across paths
            for hash_val, nodes in path_duplicates.items():
                if hash_val not in total_duplicates:
                    total_duplicates[hash_val] = []
                total_duplicates[hash_val].extend(nodes)
        
        # Display combined results
        total_nodes = sum(s['total_nodes'] for s in all_stats)
        total_dirs = sum(s['total_dirs'] for s in all_stats)
        total_files = sum(s['total_files'] for s in all_stats)
        total_size = sum(s['total_size'] for s in all_stats)
        max_depth_found = max(s['max_depth'] for s in all_stats)
        total_files_sampled = sum(s['files_sampled'] for s in all_stats)
        total_errors = sum(s['errors'] for s in all_stats)
        total_scan_time = sum(s['scan_time'] for s in all_stats)
        
        console.print(f"\n[bold]📊 Combined Fast Treemap Results:[/bold]")
        console.print(f"   Paths scanned: [green]{len(paths)}[/green]")
        console.print(f"   Total nodes: [green]{total_nodes:,}[/green]")
        console.print(f"   Directories: [blue]{total_dirs:,}[/blue]")
        console.print(f"   Files: [yellow]{total_files:,}[/yellow]")
        console.print(f"   Total size: [cyan]{total_size / (1024**3):.2f}GB[/cyan]")
        console.print(f"   Max depth: [cyan]{max_depth_found}[/cyan]")
        console.print(f"   Files sampled: [green]{total_files_sampled:,}[/green]")
        console.print(f"   Errors: [red]{total_errors}[/red]")
        console.print(f"   Total scan time: [green]{total_scan_time:.2f}s[/green]")
        
        # Show per-path statistics
        console.print(f"\n[bold]📋 Per-Path Statistics:[/bold]")
        for i, (path, stats) in enumerate(zip(paths, all_stats), 1):
            console.print(f"   {i}. [cyan]{path}[/cyan]")
            console.print(f"      Nodes: {stats['total_nodes']:,}, Size: {stats['total_size'] / (1024**2):.1f}MB, Time: {stats['scan_time']:.2f}s")
        
        # Show cross-path duplicate analysis
        # Filter duplicates to only show those with multiple paths
        cross_path_duplicates = {}
        for hash_val, nodes in total_duplicates.items():
            # Check if nodes come from different paths
            unique_paths = set(Path(node.path).parent for node in nodes)
            if len(unique_paths) > 1:  # Duplicates across different paths
                cross_path_duplicates[hash_val] = nodes
        
        if not cross_path_duplicates:
            console.print(f"\n[bold green]🎉 No cross-path duplicate subtrees found![/bold green]")
        else:
            console.print(f"\n[bold]🔍 Found {len(cross_path_duplicates)} cross-path duplicate groups:[/bold]")
            console.print(f"   (showing only those > {min_duplicate_size}MB)\n")
            
            # Sort duplicates by total size
            sorted_duplicates = sorted(
                [(hash_val, nodes) for hash_val, nodes in cross_path_duplicates.items()],
                key=lambda x: sum(node.get_total_size() for node in x[1]),
                reverse=True
            )
            
            for i, (hash_val, nodes) in enumerate(sorted_duplicates, 1):
                # Calculate total size and check threshold
                total_size = sum(node.get_total_size() for node in nodes)
                size_mb = total_size / (1024 * 1024)
                
                if size_mb < min_duplicate_size:
                    continue
                
                console.print(f"[bold]{i}.[/bold] Cross-path duplicate group (hash: [dim]{hash_val[:12]}...[/dim])")
                console.print(f"   Total size: [cyan]{size_mb:.1f}MB[/cyan] × [yellow]{len(nodes)}[/yellow] copies = [red]{size_mb * len(nodes):.1f}MB[/red]")
                console.print(f"   Potential waste: [red]{size_mb * (len(nodes) - 1):.1f}MB[/red]")
                
                # Group nodes by path
                path_groups = {}
                for node in nodes:
                    node_path = Path(node.path)
                    # Find which original path this belongs to
                    for original_path in paths:
                        if node_path.is_relative_to(original_path):
                            if original_path not in path_groups:
                                path_groups[original_path] = []
                            path_groups[original_path].append(node)
                            break
                
                for j, (path, path_nodes) in enumerate(path_groups.items(), 1):
                    console.print(f"   [bold]Path {j}:[/bold] [cyan]{path}[/cyan]")
                    for k, node in enumerate(path_nodes, 1):
                        node_size = node.get_total_size() / (1024 * 1024)
                        node_files = node.get_total_files()
                        depth_indicator = "  " * min(node.depth, 3)
                        console.print(f"      {k}. {depth_indicator}[cyan]{node.name}/[/cyan] - [green]{node_size:.1f}MB[/green], [yellow]{node_files:,}[/yellow] files")
                        console.print(f"         Path: [dim]{node.path}[/dim]")
                
                console.print()
        
        # Show errors if any
        if total_errors > 0:
            console.print(f"\n[bold red]⚠️  Errors encountered:[/bold red]")
            console.print(f"   Total errors: {total_errors}")
            # Note: Detailed error reporting could be added here if needed
        
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)


@app.command("fast-scan")
def fast_scan(
    path: str = typer.Argument(..., help="Directory to scan quickly"),
    max_depth: Optional[int] = typer.Option(None, "--depth", "-d", 
        help="Maximum directory depth to scan"),
    include_hidden: bool = typer.Option(False, "--hidden", 
        help="Include hidden files and directories"),
    show_tree: bool = typer.Option(True, "--tree/--no-tree", 
        help="Show directory tree structure"),
) -> None:
    """Ultra-fast directory structure analysis (metadata only)."""
    console.print(f"[bold blue]🚀 Fast Scan Mode[/bold blue]")
    console.print(f"Scanning: [cyan]{path}[/cyan]")
    
    try:
        scanner = _fast_scanner.FastScanner(
            max_depth=max_depth, 
            include_hidden=include_hidden
        )
        root = scanner.scan(path)
        stats = scanner.get_stats(root)
        
        # Display results
        console.print(f"\n[bold]📊 Quick Scan Results:[/bold]")
        console.print(f"   Total nodes: [green]{stats['total_nodes']:,}[/green]")
        console.print(f"   Directories: [blue]{stats['total_dirs']:,}[/blue]")
        console.print(f"   Files: [yellow]{stats['total_files']:,}[/yellow]")
        console.print(f"   Max depth: [cyan]{stats['max_depth']}[/cyan]")
        console.print(f"   Errors: [red]{stats['errors']}[/red]")
        console.print(f"   Scan time: [green]{stats['scan_time']:.2f}s[/green]")
        
        # Show largest directories
        largest_dirs = scanner.find_largest_dirs(root, top_n=10)
        if largest_dirs:
            console.print(f"\n[bold]📁 Largest directories (by node count):[/bold]")
            for i, (dir_node, size) in enumerate(largest_dirs, 1):
                depth_indicator = "  " * min(dir_node.depth, 5)
                console.print(f"   {i:2d}. {depth_indicator}[cyan]{dir_node.name}/[/cyan] - [green]{size:,}[/green] items")
        
        # Show tree structure if requested
        if show_tree:
            console.print(f"\n[bold]🌳 Directory Structure (depth limited):[/bold]")
            tree_depth = min(3, max_depth) if max_depth else 3
            scanner.print_tree(root, max_depth=tree_depth)
        
        # Show errors if any
        if scanner.errors:
            console.print(f"\n[bold red]⚠️  Errors encountered:[/bold red]")
            for error in scanner.errors[:5]:  # Show first 5 errors
                console.print(f"   {error}")
            if len(scanner.errors) > 5:
                console.print(f"   ... and {len(scanner.errors) - 5} more errors")
        
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def scan(
    path: str = typer.Argument(..., help="Directory path to scan"),
    include_hidden: bool = typer.Option(False, "--hidden", "-h", help="Include hidden files"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, csv"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Scan and index directory contents (read-only)."""
    if verbose:
        logging.basicConfig(level=logging.INFO)

    console.print(f"[bold blue]Scanning directory (read-only):[/bold blue] {path}")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Initializing...", total=None)
        indexer = StorageIndexer(path, read_only=True)

        progress.update(task, description="Scanning files...")
        result = indexer.scan_directory(include_hidden)

        progress.update(task, description="Computing hashes...")
        hashes = indexer.compute_hashes()

        progress.update(task, description="Done", completed=True)

    console.print(Panel(
        f"[bold green]Scan Complete![/bold green]\n"
        f"Total files: {result['total_files']}\n"
        f"Hashes computed: {len(hashes)}",
        title="Results",
    ))

    denied = result.get("permission_denied_dirs", [])
    if denied:
        console.print(f"[bold yellow]Permission denied for {len(denied)} director{'y' if len(denied) == 1 else 'ies'}[/bold yellow]")
        for d in denied[:5]:
            console.print(f"  [dim]{d}[/dim]")
        if len(denied) > 5:
            console.print(f"  ... and {len(denied) - 5} more")

    file_types: dict = {}
    total_size = 0
    for fi in result["files"]:
        ext = fi["file_type"] or "no_extension"
        file_types[ext] = file_types.get(ext, 0) + 1
        total_size += fi["size"]

    table = Table(title="File Type Distribution")
    table.add_column("Extension", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")
    for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:15]:
        pct = (count / max(result["total_files"], 1)) * 100
        table.add_row(ext, str(count), f"{pct:.1f}%")
    console.print(table)

    if output_file:
        output_gen = OutputGenerator(indexer)
        analysis = {"scan_result": result, "hashes": hashes, "duplicates": indexer.find_duplicates()}
        if output_format == "csv":
            ok = output_gen.generate_csv_summary(analysis, output_file)
        else:
            ok = output_gen.generate_json_report(analysis, output_file)
        if ok:
            console.print(f"[green]Saved to:[/green] {output_file}")
        else:
            console.print(f"[red]Failed to save to:[/red] {output_file}")


@app.command()
def duplicates(
    paths: list[str] = typer.Argument(..., help="Directory paths to analyze (can be multiple, supports glob patterns)"),
    group_by_dir: bool = typer.Option(False, "--group-by-dir", "-g", help="Group duplicates by directory"),
    percent_dup_threshold: float = typer.Option(100.0, "--percent-dup-threshold", "-t", help="Show directories with duplicate percentage above this threshold (0-100)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save output to file"),
    export_data: Optional[str] = typer.Option(None, "--export-data", "-e", help="Export machine-readable data for visualization (json, csv)"),
    union_file: Optional[str] = typer.Option(None, "--union", "-u", help="Save union of all files to text file"),
    intersection_file: Optional[str] = typer.Option(None, "--intersection", "-i", help="Save intersection of files to text file"),
    exclusive_file: Optional[str] = typer.Option(None, "--exclusive", "-x", help="Save files exclusive to only one path to text file"),
    depth: Optional[int] = typer.Option(None, "--depth", help="Maximum depth for glob expansion (0=current dir only, 1=subdirs, etc.)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Find duplicate files (read-only)."""
    if verbose:
        logging.basicConfig(level=logging.INFO)

    # Helper function to print to both console and file
    def print_both(message=""):
        if output_capture:
            output_capture.print(message)
        console.print(message)

    # Capture output if file specified
    output_capture = None
    if output:
        from rich.console import Console
        output_capture = Console(file=open(output, 'w'), width=120)

    # Expand glob patterns in paths
    import glob
    expanded_paths = []
    
    for path_pattern in paths:
        if '*' in path_pattern or '?' in path_pattern or '[' in path_pattern:
            # This is a glob pattern, expand it
            if debug:
                print_both(f"[dim]Debug: Expanding glob pattern: {path_pattern}[/dim]")
            
            # Handle depth-limited expansion
            if depth is not None:
                # For depth-limited expansion, we need to manually walk
                base_path = path_pattern.replace('*', '').replace('?', '').replace('[', '').replace(']', '')
                base_path = base_path.rstrip('/\\')  # Remove trailing slashes
                if not base_path:
                    base_path = '.'
                
                expanded_dirs = []
                if depth == 0:
                    # Only current directory
                    if os.path.isdir(base_path):
                        expanded_dirs = [base_path]
                else:
                    # Walk to specified depth
                    for root, dirs, files in os.walk(base_path):
                        current_depth = root.count(os.sep) - base_path.count(os.sep)
                        if current_depth <= depth:
                            if current_depth < depth:
                                # Limit further exploration
                                dirs[:] = [d for d in dirs if not d.startswith('.')]  # Remove hidden dirs
                            expanded_dirs.append(root)
                
                # Filter to match the original pattern
                import fnmatch
                for dir_path in expanded_dirs:
                    if fnmatch.fnmatch(dir_path, path_pattern) or fnmatch.fnmatch(os.path.basename(dir_path), path_pattern.replace('*/', '')):
                        if os.path.isdir(dir_path):
                            expanded_paths.append(dir_path)
                            if debug:
                                print_both(f"[dim]Debug: Added directory: {dir_path}[/dim]")
            else:
                # Unlimited depth - use standard glob
                glob_matches = glob.glob(path_pattern, recursive=True)
                for match in glob_matches:
                    if os.path.isdir(match):
                        expanded_paths.append(match)
                        if debug:
                            print_both(f"[dim]Debug: Added directory: {match}[/dim]")
                
                # Also handle the case where pattern matches directories inside
                # For example: tests/testdirs/* should match subdirs of testdirs
                if '*' in path_pattern and path_pattern.endswith('*'):
                    base_pattern = path_pattern.rsplit('*', 1)[0]
                    if os.path.isdir(base_pattern):
                        for item in glob.glob(os.path.join(base_pattern, '*')):
                            if os.path.isdir(item):
                                expanded_paths.append(item)
                                if debug:
                                    print_both(f"[dim]Debug: Added subdirectory: {item}[/dim]")
        else:
            # Regular path, just add it if it exists and is a directory
            if os.path.isdir(path_pattern):
                expanded_paths.append(path_pattern)
            elif debug:
                print_both(f"[dim]Debug: Path not found or not a directory: {path_pattern}[/dim]")
    
    # Remove duplicates and sort
    expanded_paths = sorted(list(set(expanded_paths)))
    
    if not expanded_paths:
        print_both("[red]No valid directories found to analyze[/red]")
        return
    
    if debug or verbose:
        print_both(f"[dim]Found {len(expanded_paths)} directories to analyze:[/dim]")
        for path in expanded_paths:
            print_both(f"[dim]  - {path}[/dim]")
    
    # Use expanded paths instead of original paths
    paths = expanded_paths
    
    print_both(f"[bold blue]Finding duplicates in:[/bold blue] {', '.join(paths)}")

    # Scan all paths
    all_indexed_files = []
    all_dups = []
    
    with Progress(console=console) as progress:
        task = progress.add_task("Scanning and hashing...", total=None)
        
        for path in paths:
            progress.update(task, description=f"Scanning {path}...")
            indexer = StorageIndexer(path, read_only=True)
            indexer.scan_directory()
            indexer.compute_hashes()
            dups = indexer.find_duplicates()
            
            all_indexed_files.extend(indexer._indexed_files)
            all_dups.extend(dups)
        
        # Combine duplicate groups that span multiple paths
        # Create a hash-based mapping to merge duplicate groups across paths
        hash_to_files = {}
        for file_info in all_indexed_files:
            file_hash = file_info.get("hash")
            if file_hash:
                if file_hash not in hash_to_files:
                    hash_to_files[file_hash] = []
                hash_to_files[file_hash].append(file_info["path"])
        
        # Create final duplicate groups (only groups with 2+ files)
        combined_dups = [files for files in hash_to_files.values() if len(files) > 1]
        
        progress.update(task, description="Done", completed=True)

    if not combined_dups:
        print_both("[green]No duplicate files found.[/green]")
        if output_capture:
            output_capture.file.close()
        return

    # Perform set operations if requested
    if union_file or intersection_file or exclusive_file:
        from collections import defaultdict
        
        # Build file sets for each path
        path_file_sets = {}
        path_file_hashes = {}
        
        for path in paths:
            path_files = set()
            path_hashes = set()
            
            for file_info in all_indexed_files:
                file_path = file_info["path"]
                if file_path.startswith(path):
                    path_files.add(file_path)
                    if file_info.get("hash"):
                        path_hashes.add(file_info["hash"])
                    if debug and len(path_files) <= 3:  # Show first few files per path
                        print_both(f"[dim]Debug: {path} -> {file_path} (hash: {file_info.get('hash', 'None')[:8]})[/dim]")
            
            path_file_sets[path] = path_files
            path_file_hashes[path] = path_hashes
            
            if debug:
                print_both(f"[dim]Debug: Path {path} has {len(path_files)} files, {len(path_hashes)} unique hashes[/dim]")
        
        # Union of all files
        if union_file:
            union_files = set()
            for file_set in path_file_sets.values():
                union_files.update(file_set)
            
            with open(union_file, 'w') as f:
                for file_path in sorted(union_files):
                    f.write(f"{file_path}\n")
            console.print(f"[green]Union ({len(union_files)} files) saved to:[/green] {union_file}")
        
        # Intersection of files (by hash)
        if intersection_file and len(paths) > 1:
            # Find hashes that exist in ALL paths
            common_hashes = set.intersection(*path_file_hashes.values()) if path_file_hashes else set()
            
            if debug:
                print_both(f"[dim]Debug: Path hash counts:[/dim]")
                for path, hashes in path_file_hashes.items():
                    print_both(f"[dim]  {path}: {len(hashes)} hashes[/dim]")
                print_both(f"[dim]Debug: Common hashes across all paths: {len(common_hashes)}[/dim]")
                if common_hashes:
                    print_both(f"[dim]Debug: Common hash samples: {list(common_hashes)[:3]}[/dim]")
            
            # Get file paths for common hashes (first occurrence from each path)
            intersection_files = set()
            for file_info in all_indexed_files:
                if file_info.get("hash") in common_hashes:
                    intersection_files.add(file_info["path"])
            
            if debug and not intersection_files:
                print_both(f"[dim]Debug: No intersection files found. Checking for partial overlaps...[/dim]")
                # Show some hash overlaps between pairs of paths
                path_list = list(paths)
                for i in range(len(path_list)):
                    for j in range(i + 1, len(path_list)):
                        path1, path2 = path_list[i], path_list[j]
                        overlap = path_file_hashes[path1] & path_file_hashes[path2]
                        if overlap:
                            print_both(f"[dim]  {path1} ↔ {path2}: {len(overlap)} common hashes[/dim]")
                            # Show some example files
                            for file_info in all_indexed_files:
                                if (file_info.get("hash") in overlap and 
                                    file_info["path"].startswith(path1)):
                                    print_both(f"[dim]    Example: {file_info['path']}[/dim]")
                                    break
            
            with open(intersection_file, 'w') as f:
                for file_path in sorted(intersection_files):
                    f.write(f"{file_path}\n")
            console.print(f"[green]Intersection ({len(intersection_files)} files) saved to:[/green] {intersection_file}")
        
        # Exclusive files (exist in only one path)
        if exclusive_file:
            # Count how many paths each hash appears in
            hash_path_count = defaultdict(int)
            hash_to_paths = defaultdict(list)
            
            for file_info in all_indexed_files:
                file_hash = file_info.get("hash")
                if file_hash:
                    hash_path_count[file_hash] += 1
                    # Find which path this file belongs to
                    for path in paths:
                        if file_info["path"].startswith(path):
                            hash_to_paths[file_hash].append(path)
                            break
            
            # Files that are exclusive to one path (hash appears in only one path)
            exclusive_files = set()
            for file_info in all_indexed_files:
                file_hash = file_info.get("hash")
                if file_hash and hash_path_count[file_hash] == 1:
                    exclusive_files.add(file_info["path"])
            
            with open(exclusive_file, 'w') as f:
                for file_path in sorted(exclusive_files):
                    f.write(f"{file_path}\n")
            console.print(f"[green]Exclusive files ({len(exclusive_files)} files) saved to:[/green] {exclusive_file}")

    if group_by_dir:
        # Group duplicates by directory with percentage analysis
        from collections import defaultdict
        dir_analysis = defaultdict(lambda: {"total_files": 0, "duplicate_files": set(), "non_duplicate_files": set()})
        
        # First, collect all files in each directory
        all_files = set()
        if debug:
            print_both(f"[dim]Debug: Scanning directories for file analysis...[/dim]")
        
        for file_info in all_indexed_files:
            filepath = file_info["path"]
            parent_dir = str(Path(filepath).parent)
            all_files.add(filepath)
            dir_analysis[parent_dir]["total_files"] += 1
        
        # Identify duplicate files
        duplicate_files = set()
        for group in combined_dups:
            for filepath in group:
                duplicate_files.add(filepath)
        
        # Analyze each directory for cross-directory duplicates
        for filepath in all_files:
            parent_dir = str(Path(filepath).parent)
            if filepath in duplicate_files:
                dir_analysis[parent_dir]["duplicate_files"].add(filepath)
            else:
                dir_analysis[parent_dir]["non_duplicate_files"].add(filepath)
        
        # Filter directories by threshold based on cross-directory duplication
        filtered_dirs = {}
        for dir_path, analysis in dir_analysis.items():
            if analysis["total_files"] == 0:
                continue
            
            # Count files that have duplicates in OTHER directories
            cross_dir_duplicates = 0
            for filepath in analysis["duplicate_files"]:
                # Find all files with the same content
                for group in combined_dups:
                    if filepath in group:
                        # Check if this file exists in other directories
                        other_dirs_with_same_file = set()
                        for fp in group:
                            other_dir = str(Path(fp).parent)
                            if other_dir != dir_path:
                                other_dirs_with_same_file.add(other_dir)
                        
                        if other_dirs_with_same_file:  # File exists in other directories
                            cross_dir_duplicates += 1
                        break
            
            dup_percentage = (cross_dir_duplicates / analysis["total_files"]) * 100
            if dup_percentage >= percent_dup_threshold:
                filtered_dirs[dir_path] = {
                    **analysis,
                    "dup_percentage": dup_percentage,
                    "cross_dir_duplicates": cross_dir_duplicates
                }
        
        if not filtered_dirs:
            console.print(f"[green]No directories found with >= {percent_dup_threshold}% duplicates[/green]")
            return

        print_both(f"[bold yellow]Found {len(filtered_dirs)} directories with >= {percent_dup_threshold}% duplicates[/bold yellow]")
        if debug:
            print_both(f"[dim]Debug: Total duplicate groups found: {len(combined_dups)}[/dim]")
        
        # Group directories by their file content to identify identical directories
        dir_signatures = {}
        for dir_path, analysis in filtered_dirs.items():
            # Create a signature based on the set of file hashes in this directory
            file_hashes = set()
            for file_info in all_indexed_files:
                if str(Path(file_info["path"]).parent) == dir_path and file_info.get("hash"):
                    file_hashes.add(file_info["hash"])
            
            # Sort hashes to create consistent signature
            signature = tuple(sorted(file_hashes))
            if signature not in dir_signatures:
                dir_signatures[signature] = []
            dir_signatures[signature].append((dir_path, analysis))
        
        # Sort by duplicate percentage (highest first), but only take one directory per signature
        unique_dirs = []
        for signature, dirs_list in dir_signatures.items():
            # Sort dirs in this group by percentage and take the highest
            dirs_list.sort(key=lambda x: x[1]["dup_percentage"], reverse=True)
            unique_dirs.append(dirs_list[0])
        
        # Sort all unique directories by percentage
        unique_dirs.sort(key=lambda x: x[1]["dup_percentage"], reverse=True)
        
        # Track which directory pairs we've already compared to avoid duplicates
        compared_pairs = set()
        
        for i, (dir_path, analysis) in enumerate(unique_dirs, 1):
            dup_pct = analysis["dup_percentage"]
            console.print(f"\n[bold]Directory {i}[/bold]: {dir_path}")
            cross_dup_count = analysis.get('cross_dir_duplicates', len(analysis['duplicate_files']))
            console.print(f"  [cyan]Cross-directory duplicates:[/cyan] {cross_dup_count}/{analysis['total_files']} ({dup_pct:.1f}%)")
            if debug:
                console.print(f"    [dim]Debug: Total files: {analysis['total_files']}, Duplicate files: {len(analysis['duplicate_files'])}, Non-duplicate: {len(analysis['non_duplicate_files'])}[/dim]")
            
            if dup_pct < 100.0 and analysis["non_duplicate_files"]:
                console.print(f"  [yellow]Non-duplicate files ({len(analysis['non_duplicate_files'])}):[/yellow]")
                for fp in sorted(analysis["non_duplicate_files"])[:10]:
                    console.print(f"    {fp}")
                if len(analysis["non_duplicate_files"]) > 10:
                    console.print(f"    ... and {len(analysis['non_duplicate_files']) - 10} more")
            
            # Show vimdiff-style directory comparison for this directory group
            if analysis["duplicate_files"]:
                console.print(f"  [dim]Directory comparison (vimdiff-style):[/dim]")
                
                # Get all other directories that have ANY duplicate files
                other_dirs = set()
                for file_info in all_indexed_files:
                    if file_info["path"] in analysis["duplicate_files"]:
                        parent_dir = str(Path(file_info["path"]).parent)
                        if parent_dir != dir_path:
                            other_dirs.add(parent_dir)
                
                # Also add directories that have files with the same content
                for filepath in analysis["duplicate_files"]:
                    for group in combined_dups:
                        if filepath in group:
                            for fp in group:
                                other_dir = str(Path(fp).parent)
                                if other_dir != dir_path:
                                    other_dirs.add(other_dir)
                            break
                
                # Filter out directories we've already compared with (avoid bidirectional comparisons)
                dirs_to_compare = []
                for other_dir in sorted(other_dirs):
                    comparison_key = tuple(sorted([dir_path, other_dir]))
                    if comparison_key not in compared_pairs:
                        dirs_to_compare.append(other_dir)
                        compared_pairs.add(comparison_key)
                
                if not dirs_to_compare:
                    console.print(f"    [yellow]No new directory comparisons needed[/yellow]")
                    if debug:
                        console.print(f"    [dim]Debug: Current dir has {len(analysis['duplicate_files'])} duplicate files[/dim]")
                        console.print(f"    [dim]Debug: All comparisons already done[/dim]")
                else:
                    # Sort other directories for consistent display
                    sorted_other_dirs = sorted(dirs_to_compare)
                    
                    # Create column headers (current dir + other dirs)
                    filename_width = 40
                    dir_width = 25
                
                # Get display names with longer, more meaningful paths
                    def get_meaningful_dir_name(dir_path):
                        """Get a more meaningful directory name that shows context."""
                        path_parts = Path(dir_path).parts
                        
                        # Show more context - aim for 20-25 characters instead of 15
                        if len(path_parts) <= 2:
                            return Path(dir_path).name[:dir_width]
                        elif len(path_parts) == 3:
                            return "/".join(path_parts[-2:])[:dir_width]
                        else:
                            # For longer paths, show the last 3 parts
                            return "/".join(path_parts[-3:])[:dir_width]
                    
                    all_dirs_for_comparison = [dir_path] + sorted_other_dirs
                    
                    # Create header
                    header = "    FILENAME".ljust(filename_width)
                    current_dir_name = get_meaningful_dir_name(dir_path)
                    header += f" | {current_dir_name.ljust(dir_width)}"
                    for other_dir in sorted_other_dirs[:5]:
                        other_dir_name = get_meaningful_dir_name(other_dir)
                        header += f" | {other_dir_name.ljust(dir_width)}"
                    console.print(header)
                    console.print("    " + "-" * (len(header) - 4))
                    
                    # Add a clear comparison header
                    if debug or len(sorted_other_dirs) > 2:
                        console.print(f"    [dim]Comparing: {dir_path}[/dim]")
                        for i, other_dir in enumerate(sorted_other_dirs[:5], 1):
                            console.print(f"    [dim]vs {i}: {other_dir}[/dim]")
                    
                    # Show files with directory presence/absence
                    shown_files = 0
                    
                    # Get all unique filenames across all directories in this comparison
                    all_filenames = set()
                    for file_info in all_indexed_files:
                        parent_dir = str(Path(file_info["path"]).parent)
                        if parent_dir == dir_path or parent_dir in other_dirs:
                            all_filenames.add(Path(file_info["path"]).name)
                    
                    # Sort filenames for consistent display
                    sorted_filenames = sorted(all_filenames)
                    
                    for filename in sorted_filenames[:30]:  # Limit to 30 files
                        # Handle long filenames by truncating
                        display_filename = filename
                        if len(filename) > filename_width - 4:
                            display_filename = filename[:filename_width - 7] + "..."
                        
                        row = f"    {display_filename.ljust(filename_width - 2)}"
                        
                        # Check if file exists in current directory
                        current_dir_has_file = False
                        for file_info in all_indexed_files:
                            if (Path(file_info["path"]).parent == Path(dir_path) and 
                                Path(file_info["path"]).name == filename):
                                current_dir_has_file = True
                                break
                        
                        if current_dir_has_file:
                            row += f" | {'✓'.center(dir_width)}"
                        else:
                            row += f" | {'✗'.center(dir_width)}"
                        
                        # Check if file exists in other directories
                        for other_dir in sorted_other_dirs[:5]:
                            other_dir_has_file = False
                            for file_info in all_indexed_files:
                                if (Path(file_info["path"]).parent == Path(other_dir) and 
                                    Path(file_info["path"]).name == filename):
                                    other_dir_has_file = True
                                    break
                            
                            if other_dir_has_file:
                                row += f" | {'✓'.center(dir_width)}"
                            else:
                                row += f" | {'✗'.center(dir_width)}"
                        
                        console.print(row)
                        
                        # Show full filename if truncated
                        if len(filename) > filename_width - 4:
                            console.print(f"    [dim]Full: {filename}[/dim]")
                        
                        shown_files += 1
                    
                    if len(all_filenames) > 30:
                        console.print(f"    ... and {len(all_filenames) - 30} more files")
                    
                    # Show summary
                    console.print(f"\n    [dim]Legend: ✓ = file exists in directory, ✗ = file missing[/dim]")
                    console.print(f"    [dim]Comparing {get_meaningful_dir_name(dir_path)} with {len(sorted_other_dirs)} other directories[/dim]")
                    if len(sorted_other_dirs) > 5:
                        console.print(f"    [dim]Showing first 5 of {len(sorted_other_dirs)} directories[/dim]")
                    
                    # Show if there are identical directories we skipped
                    identical_dirs = []
                    current_signature = None
                    for file_info in all_indexed_files:
                        if str(Path(file_info["path"]).parent) == dir_path and file_info.get("hash"):
                            if current_signature is None:
                                current_signature = set()
                            current_signature.add(file_info["hash"])
                    
                    if current_signature:
                        for signature, dirs_list in dir_signatures.items():
                            if signature == tuple(sorted(current_signature)) and len(dirs_list) > 1:
                                identical_dirs = [d[0] for d in dirs_list if d[0] != dir_path]
                                break
                    
                    if identical_dirs:
                        console.print(f"    [dim]Note: Identical directories skipped: {', '.join(identical_dirs[:3])}{'...' if len(identical_dirs) > 3 else ''}[/dim]")
    else:
        console.print(f"[bold yellow]Found {len(dups)} duplicate groups[/bold yellow]")
        for i, group in enumerate(dups[:10], 1):
            console.print(f"\n[bold]Group {i}[/bold] ({len(group)} files):")
            for fp in group:
                console.print(f"  {fp}")
        if len(dups) > 10:
            console.print(f"\n... and {len(dups) - 10} more groups")
    
    # Export machine-readable data for visualization
    if export_data:
        export_format = "json"
        if export_data.endswith('.csv'):
            export_format = "csv"
        
        # Prepare comprehensive data for visualization
        viz_data = {
            "metadata": {
                "paths": paths,
                "command": "duplicates",
                "timestamp": datetime.datetime.now().isoformat(),
                "total_files": len(all_indexed_files),
                "total_directories": len(set(str(Path(f["path"]).parent) for f in all_indexed_files)),
                "duplicate_groups": len(combined_dups)
            },
            "directories": {},
            "duplicate_groups": [],
            "file_matrix": []
        }
        
        # Analyze directories
        all_dirs = set()
        for file_info in all_indexed_files:
            dir_path = str(Path(file_info["path"]).parent)
            all_dirs.add(dir_path)
        
        # Build directory analysis
        for dir_path in sorted(all_dirs):
            dir_files = [f for f in all_indexed_files if str(Path(f["path"]).parent) == dir_path]
            duplicate_files = set()
            
            for file_info in dir_files:
                for group in combined_dups:
                    if file_info["path"] in group:
                        duplicate_files.add(file_info["path"])
                        break
            
            viz_data["directories"][dir_path] = {
                "total_files": len(dir_files),
                "duplicate_files": list(duplicate_files),
                "unique_files": [f["path"] for f in dir_files if f["path"] not in duplicate_files],
                "total_size": sum(f["size"] for f in dir_files),
                "duplicate_percentage": (len(duplicate_files) / len(dir_files) * 100) if dir_files else 0
            }
        
        # Add duplicate groups
        for i, group in enumerate(combined_dups):
            viz_data["duplicate_groups"].append({
                "group_id": i + 1,
                "files": group,
                "size": len(group),
                "directories": list(set(str(Path(f).parent) for f in group))
            })
        
        # Build file presence matrix for visualization
        if group_by_dir and len(all_dirs) <= 10:  # Only for manageable number of directories
            all_filenames = set()
            for file_info in all_indexed_files:
                all_filenames.add(Path(file_info["path"]).name)
            
            sorted_dirs = sorted(all_dirs)
            sorted_filenames = sorted(all_filenames)
            
            for filename in sorted_filenames:
                row = {"filename": filename}
                for dir_path in sorted_dirs:
                    has_file = any(
                        Path(f["path"]).name == filename and str(Path(f["path"]).parent) == dir_path
                        for f in all_indexed_files
                    )
                    row[dir_path] = has_file
                viz_data["file_matrix"].append(row)
        
        # Save export data
        if export_format == "json":
            import json
            with open(export_data, 'w') as f:
                json.dump(viz_data, f, indent=2, default=str)
        else:  # csv
            import csv
            if viz_data["file_matrix"]:  # Export matrix if available
                with open(export_data, 'w', newline='') as f:
                    if viz_data["file_matrix"]:
                        fieldnames = ["filename"] + sorted(all_dirs)
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(viz_data["file_matrix"])
            else:  # Export directory summary
                with open(export_data, 'w', newline='') as f:
                    fieldnames = ["directory", "total_files", "duplicate_files", "unique_files", "total_size", "duplicate_percentage"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for dir_path, data in viz_data["directories"].items():
                        writer.writerow({
                            "directory": dir_path,
                            "total_files": data["total_files"],
                            "duplicate_files": len(data["duplicate_files"]),
                            "unique_files": len(data["unique_files"]),
                            "total_size": data["total_size"],
                            "duplicate_percentage": data["duplicate_percentage"]
                        })
        
        console.print(f"[green]Data exported to:[/green] {export_data} ({export_format})")
    
    # Close output file if opened
    if output_capture:
        output_capture.file.close()
        console.print(f"[green]Output saved to:[/green] {output}")


@app.command()
def generate(
    path: str = typer.Argument(..., help="Directory path to analyze"),
    target_base: str = typer.Option("/mnt/storage", "--target", "-t", help="Target base for generated commands"),
    output_file: str = typer.Option("consolidate.sh", "--output", "-o", help="Output bash script"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Generate bash commands for consolidation (read-only analysis)."""
    if verbose:
        logging.basicConfig(level=logging.INFO)

    console.print(f"[bold blue]Generating commands for:[/bold blue] {path}")

    indexer = StorageIndexer(path, read_only=True)
    result = indexer.scan_directory()
    indexer.compute_hashes()

    output_gen = OutputGenerator(indexer)
    analysis = {"scan_result": result, "duplicates": indexer.find_duplicates()}
    commands = output_gen.generate_bash_commands(analysis, target_base)

    with open(output_file, "w") as f:
        f.write("\n".join(commands))

    console.print(Panel(
        f"[bold green]Script generated:[/bold green] {output_file}\n"
        f"Commands: {len(commands)}\n"
        f"[bold]Review before executing![/bold]",
        title="Done",
    ))


@app.command()
def analyze(
    path: str = typer.Argument(..., help="Directory path to analyze"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, csv"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Full storage analysis with recommendations (read-only)."""
    if verbose:
        logging.basicConfig(level=logging.INFO)

    console.print(f"[bold blue]Analyzing:[/bold blue] {path}")

    indexer = StorageIndexer(path, read_only=True)
    result = indexer.scan_directory()
    indexer.compute_hashes()
    dups = indexer.find_duplicates()

    analysis = {
        "total_files": result["total_files"],
        "total_size": sum(f["size"] for f in result["files"]),
        "duplicate_groups": len(dups),
        "temporary_files": len([f for f in result["files"] if f["is_temporary"]]),
        "system_files": len([f for f in result["files"] if f["is_system_file"]]),
        "permission_denied_dirs": result.get("permission_denied_dirs", []),
    }

    console.print(Panel(
        f"[bold]Files:[/bold] {analysis['total_files']:,}\n"
        f"[bold]Size:[/bold] {analysis['total_size']:,} bytes\n"
        f"[bold]Duplicates:[/bold] {analysis['duplicate_groups']}\n"
        f"[bold]Temp files:[/bold] {analysis['temporary_files']}\n"
        f"[bold]System files:[/bold] {analysis['system_files']}",
        title="Storage Analysis",
    ))

    if analysis["permission_denied_dirs"]:
        console.print(f"\n[bold yellow]Permission denied for {len(analysis['permission_denied_dirs'])} directories[/bold yellow]")

    if output_file:
        output_gen = OutputGenerator(indexer)
        full_analysis = {"scan_result": result, "duplicates": dups, "summary": analysis}
        if output_format == "csv":
            ok = output_gen.generate_csv_summary(full_analysis, output_file)
        else:
            ok = output_gen.generate_json_report(full_analysis, output_file)
        if ok:
            console.print(f"\n[green]Analysis saved to:[/green] {output_file}")
        else:
            console.print(f"\n[red]Failed to save to:[/red] {output_file}")


# ---------------------------------------------------------------------------
# Treemap subcommands
# ---------------------------------------------------------------------------

treemap_app = typer.Typer(
    name="treemap",
    help="Hash-identified directory tree maps for cross-device comparison.",
    no_args_is_help=True,
)
app.add_typer(treemap_app, name="treemap")


@treemap_app.command("scan")
def treemap_scan(
    paths: List[str] = typer.Argument(..., help="One or more root directories to scan"),
    label: Optional[str] = typer.Option(None, "--label", "-l",
        help="Label to save this treemap under (e.g. 'MyBackupDrive'). "
             "If omitted the directory name is used."),
    slow: bool = typer.Option(False, "--slow", "-s",
        help="Use SHA-256 file content hashing instead of fast metadata hashing"),
    include_hidden: bool = typer.Option(False, "--hidden",
        help="Include hidden files and directories"),
    ignore_system: bool = typer.Option(False, "--ignore-system",
        help="Skip known system directories and files (Recycle Bin, pagefile, node_modules, .git, etc.)"),
    dir_pattern: Optional[str] = typer.Option(None, "--dir-pattern", "-p",
        help="Comma-separated wildcard patterns — only descend into directories whose names match "
             "(e.g. 'photos*,videos,20*'). Applied at depth > 0."),
    media_only: bool = typer.Option(False, "--media-only", "-m",
        help="Only hash recognised media and document file types "
             "(images, video, audio, PDF, Office docs, archives)"),
    sparse: bool = typer.Option(False, "--sparse",
        help="Display only directories suspected of being duplicates (prune unique subtrees)"),
    save: bool = typer.Option(True, "--save/--no-save",
        help="Persist the treemap to the store for later comparison"),
    force: bool = typer.Option(False, "--force", "-f",
        help="Force overwrite existing cache without prompting (creates versioned file)"),
    store_dir: Optional[str] = typer.Option(None, "--store",
        help="Override the treemap store directory (default: ~/.storage-wizard/treemaps/)"),
    display_depth: Optional[int] = typer.Option(None, "--depth", "-d",
        help="Max display depth (default: unlimited)"),
    compare_with: Optional[str] = typer.Option(None, "--compare", "-c",
        help="Comma-separated labels of saved treemaps to compare against after scanning"),
) -> None:
    """Scan directories and build hash-identified treemaps."""
    store = Path(store_dir) if store_dir else None
    patterns = [p.strip() for p in dir_pattern.split(",")] if dir_pattern else []
    builder = _treemap.TreemapBuilder(
        slow=slow,
        include_hidden=include_hidden,
        ignore_system=ignore_system,
        dir_patterns=patterns,
        media_only=media_only,
    )
    mode_str = "[yellow]slow (SHA-256)[/yellow]" if slow else "[green]fast (metadata)[/green]"
    flags = []
    if ignore_system:
        flags.append("ignore-system")
    if media_only:
        flags.append("media-only")
    if patterns:
        flags.append(f"dir-pattern={dir_pattern}")
    if sparse:
        flags.append("sparse")
    flag_str = f"  [dim]{', '.join(flags)}[/dim]" if flags else ""
    console.print(f"[bold]Treemap scan[/bold]  mode={mode_str}{flag_str}")

    scanned: List[tuple] = []
    for raw_path in paths:
        root = str(Path(raw_path).resolve())
        lbl = label if (label and len(paths) == 1) else (label + ":" + Path(root).name if label else Path(root).name)
        console.print(f"  Scanning [cyan]{root}[/cyan] → label [bold]{lbl}[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as prog:
            task = prog.add_task("Scanning...", total=None)
            node = builder.build(root, progress_task=task, progress=prog)

        scanned_at = datetime.datetime.now().isoformat()

        denied = builder.permission_denied
        if denied:
            console.print(
                f"  [bold yellow]⚠ Permission denied for {len(denied)} "
                f"path{'s' if len(denied) != 1 else ''}[/bold yellow] "
                f"[dim](skipped, not included in hash)[/dim]"
            )
            for p in denied[:5]:
                console.print(f"    [dim red]{p}[/dim red]")
            if len(denied) > 5:
                console.print(f"    [dim]… and {len(denied) - 5} more[/dim]")

        if save:
            dest = _treemap.save_treemap(node, lbl, root, slow, store, force)
            console.print(f"  [green]Saved →[/green] {dest}")

        scanned.append((lbl, node, root, scanned_at))

    # Display
    labeled = [(lbl, node) for lbl, node, _, _ in scanned]

    extra: List[tuple] = []
    if compare_with:
        for clbl in compare_with.split(","):
            clbl = clbl.strip()
            if not clbl:
                continue
            try:
                meta, cnode = _treemap.load_treemap(clbl, store)
                extra.append((clbl, cnode))
                console.print(f"  Loaded saved treemap [bold]{clbl}[/bold] ({meta.get('root_path', '')}")
            except FileNotFoundError as exc:
                console.print(f"  [red]{exc}[/red]")

    all_trees = labeled + extra
    dup_map = _treemap.find_duplicate_nodes(all_trees)
    _treemap.display_trees(all_trees, dup_map, max_depth=display_depth, sparse=sparse)

    if dup_map:
        console.print(f"[bold yellow]{len(dup_map)}[/bold yellow] duplicate subtree hash(es) found across {len(all_trees)} tree(s).")


@treemap_app.command("compare")
def treemap_compare(
    labels: List[str] = typer.Argument(...,
        help="Labels of saved treemaps to compare (space-separated)"),
    store_dir: Optional[str] = typer.Option(None, "--store",
        help="Override the treemap store directory"),
    display_depth: Optional[int] = typer.Option(None, "--depth", "-d",
        help="Max display depth (default: unlimited)"),
    sparse: bool = typer.Option(False, "--sparse",
        help="Display only directories suspected of being duplicates (prune unique subtrees)"),
    min_size: Optional[str] = typer.Option(None, "--min-size", "-s",
        help="Minimum size threshold for duplicates (e.g., 100MB, 1GB, 500KB)"),
    side_by_side: bool = typer.Option(False, "--side-by-side",
        help="Show side-by-side comparison of differences (more intuitive than sparse view)"),
) -> None:
    """Compare previously saved treemaps by label."""
    store = Path(store_dir) if store_dir else None
    trees: List[tuple] = []
    for lbl in labels:
        try:
            meta, node = _treemap.load_treemap(lbl, store)
            trees.append((lbl, node))
            console.print(f"  Loaded [bold]{lbl}[/bold]  root={meta.get('root_path', '')}  scanned={meta.get('scanned_at', '')}")
        except FileNotFoundError as exc:
            console.print(f"  [red]{exc}[/red]")

    if not trees:
        console.print("[red]No treemaps loaded — nothing to compare.[/red]")
        raise typer.Exit(1)

    dup_map = _treemap.find_duplicate_nodes(trees)
    
    # Filter duplicates by minimum size if specified
    if min_size:
        min_size_bytes = _parse_size_string(min_size)
        filtered_dup_map = {}
        for hash_val, entries in dup_map.items():
            # Check if any node in this duplicate group meets the size threshold
            if any(entry[1].size >= min_size_bytes for entry in entries):
                filtered_dup_map[hash_val] = entries
        dup_map = filtered_dup_map
        
        if dup_map:
            console.print(f"[bold green]Filtered to duplicates ≥ {min_size}[/bold green]")
        else:
            console.print(f"[yellow]No duplicates found ≥ {min_size}[/yellow]")
            return
    
    # Choose display method
    if side_by_side:
        _display_side_by_side_comparison(trees, dup_map, display_depth)
    else:
        _treemap.display_trees(trees, dup_map, max_depth=display_depth, sparse=sparse)

    if dup_map:
        console.print(f"[bold yellow]{len(dup_map)}[/bold yellow] duplicate subtree hash(es) found.")
        if min_size:
            console.print(f"[dim]Showing only duplicates ≥ {min_size}[/dim]")
        if side_by_side:
            console.print(f"[dim]Side-by-side comparison view[/dim]")
    else:
        console.print("[green]No duplicate subtrees found.[/green]")


@treemap_app.command("list")
def treemap_list(
    store_dir: Optional[str] = typer.Option(None, "--store",
        help="Override the treemap store directory"),
) -> None:
    """List all saved treemaps."""
    store = Path(store_dir) if store_dir else None
    maps = _treemap.list_saved_treemaps(store)
    if not maps:
        console.print("[dim]No saved treemaps found.[/dim]")
        return
    table = Table(title="Saved Treemaps", show_lines=True)
    table.add_column("Label", style="bold cyan")
    table.add_column("Root Path")
    table.add_column("Scanned At")
    table.add_column("Mode")
    for m in maps:
        table.add_row(
            m["label"],
            m["root_path"],
            m["scanned_at"],
            "slow" if m["slow"] else "fast",
        )
    console.print(table)


@treemap_app.command("label")
def treemap_label(
    source: str = typer.Argument(...,
        help="Label of a saved treemap OR a directory path to scan on-the-fly"),
    label_name: Optional[str] = typer.Option(None, "--label", "-l",
        help="Override label text (used when source is a path)"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o",
        help="Write label to this file instead of stdout"),
    depth: int = typer.Option(3, "--depth", "-d",
        help="Max depth for the printed tree (default: 3)"),
    slow: bool = typer.Option(False, "--slow", "-s",
        help="Use SHA-256 hashing when scanning on-the-fly"),
    store_dir: Optional[str] = typer.Option(None, "--store",
        help="Override the treemap store directory"),
    qr: bool = typer.Option(False, "--qr",
        help="Include a QR code containing the first-level directory tree (scannable)"),
    qr_image: Optional[str] = typer.Option(None, "--qr-image",
        help="Generate a 1\"×1\" PNG QR code image suitable for printing on small labels (specify output path)"),
    qr_size: float = typer.Option(1.0, "--qr-size",
        help="Physical size of QR image in inches (default: 1.0)"),
    qr_dpi: int = typer.Option(300, "--qr-dpi",
        help="DPI resolution for QR image (default: 300)"),
) -> None:
    """Generate a printable plain-text label for attaching to a physical drive."""
    store = Path(store_dir) if store_dir else None
    src_path = Path(source)

    if src_path.is_dir():
        # Scan on-the-fly
        root = str(src_path.resolve())
        lbl = label_name or src_path.name
        console.print(f"Scanning [cyan]{root}[/cyan] for label...")
        builder = _treemap.TreemapBuilder(slow=slow)
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as prog:
            task = prog.add_task("Scanning...", total=None)
            node = builder.build(root, progress_task=task, progress=prog)
        scanned_at = datetime.datetime.now().isoformat()
    else:
        # Load from store
        lbl = label_name or source
        try:
            meta, node = _treemap.load_treemap(source, store)
        except FileNotFoundError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
        root = meta.get("root_path", source)
        slow = meta.get("slow", False)
        scanned_at = meta.get("scanned_at", "unknown")

    # Generate QR code image if requested
    if qr_image:
        _treemap.generate_qr_image(
            node, lbl, root, scanned_at, slow,
            output_path=qr_image,
            size_inches=qr_size,
            dpi=qr_dpi,
        )
        # If only QR image requested, we're done
        if not qr and not output_file:
            return

    # Generate text label (ASCII QR or standard)
    if qr:
        text = _treemap.generate_qr_label(node, lbl, root, scanned_at, slow)
    else:
        text = _treemap.generate_printable_label(node, lbl, root, scanned_at, slow, max_depth=depth)

    if output_file:
        Path(output_file).write_text(text + "\n", encoding="utf-8")
        console.print(f"[green]Label written to:[/green] {output_file}")
    else:
        console.print(text)


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
