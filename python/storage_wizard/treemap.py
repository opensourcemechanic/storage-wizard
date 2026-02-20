"""
Treemap plugin for Storage Wizard.

Builds a hash-identified tree of directory nodes so that identical or similar
subtrees can be detected across multiple roots / removable devices.

Hash modes
----------
fast (default)
    Each node's hash is derived from the sorted list of
    (child_name, child_mtime, child_size) tuples.  Pure metadata — no file I/O
    beyond a single os.scandir pass.

slow
    Each file's hash is a SHA-256 of its content.  Node hashes are then derived
    from the sorted list of (child_name, child_sha256) tuples.  Accurate even
    when timestamps differ between copies.

Persistence
-----------
Treemaps are saved as JSON files in a configurable store directory
(default: ~/.storage-wizard/treemaps/).  Each saved map records the label
(e.g. "MyBackupDrive"), the root path used at scan time, and the full node
tree.  At comparison time you supply the labels of the saved maps you want to
compare, plus optional labels for currently-mounted paths.

Display
-------
Duplicate subtrees (same node hash) are highlighted in the same Rich colour.
Up to 12 distinct duplicate colours are cycled.  Unique nodes are shown in the
default terminal colour.

Printable label
---------------
A plain-text summary limited to a configurable depth (default 3) is produced
for attaching to physical drives.  It includes the label, scan date, total
size, file count, and the top-level tree structure with per-node sizes.
"""

from __future__ import annotations

import datetime
import fnmatch
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

# ---------------------------------------------------------------------------
# Constants  (EMPTY_HASH is defined after _hash_from_parts below)
# ---------------------------------------------------------------------------

# System directory / file names to skip when --ignore-system is set
SYSTEM_NAMES: Set[str] = {
    "$recycle.bin", "recycler", "system volume information",
    "pagefile.sys", "hiberfil.sys", "swapfile.sys",
    "thumbs.db", "desktop.ini", ".ds_store", ".spotlight-v100",
    ".trashes", ".fseventsd", ".temporaryitems", "lost+found",
    "$windows.~bt", "$windows.~ws", "windows", "windows.old",
    "program files", "program files (x86)", "programdata",
    "__pycache__", ".git", ".svn", ".hg", "node_modules",
}

# Common user-generated media and document extensions
MEDIA_EXTENSIONS: Set[str] = {
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".heic", ".heif", ".raw", ".cr2", ".cr3", ".nef",
    ".arw", ".dng", ".orf", ".rw2", ".pef", ".srw",
    # Video
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v",
    ".mpg", ".mpeg", ".3gp", ".webm", ".mts", ".m2ts",
    # Audio
    ".mp3", ".flac", ".aac", ".wav", ".ogg", ".wma", ".m4a",
    ".aiff", ".opus",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".rtf", ".txt", ".md", ".csv",
    # Archives (user-created)
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
}

# ---------------------------------------------------------------------------
# Colour palette for duplicate highlighting (Rich colour names)
# ---------------------------------------------------------------------------
_DUP_COLOURS = [
    "bright_red",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
    "orange3",
    "deep_pink3",
    "chartreuse3",
    "cornflower_blue",
    "gold3",
    "medium_orchid",
]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class TreeNode:
    """Represents one directory node in the scanned tree."""

    __slots__ = (
        "name", "path", "hash", "size", "file_count",
        "children", "depth", "mtime",
    )

    def __init__(self, name: str, path: str, depth: int = 0):
        self.name: str = name
        self.path: str = path
        self.hash: str = ""
        self.size: int = 0
        self.file_count: int = 0
        self.children: List["TreeNode"] = []
        self.depth: int = depth
        self.mtime: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "hash": self.hash,
            "size": self.size,
            "file_count": self.file_count,
            "mtime": self.mtime,
            "depth": self.depth,
            "children": [c.to_dict() for c in self.children],
        }

    @staticmethod
    def from_dict(d: dict, depth: int = 0) -> "TreeNode":
        node = TreeNode(d["name"], d["path"], depth)
        node.hash = d["hash"]
        node.size = d["size"]
        node.file_count = d["file_count"]
        node.mtime = d.get("mtime", 0.0)
        node.children = [TreeNode.from_dict(c, depth + 1) for c in d.get("children", [])]
        return node


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            while True:
                buf = fh.read(chunk)
                if not buf:
                    break
                h.update(buf)
    except OSError:
        return "error"
    return h.hexdigest()


