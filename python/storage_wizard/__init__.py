"""
Storage Wizard - Read-only storage indexing and optimization tool.

This package provides comprehensive storage analysis capabilities including:
- Media file consolidation analysis
- Duplicate detection and reporting
- Temporary and system file identification
- Directory tree optimization suggestions
- Optional Python-Rust performance integration
"""

__version__ = "0.1.0"
__author__ = "Storage Wizard Team"

from .core import StorageIndexer, MediaConsolidator, DuplicateDetector, OutputGenerator
from .cli import main

__all__ = [
    "StorageIndexer",
    "MediaConsolidator", 
    "DuplicateDetector",
    "OutputGenerator",
    "main",
]
