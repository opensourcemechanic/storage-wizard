"""
Tests for core storage wizard functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from storage_wizard.core import StorageIndexer, MediaConsolidator, DuplicateDetector


class TestStorageIndexer:
    """Test cases for StorageIndexer class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def sample_files(self, temp_dir):
        """Create sample files for testing."""
        files = {
            'test.txt': 'Hello World',
            'photo.jpg': 'fake image data',
            'video.mp4': 'fake video data',
            'temp.tmp': 'temporary data',
            'document.pdf': 'fake pdf data'
        }
        
        created_files = []
        for filename, content in files.items():
            filepath = Path(temp_dir) / filename
            filepath.write_text(content)
            created_files.append(str(filepath))
        
        return created_files
    
    def test_indexer_initialization(self, temp_dir):
        """Test indexer initialization."""
        indexer = StorageIndexer(temp_dir)
        assert indexer.base_path == Path(temp_dir)
        assert indexer.read_only == True
    
    def test_scan_directory(self, temp_dir, sample_files):
        """Test directory scanning."""
        indexer = StorageIndexer(temp_dir, read_only=True)
        result = indexer.scan_directory()
        
        assert 'files' in result
        assert 'total_files' in result
        assert result['total_files'] == len(sample_files)
        
        # Check file info structure
        file_info = result['files'][0]
        assert 'path' in file_info
        assert 'size' in file_info
        assert 'file_type' in file_info
        assert 'is_temporary' in file_info
        assert 'is_system_file' in file_info
    
    def test_temporary_file_detection(self, temp_dir):
        """Test temporary file detection."""
        # Create temporary files
        temp_files = ['test.tmp', 'backup.bak', '~$temp.doc']
        for filename in temp_files:
            (Path(temp_dir) / filename).write_text('temp content')
        
        indexer = StorageIndexer(temp_dir, read_only=True)
        result = indexer.scan_directory()
        
        temp_count = sum(1 for f in result['files'] if f['is_temporary'])
        assert temp_count >= len(temp_files)
    
    def test_hash_computation(self, temp_dir, sample_files):
        """Test file hash computation."""
        indexer = StorageIndexer(temp_dir, read_only=True)
        indexer.scan_directory()
        
        hashes = indexer.compute_hashes()
        assert len(hashes) > 0
        
        # Check hash format
        for filepath, file_hash in hashes:
            assert len(file_hash) == 64  # SHA-256 hex length
            assert os.path.exists(filepath)
    
    def test_duplicate_detection(self, temp_dir):
        """Test duplicate file detection."""
        # Create duplicate files
        content = "duplicate content"
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        
        file1.write_text(content)
        file2.write_text(content)
        
        indexer = StorageIndexer(temp_dir, read_only=True)
        indexer.scan_directory()
        indexer.compute_hashes()
        
        duplicates = indexer.find_duplicates()
        assert len(duplicates) >= 1
        
        # Check duplicate group
        duplicate_group = duplicates[0]
        assert len(duplicate_group) == 2
        assert any("file1.txt" in path for path in duplicate_group)
        assert any("file2.txt" in path for path in duplicate_group)


class TestMediaConsolidator:
    """Test cases for MediaConsolidator class."""
    
    def test_media_type_detection(self):
        """Test media type detection."""
        consolidator = MediaConsolidator()
        
        assert consolidator._get_media_type('.mp4') == 'video'
        assert consolidator._get_media_type('.mp3') == 'audio'
        assert consolidator._get_media_type('.jpg') == 'photo'
        assert consolidator._get_media_type('.pdf') == 'document'
        assert consolidator._get_media_type('.xyz') is None


if __name__ == "__main__":
    pytest.main([__file__])
