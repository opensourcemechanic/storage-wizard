"""
Core storage analysis and optimization functionality.

This module provides the main classes for storage indexing, media consolidation,
and duplicate detection with optional Rust performance integration.
"""

import os
import hashlib
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import json
import logging

try:
    from . import _core
except ImportError:
    _core = None

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """File information model."""
    path: str
    size: int
    modified: int
    file_type: str
    hash: Optional[str] = None
    is_temporary: bool = False
    is_system_file: bool = False


class DirectoryTree(BaseModel):
    """Directory tree analysis model."""
    path: str
    files: List[FileInfo] = Field(default_factory=list)
    subdirectories: List[str] = Field(default_factory=list)
    total_size: int = 0
    file_count: int = 0


class StorageIndexer:
    """Read-only storage indexing class with optional Rust acceleration."""

    TEMP_PATTERNS = [
        '.tmp', '.temp', '~$', '.swp', '.bak', '.old',
        'thumbs.db', 'desktop.ini', '.ds_store',
    ]

    SYSTEM_INDICATORS = [
        'system volume information', '$recycle.bin', 'recycler',
        'pagefile.sys', 'hiberfil.sys', 'swapfile.sys',
    ]

    def __init__(self, base_path: str, db_path: Optional[str] = None, read_only: bool = True):
        self.base_path = Path(base_path)
        self.db_path = db_path or str(self.base_path / "storage_wizard.db")
        self.read_only = read_only
        self.logger = logging.getLogger(__name__)
        self._permission_denied_dirs: Set[str] = set()
        self._indexed_files: List[dict] = []
        self._hashes: List[Tuple[str, str]] = []

        if _core:
            self.rust_indexer = _core.FastIndexer(str(self.base_path))
        else:
            self.rust_indexer = None
            self.logger.info("Rust core not available; using Python-only indexing")

    def scan_directory(self, include_hidden: bool = False) -> Dict:
        """Scan directory and index files (read-only)."""
        if self.rust_indexer:
            result = self.rust_indexer.scan_directory(include_hidden)
            return dict(result)
        return self._python_scan_directory(include_hidden)

    def _python_scan_directory(self, include_hidden: bool) -> Dict:
        """Python fallback for directory scanning with permission handling."""
        files: List[dict] = []

        for root, dirs, filenames in os.walk(self.base_path):
            if not self._check_directory_permissions(root):
                dirs.clear()
                continue

            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                filenames = [f for f in filenames if not f.startswith('.')]

            for filename in filenames:
                filepath = Path(root) / filename
                try:
                    stat = filepath.stat()
                    info = FileInfo(
                        path=str(filepath),
                        size=stat.st_size,
                        modified=int(stat.st_mtime),
                        file_type=filepath.suffix.lower().lstrip('.'),
                        is_temporary=self._is_temporary_file(str(filepath)),
                        is_system_file=self._is_system_file(str(filepath)),
                    )
                    files.append(info.model_dump())
                except (OSError, PermissionError) as exc:
                    self.logger.debug("Could not access %s: %s", filepath, exc)

        self._indexed_files = files
        return {
            "files": files,
            "total_files": len(files),
            "permission_denied_dirs": list(self._permission_denied_dirs),
        }

    def _check_directory_permissions(self, directory: str) -> bool:
        """Check read permissions once per directory tree."""
        try:
            os.listdir(directory)
            return True
        except PermissionError:
            if directory not in self._permission_denied_dirs:
                self._permission_denied_dirs.add(directory)
                self.logger.warning("Permission denied: %s (skipping tree)", directory)
            return False
        except OSError as exc:
            if directory not in self._permission_denied_dirs:
                self._permission_denied_dirs.add(directory)
                self.logger.warning("Cannot access %s: %s (skipping tree)", directory, exc)
            return False

    def compute_hashes(self, batch_size: int = 100) -> List[Tuple[str, str]]:
        """Compute content hashes for duplicate detection (read-only)."""
        if self.rust_indexer:
            return self.rust_indexer.compute_hashes(batch_size)
        return self._python_compute_hashes()

    def _python_compute_hashes(self) -> List[Tuple[str, str]]:
        """Python fallback for hash computation."""
        hashes: List[Tuple[str, str]] = []
        for file_info in self._indexed_files:
            filepath = file_info["path"]
            try:
                h = hashlib.sha256()
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                file_hash = h.hexdigest()
                file_info["hash"] = file_hash
                hashes.append((filepath, file_hash))
            except (OSError, PermissionError) as exc:
                self.logger.debug("Could not hash %s: %s", filepath, exc)
        self._hashes = hashes
        return hashes

    def find_duplicates(self) -> List[List[str]]:
        """Find duplicate files based on content hash."""
        if self.rust_indexer:
            return self.rust_indexer.find_duplicates()
        return self._python_find_duplicates()

    def _python_find_duplicates(self) -> List[List[str]]:
        """Python fallback for duplicate detection."""
        hash_groups: Dict[str, List[str]] = {}
        for file_info in self._indexed_files:
            h = file_info.get("hash")
            if h:
                hash_groups.setdefault(h, []).append(file_info["path"])
        return [paths for paths in hash_groups.values() if len(paths) > 1]

    def _is_temporary_file(self, path: str) -> bool:
        filename = os.path.basename(path).lower()
        return any(p in filename for p in self.TEMP_PATTERNS)

    def _is_system_file(self, path: str) -> bool:
        path_lower = path.lower()
        return any(ind in path_lower for ind in self.SYSTEM_INDICATORS)