def _hash_from_parts(parts: List[Tuple]) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(repr(part).encode())
    return h.hexdigest()[:16]


# The canonical hash for a completely empty directory
EMPTY_HASH: str = _hash_from_parts([("empty",)])


def _format_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def _is_system(name: str) -> bool:
    """True if the entry name matches a known system directory/file."""
    return name.lower() in SYSTEM_NAMES


def _matches_patterns(name: str, patterns: List[str]) -> bool:
    """True if name matches any of the given fnmatch wildcard patterns."""
    nl = name.lower()
    return any(fnmatch.fnmatch(nl, p.lower()) for p in patterns)


def _ext_is_media(name: str) -> bool:
    """True if the file extension is in the predefined media/document set."""
    return Path(name).suffix.lower() in MEDIA_EXTENSIONS


# ---------------------------------------------------------------------------
# Tree builder
# ---------------------------------------------------------------------------

class TreemapBuilder:
    """Recursively scans directories and builds a TreeNode hierarchy."""

    def __init__(
        self,
        slow: bool = False,
        include_hidden: bool = False,
        ignore_system: bool = False,
        dir_patterns: Optional[List[str]] = None,
        media_only: bool = False,
    ):
        self.slow = slow
        self.include_hidden = include_hidden
        self.ignore_system = ignore_system
        self.dir_patterns: List[str] = dir_patterns or []
        self.media_only = media_only
        self._file_count_total = 0
        self.permission_denied: List[str] = []

    def build(self, root: str, progress_task=None, progress=None) -> TreeNode:
        self.permission_denied = []
        root_path = Path(root).resolve()
        node = self._scan(root_path, depth=0, progress_task=progress_task, progress=progress)
        return node

    def _scan(self, path: Path, depth: int, progress_task=None, progress=None) -> TreeNode:
        node = TreeNode(path.name or str(path), str(path), depth)

        if progress and progress_task is not None:
            indent = "  " * min(depth, 4)
            display = str(path) if depth == 0 else path.name
            progress.update(progress_task, description=f"{indent}[cyan]{display}[/cyan]")

        try:
            entries = list(os.scandir(path))
        except PermissionError:
            node.hash = "permission-denied"
            self.permission_denied.append(str(path))
            if progress and progress_task is not None:
                indent = "  " * min(depth, 4)
                progress.update(
                    progress_task,
                    description=f"{indent}[red]permission denied:[/red] [dim]{path.name}[/dim]",
                )
            return node

        dirs = []
        files = []
        for e in entries:
            if not self.include_hidden and e.name.startswith("."):
                continue
            if self.ignore_system and _is_system(e.name):
                continue
            try:
                is_dir = e.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                # Apply directory name pattern filter (only descend matching dirs)
                if self.dir_patterns and depth > 0:
                    if not _matches_patterns(e.name, self.dir_patterns):
                        continue
                dirs.append(e)
            else:
                files.append(e)

        # Recurse into subdirectories
        for d in sorted(dirs, key=lambda e: e.name.lower()):
            child = self._scan(Path(d.path), depth + 1, progress_task, progress)
            node.children.append(child)
            node.size += child.size
            node.file_count += child.file_count

        # Process files
        file_parts: List[Tuple] = []
        for f in sorted(files, key=lambda e: e.name.lower()):
            # Apply media-only filter
            if self.media_only and not _ext_is_media(f.name):
                continue
            try:
                st = f.stat(follow_symlinks=False)
            except PermissionError:
                self.permission_denied.append(f.path)
                continue
            except OSError:
                continue
            size = st.st_size
            mtime = st.st_mtime
            node.size += size
            node.file_count += 1
            self._file_count_total += 1

            if self.slow:
                fhash = _sha256_file(f.path)
                file_parts.append((f.name, fhash))
            else:
                file_parts.append((f.name, int(mtime), size))

            if progress and progress_task is not None:
                progress.advance(progress_task)

        # Build child hash parts
        child_parts: List[Tuple] = [(c.name, c.hash) for c in node.children]

        # Node hash = hash of sorted file parts + sorted child hashes
        all_parts = sorted(file_parts) + sorted(child_parts)
        if all_parts:
            node.hash = _hash_from_parts(all_parts)
        else:
            node.hash = EMPTY_HASH

        # Record directory mtime
        try:
            node.mtime = path.stat().st_mtime
        except OSError:
            node.mtime = 0.0

        return node


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