class OutputGenerator:
    """Generate various output formats from analysis results (all read-only)."""

    def __init__(self, indexer: StorageIndexer):
        self.indexer = indexer
        self.logger = logging.getLogger(__name__)

    def generate_bash_commands(self, analysis_result: Dict, target_base: str = "/mnt/storage") -> List[str]:
        """Generate bash commands for media consolidation."""
        commands = [
            "#!/bin/bash",
            "# Storage Wizard - Generated Consolidation Commands",
            "# *** REVIEW BEFORE EXECUTING *** This tool is read-only.",
            "",
        ]

        commands.append("# Create target directories")
        for media_type in MediaConsolidator.MEDIA_TYPES:
            commands.append(f"mkdir -p '{target_base}/{media_type.capitalize()}'")
        commands.append("")

        scan_result = analysis_result.get("scan_result", {})
        files = scan_result.get("files", [])

        commands.append("# Move media files")
        for file_info in files:
            if file_info.get("is_system_file") or file_info.get("is_temporary"):
                continue
            media_type = self._get_media_type(file_info["file_type"])
            if media_type:
                src = file_info["path"]
                dst = f"{target_base}/{media_type.capitalize()}/{os.path.basename(src)}"
                commands.append(f"cp -n '{src}' '{dst}'")
        commands.append("")

        temp_files = [f["path"] for f in files if f.get("is_temporary")]
        if temp_files:
            commands.append("# Remove temporary files")
            for tf in temp_files:
                commands.append(f"rm '{tf}'")
            commands.append("")

        duplicates = analysis_result.get("duplicates", [])
        if duplicates:
            commands.append("# Remove duplicate files (keeping first occurrence)")
            for i, group in enumerate(duplicates):
                if len(group) > 1:
                    commands.append(f"# Duplicate group {i + 1}")
                    for dup in group[1:]:
                        commands.append(f"rm '{dup}'")
            commands.append("")

        commands.append("# End of generated commands")
        return commands

    def generate_json_report(self, analysis_result: Dict, output_file: str) -> bool:
        try:
            with open(output_file, "w") as f:
                json.dump(analysis_result, f, indent=2, default=str)
            return True
        except Exception as exc:
            self.logger.error("Failed to write JSON report: %s", exc)
            return False

    def generate_csv_summary(self, analysis_result: Dict, output_file: str) -> bool:
        try:
            files = analysis_result.get("scan_result", {}).get("files", [])
            with open(output_file, "w", newline="") as csvfile:
                fieldnames = ["path", "size", "modified", "file_type", "is_temporary", "is_system_file"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for fi in files:
                    writer.writerow(fi)
            return True
        except Exception as exc:
            self.logger.error("Failed to write CSV summary: %s", exc)
            return False

    def _get_media_type(self, extension: str) -> Optional[str]:
        ext = f".{extension}" if extension and not extension.startswith(".") else extension
        for media_type, extensions in MediaConsolidator.MEDIA_TYPES.items():
            if ext in extensions:
                return media_type
        return None


class MediaConsolidator:
    """Media file type classification (read-only analysis)."""

    MEDIA_TYPES = {
        "video": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"],
        "audio": [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma"],
        "photo": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".raw", ".cr2", ".nef"],
        "document": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"],
    }


class DuplicateDetector:
    """Advanced duplicate detection and directory tree analysis."""

    def __init__(self, indexer: StorageIndexer):
        self.indexer = indexer
        self.logger = logging.getLogger(__name__)

    def suggest_tree_optimization(self) -> List[Dict]:
        """Suggest directory tree optimizations (read-only)."""
        trees = self._build_trees()
        suggestions = []
        for i, tree1 in enumerate(trees):
            for tree2 in trees[i + 1:]:
                similarity = self._calculate_tree_similarity(tree1, tree2)
                if similarity > 0.8:
                    suggestions.append({
                        "type": "duplicate_tree",
                        "tree1": tree1.path,
                        "tree2": tree2.path,
                        "similarity": similarity,
                        "recommendation": self._get_tree_recommendation(tree1, tree2),
                    })
        return suggestions

    def _build_trees(self) -> List[DirectoryTree]:
        trees: Dict[str, DirectoryTree] = {}
        for fi in self.indexer._indexed_files:
            parent = str(Path(fi["path"]).parent)
            if parent not in trees:
                trees[parent] = DirectoryTree(path=parent)
            t = trees[parent]
            t.files.append(FileInfo(**{k: fi[k] for k in FileInfo.model_fields if k in fi}))
            t.total_size += fi["size"]
            t.file_count += 1
        return list(trees.values())

    def _calculate_tree_similarity(self, t1: DirectoryTree, t2: DirectoryTree) -> float:
        max_size = max(t1.total_size, t2.total_size, 1)
        max_count = max(t1.file_count, t2.file_count, 1)
        size_diff = abs(t1.total_size - t2.total_size) / max_size
        count_diff = abs(t1.file_count - t2.file_count) / max_count
        return 1.0 - (size_diff + count_diff) / 2

    def _get_tree_recommendation(self, t1: DirectoryTree, t2: DirectoryTree) -> str:
        if t1.file_count > t2.file_count:
            return f"Keep {t1.path}, remove {t2.path}"
        elif t2.file_count > t1.file_count:
            return f"Keep {t2.path}, remove {t1.path}"
        return "Keep more recently modified tree"