DEFAULT_STORE = Path.home() / ".storage-wizard" / "treemaps"


def _store_path(store_dir: Path, label: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in label)
    return store_dir / f"{safe}.json"


def save_treemap(node: TreeNode, label: str, root_path: str,
                 slow: bool, store_dir: Optional[Path] = None) -> Path:
    """Persist a treemap to the store directory."""
    store = store_dir or DEFAULT_STORE
    store.mkdir(parents=True, exist_ok=True)
    dest = _store_path(store, label)
    payload = {
        "label": label,
        "root_path": root_path,
        "slow": slow,
        "scanned_at": datetime.datetime.now().isoformat(),
        "tree": node.to_dict(),
    }
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def load_treemap(label: str, store_dir: Optional[Path] = None) -> Tuple[dict, TreeNode]:
    """Load a saved treemap by label. Returns (metadata_dict, root_node)."""
    store = store_dir or DEFAULT_STORE
    dest = _store_path(store, label)
    if not dest.exists():
        raise FileNotFoundError(f"No saved treemap for label '{label}' in {store}")
    payload = json.loads(dest.read_text(encoding="utf-8"))
    node = TreeNode.from_dict(payload["tree"])
    return payload, node


def list_saved_treemaps(store_dir: Optional[Path] = None) -> List[dict]:
    """Return metadata for all saved treemaps."""
    store = store_dir or DEFAULT_STORE
    if not store.exists():
        return []
    results = []
    for p in sorted(store.glob("*.json")):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            results.append({
                "label": payload.get("label", p.stem),
                "root_path": payload.get("root_path", ""),
                "scanned_at": payload.get("scanned_at", ""),
                "slow": payload.get("slow", False),
                "file": str(p),
            })
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# Duplicate detection across trees
# ---------------------------------------------------------------------------

def _collect_hashes(node: TreeNode, mapping: Dict[str, List[Tuple[str, TreeNode]]],
                    label: str) -> None:
    """Walk tree and populate hash → [(label, node)] mapping."""
    if node.hash and node.hash not in ("permission-denied",):
        mapping.setdefault(node.hash, []).append((label, node))
    for child in node.children:
        _collect_hashes(child, mapping, label)


def find_duplicate_nodes(
    labeled_trees: List[Tuple[str, TreeNode]]
) -> Dict[str, List[Tuple[str, TreeNode]]]:
    """
    Return only hashes that appear more than once (across any combination of
    trees), mapping hash → [(label, node), ...].
    Empty-dir nodes (EMPTY_HASH) are excluded — they are reported separately.
    """
    mapping: Dict[str, List[Tuple[str, TreeNode]]] = {}
    for label, root in labeled_trees:
        _collect_hashes(root, mapping, label)
    return {
        h: entries
        for h, entries in mapping.items()
        if len(entries) > 1 and h != EMPTY_HASH
    }


def collect_empty_nodes(
    labeled_trees: List[Tuple[str, TreeNode]]
) -> List[Tuple[str, TreeNode]]:
    """Return all nodes whose hash equals EMPTY_HASH (truly empty directories)."""
    result: List[Tuple[str, TreeNode]] = []

    def _walk(label: str, node: TreeNode) -> None:
        if node.hash == EMPTY_HASH:
            result.append((label, node))
        for child in node.children:
            _walk(label, child)

    for label, root in labeled_trees:
        _walk(label, root)
    return result


def build_sparse_tree(
    root: TreeNode,
    dup_hashes: Set[str],
) -> Optional[TreeNode]:
    """
    Return a pruned copy of *root* containing only nodes whose hash is in
    *dup_hashes* (or ancestors needed to reach them).  Returns None if no
    duplicate nodes exist under this root.
    """
    # Leaf: this node itself is a duplicate
    if root.hash in dup_hashes:
        clone = TreeNode(root.name, root.path, root.depth)
        clone.hash = root.hash
        clone.size = root.size
        clone.file_count = root.file_count
        clone.mtime = root.mtime
        return clone

    # Recurse into children
    kept_children = []
    for child in root.children:
        pruned = build_sparse_tree(child, dup_hashes)
        if pruned is not None:
            kept_children.append(pruned)

    if not kept_children:
        return None

    # Return a shell of this node containing only the relevant subtrees
    clone = TreeNode(root.name, root.path, root.depth)
    clone.hash = root.hash
    clone.size = root.size
    clone.file_count = root.file_count
    clone.mtime = root.mtime
    clone.children = kept_children
    return clone


# ---------------------------------------------------------------------------
# Rich terminal display
# ---------------------------------------------------------------------------

def _assign_colours(dup_map: Dict[str, List]) -> Dict[str, str]:
    """Map each duplicate hash to a colour string."""
    colour_map: Dict[str, str] = {}
    idx = 0
    for h in dup_map:
        colour_map[h] = _DUP_COLOURS[idx % len(_DUP_COLOURS)]
        idx += 1
    return colour_map


def _render_tree(
    node: TreeNode,
    colour_map: Dict[str, str],
    text: Text,
    prefix: str = "",
    is_last: bool = True,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
) -> None:
    connector = "└── " if is_last else "├── "
    extension = "    " if is_last else "│   "

    colour = colour_map.get(node.hash)
    size_str = _format_size(node.size)
    denied = node.hash == "permission-denied"
    empty = node.hash == EMPTY_HASH

    if denied:
        text.append(prefix + connector)
        text.append(f"{node.name}/", style="bold red")
        text.append("  [permission denied]\n", style="dim red")
    elif empty:
        text.append(prefix + connector)
        text.append(f"{node.name}/", style="grey46")
        text.append("  [empty]\n", style="dim grey46")
    elif colour:
        label = f"{node.name}/  [{size_str}, {node.file_count} files]"
        text.append(prefix + connector)
        text.append(label, style=f"bold {colour}")
        text.append(f"  #{node.hash[:8]}\n", style=f"dim {colour}")
    else:
        label = f"{node.name}/  [{size_str}, {node.file_count} files]"
        text.append(prefix + connector + label + "\n")

    if max_depth is not None and current_depth >= max_depth:
        if node.children:
            text.append(prefix + extension + f"  [dim]({len(node.children)} subdirs hidden)[/dim]\n")
        return

    for i, child in enumerate(node.children):
        _render_tree(
            child, colour_map, text,
            prefix=prefix + extension,
            is_last=(i == len(node.children) - 1),
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )


def display_trees(
    labeled_trees: List[Tuple[str, TreeNode]],
    dup_map: Dict[str, List[Tuple[str, TreeNode]]],
    max_depth: Optional[int] = None,
    sparse: bool = False,
) -> None:
    colour_map = _assign_colours(dup_map)
    dup_hashes: Set[str] = set(dup_map.keys())

    # --- Legend panel ---
    console.print()
    if dup_map:
        legend = Text("Duplicate subtrees share the same colour  ", style="bold")
        for h, colour in list(colour_map.items())[:8]:
            entries = dup_map[h]
            labels = ", ".join(f"{lbl}:{n.name}" for lbl, n in entries[:3])
            legend.append(f"  [{h[:6]}] ", style=f"bold {colour}")
            legend.append(f"{labels}  ", style=f"dim {colour}")
        legend.append("  ")  
        legend.append("  [empty dir] ", style="grey46")
        console.print(Panel(legend, title="Legend", border_style="dim"))
    else:
        console.print("[dim]No duplicate subtrees found across the supplied trees.[/dim]")

    # --- Per-tree panels ---
    for label, root in labeled_trees:
        display_root = root
        if sparse:
            display_root = build_sparse_tree(root, dup_hashes)
            if display_root is None:
                console.print(
                    f"[dim]  {label}: no duplicate subtrees to show in sparse mode.[/dim]"
                )
                continue

        text = Text()
        size_str = _format_size(display_root.size)
        root_colour = colour_map.get(display_root.hash)
        root_label = f"{display_root.name or label}/  [{size_str}, {display_root.file_count} files]"
        if root_colour:
            text.append(root_label, style=f"bold {root_colour}")
            text.append(f"  #{display_root.hash[:8]}", style=f"dim {root_colour}")
        elif display_root.hash == EMPTY_HASH:
            text.append(root_label, style="grey46")
        else:
            text.append(root_label, style="bold white")
        if sparse:
            text.append("  [sparse]", style="dim yellow")
        text.append("\n")

        for i, child in enumerate(display_root.children):
            _render_tree(
                child, colour_map, text,
                prefix="",
                is_last=(i == len(display_root.children) - 1),
                max_depth=max_depth,
                current_depth=0,
            )

        console.print(Panel(text, title=f"[bold cyan]{label}[/bold cyan]  {root.path}",
                            border_style="cyan"))

    # --- Empty directories panel ---
    empty_nodes = collect_empty_nodes(labeled_trees)
    if empty_nodes:
        empty_text = Text()
        for lbl, node in empty_nodes:
            empty_text.append(f"{lbl}: ", style="dim")
            empty_text.append(node.path, style="grey46")
            empty_text.append("\n", style="grey46")
        console.print(Panel(
            empty_text,
            title="[grey46]Empty directories[/grey46]",
            border_style="grey46",
        ))


# ---------------------------------------------------------------------------
# Printable label
# ---------------------------------------------------------------------------

def _plain_tree_lines(
    node: TreeNode,
    prefix: str = "",
    is_last: bool = True,
    max_depth: int = 3,
    current_depth: int = 0,
) -> List[str]:
    connector = "└── " if is_last else "├── "
    extension = "    " if is_last else "│   "
    size_str = _format_size(node.size)
    lines = [f"{prefix}{connector}{node.name}/  {size_str}  ({node.file_count} files)"]

    if current_depth >= max_depth:
        if node.children:
            lines.append(prefix + extension + f"  ({len(node.children)} subdirs)")
        return lines

    for i, child in enumerate(node.children):
        lines.extend(_plain_tree_lines(
            child,
            prefix=prefix + extension,
            is_last=(i == len(node.children) - 1),
            max_depth=max_depth,
            current_depth=current_depth + 1,
        ))
    return lines


def generate_printable_label(
    node: TreeNode,
    label: str,
    root_path: str,
    scanned_at: str,
    slow: bool,
    max_depth: int = 3,
) -> str:
    """Return a plain-text label suitable for printing and attaching to a drive."""
    width = 72
    sep = "=" * width
    thin = "-" * width

    size_str = _format_size(node.size)
    hash_mode = "SHA-256 content" if slow else "metadata (name/date/size)"

    lines = [
        sep,
        f"  STORAGE WIZARD — DRIVE LABEL",
        f"  Label     : {label}",
        f"  Scanned   : {scanned_at}",
        f"  Root      : {root_path}",
        f"  Hash mode : {hash_mode}",
        f"  Total size: {size_str}",
        f"  Files     : {node.file_count:,}",
        f"  Root hash : {node.hash}",
        sep,
        f"  Directory tree (depth ≤ {max_depth})",
        thin,
        f"{node.name or label}/  {size_str}  ({node.file_count} files)",
    ]

    for i, child in enumerate(node.children):
        lines.extend(_plain_tree_lines(
            child,
            prefix="",
            is_last=(i == len(node.children) - 1),
            max_depth=max_depth - 1,
            current_depth=0,
        ))

    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# QR code label (ASCII art for text output)
# ---------------------------------------------------------------------------

def _qr_payload(node: TreeNode, label: str, root_path: str, scanned_at: str, slow: bool) -> str:
    """
    Return a compact JSON payload suitable for QR encoding.
    Includes label, scan metadata, and the first-level directory tree.
    """
    size_str = _format_size(node.size)
    children = []
    for child in sorted(node.children, key=lambda c: c.name.lower()):
        child_size_str = _format_size(child.size)
        children.append({
            "name": child.name,
            "size": child_size_str,
            "files": child.file_count,
            "hash": child.hash[:8],
        })

    payload = {
        "label": label,
        "scanned_at": scanned_at,
        "root_path": root_path,
        "hash_mode": "SHA-256 content" if slow else "metadata",
        "total_size": size_str,
        "total_files": node.file_count,
        "root_hash": node.hash[:8],
        "children": children,
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def generate_qr_label(
    node: TreeNode,
    label: str,
    root_path: str,
    scanned_at: str,
    slow: bool,
    qr_size: int = 12,
) -> str:
    """
    Return a printable label that includes a QR code containing the first-level
    directory tree.  The QR can be scanned to view the tree in a clean format.
    """
    import qrcode
    import qrcode.constants

    # Generate QR image (ASCII art fallback if PIL unavailable)
    try:
        qr = qrcode.QRCode(
            version=qr_size,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=2,
            border=2,
        )
        payload = _qr_payload(node, label, root_path, scanned_at, slow)
        qr.add_data(payload)
        qr.make(fit=True)

        # Render as ASCII art for terminal printing
        ascii_qr = qr.get_matrix()
        qr_lines = []
        for row in ascii_qr:
            qr_lines.append("".join("██" if cell else "  " for cell in row))
        qr_ascii = "\n".join(qr_lines)
    except Exception:
        # Fallback to a simple text placeholder if qrcode rendering fails
        qr_ascii = "[QR code generation failed]"

    # Build the printable label
    width = 72
    sep = "=" * width
    thin = "-" * width

    size_str = _format_size(node.size)
    hash_mode = "SHA-256 content" if slow else "metadata (name/date/size)"

    lines = [
        sep,
        f"  STORAGE WIZARD — DRIVE LABEL (with QR)",
        f"  Label     : {label}",
        f"  Scanned   : {scanned_at}",
        f"  Root      : {root_path}",
        f"  Hash mode : {hash_mode}",
        f"  Total size: {size_str}",
        f"  Files     : {node.file_count:,}",
        f"  Root hash : {node.hash}",
        sep,
        f"  Scan this QR code to view the first-level directory tree",
        thin,
    ]

    # Insert ASCII QR code, centered
    qr_rows = qr_ascii.splitlines()
    max_qr_len = max(len(row) for row in qr_rows) if qr_rows else 0
    for row in qr_rows:
        pad = (width - max_qr_len) // 2
        lines.append("  " + " " * pad + row)

    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# QR code image (PNG for printing on small labels)
# ---------------------------------------------------------------------------

def generate_qr_image(
    node: TreeNode,
    label: str,
    root_path: str,
    scanned_at: str,
    slow: bool,
    output_path: str,
    size_inches: float = 1.0,
    dpi: int = 300,
) -> None:
    """
    Generate a QR code as a PNG image suitable for printing on small labels.
    
    Args:
        node: Root TreeNode
        label: Drive label
        root_path: Original scan path
        scanned_at: ISO timestamp
        slow: Whether slow hashing was used
        output_path: Where to save the PNG file
        size_inches: Physical size of the QR code (default: 1.0 inch)
        dpi: Print resolution (default: 300 DPI)
    """
    import qrcode
    from PIL import Image
    
    # Calculate pixel size for the desired physical size
    pixel_size = int(size_inches * dpi)
    
    # Generate QR code with minimal error correction for smaller size
    qr = qrcode.QRCode(
        version=None,  # Auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    
    payload = _qr_payload(node, label, root_path, scanned_at, slow)
    qr.add_data(payload)
    qr.make(fit=True)
    
    # Create the QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize to exact pixel dimensions
    img = img.resize((pixel_size, pixel_size), Image.Resampling.NEAREST)
    
    # Save with DPI metadata for proper print sizing
    img.save(output_path, dpi=(dpi, dpi))
    
    console.print(f"[green]QR code image saved:[/green] {output_path}")
    console.print(f"  [dim]Size: {size_inches}\" × {size_inches}\" at {dpi} DPI ({pixel_size}×{pixel_size} pixels)[/dim]")
