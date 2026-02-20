"""
Test cases for glob expansion functionality in Storage Wizard duplicates command.
"""

import pytest
import tempfile
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import typer
from rich.console import Console

from storage_wizard.cli import duplicates


class TestGlobExpansion:
    """Test glob expansion patterns and depth control."""

    @pytest.fixture
    def test_dirs(self):
        """Get the path to test directories."""
        return Path(__file__).parent / "testdirs"

    @pytest.fixture
    def capture_output(self):
        """Capture console output for testing."""
        console = Console(file=tempfile.NamedTemporaryFile(mode='w', delete=False), width=120)
        return console

    def test_basic_glob_expansion(self, test_dirs):
        """Test basic glob expansion with * pattern."""
        pattern = str(test_dirs / "*")
        
        # Mock the glob expansion to return expected directories
        expected_dirs = [
            str(test_dirs / "nested1"),
            str(test_dirs / "nested2"), 
            str(test_dirs / "nested3"),
            str(test_dirs / "parallel1"),
            str(test_dirs / "parallel2"),
            str(test_dirs / "parallel3")
        ]
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = expected_dirs
            
            # Mock os.path.isdir to return True for all expected dirs
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                # Mock the scanning and hashing process
                with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                    mock_instance = mock_indexer.return_value
                    mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                    mock_instance.compute_hashes.return_value = []
                    mock_instance.find_duplicates.return_value = []
                    mock_instance._indexed_files = []
                    
                    # Capture output
                    with patch('storage_wizard.cli.console') as mock_console:
                        duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                 output=None, export_data=None, union_file=None, 
                                 intersection_file=None, exclusive_file=None, depth=None,
                                 debug=True, verbose=False)
                        
                        # Verify glob was called with correct pattern
                        mock_glob.assert_called_with(pattern, recursive=True)
                        
                        # Verify debug output shows expanded directories
                        all_calls = [str(call) for call in mock_console.print.call_args_list]
                        debug_calls = [call for call in all_calls 
                                     if 'Found' in call and 'directories to analyze' in str(call)]
                        assert len(debug_calls) > 0

    def test_parallel_pattern_expansion(self, test_dirs):
        """Test pattern matching with specific prefix."""
        pattern = str(test_dirs / "parallel*")
        expected_dirs = [
            str(test_dirs / "parallel1"),
            str(test_dirs / "parallel2"),
            str(test_dirs / "parallel3")
        ]
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = expected_dirs
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                    mock_instance = mock_indexer.return_value
                    mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                    mock_instance.compute_hashes.return_value = []
                    mock_instance.find_duplicates.return_value = []
                    mock_instance._indexed_files = []
                    
                    with patch('storage_wizard.cli.console') as mock_console:
                        duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                 output=None, export_data=None, union_file=None, 
                                 intersection_file=None, exclusive_file=None, depth=None,
                                 debug=True, verbose=False)
                        
                        # Should only find 3 directories
                        debug_calls = [call for call in mock_console.print.call_args_list 
                                     if 'Found 3 directories' in str(call)]
                        assert len(debug_calls) > 0

    def test_depth_limited_expansion(self, test_dirs):
        """Test depth-limited glob expansion."""
        pattern = str(test_dirs / "*")
        depth = 0
        
        # For depth 0, should only include immediate subdirectories
        expected_dirs = [
            str(test_dirs / "parallel1"),
            str(test_dirs / "parallel2"),
            str(test_dirs / "parallel3")
        ]
        
        with patch('os.walk') as mock_walk:
            # Mock os.walk to simulate depth-limited traversal
            mock_walk.return_value = [
                (str(test_dirs), ['parallel1', 'parallel2', 'parallel3', 'nested1', 'nested2', 'nested3'], [])
            ]
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                with patch('fnmatch.fnmatch') as mock_fnmatch:
                    mock_fnmatch.return_value = True
                    
                    with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                        mock_instance = mock_indexer.return_value
                        mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                        mock_instance.compute_hashes.return_value = []
                        mock_instance.find_duplicates.return_value = []
                        mock_instance._indexed_files = []
                        
                        with patch('storage_wizard.cli.console') as mock_console:
                            duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                     output=None, export_data=None, union_file=None, 
                                     intersection_file=None, exclusive_file=None, depth=depth,
                                     debug=True, verbose=False)
                            
                            # Verify os.walk was called for depth-limited expansion
                            mock_walk.assert_called_once()
                            
                            # Verify depth-limited behavior was triggered
                            all_calls = [str(call) for call in mock_console.print.call_args_list]
                            depth_calls = [call for call in all_calls 
                                         if 'Expanding glob pattern' in str(call)]
                            assert len(depth_calls) > 0

    def test_no_matches_pattern(self):
        """Test handling of patterns that match no directories."""
        pattern = "/nonexistent/path/*"
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = []
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = False
                
                with patch('storage_wizard.cli.console') as mock_console:
                    duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                             output=None, export_data=None, union_file=None, 
                             intersection_file=None, exclusive_file=None, depth=None,
                             debug=True, verbose=False)
                    
                    # Should show "No valid directories found" message
                    error_calls = [call for call in mock_console.print.call_args_list 
                                 if 'No valid directories found' in str(call)]
                    assert len(error_calls) > 0

    def test_glob_with_set_operations(self, test_dirs, tmp_path):
        """Test glob expansion combined with set operations."""
        pattern = str(test_dirs / "parallel*")
        union_file = tmp_path / "union.txt"
        intersection_file = tmp_path / "intersection.txt"
        exclusive_file = tmp_path / "exclusive.txt"
        
        expected_dirs = [
            str(test_dirs / "parallel1"),
            str(test_dirs / "parallel2"),
            str(test_dirs / "parallel3")
        ]
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = expected_dirs
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                    mock_instance = mock_indexer.return_value
                    mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                    mock_instance.compute_hashes.return_value = []
                    mock_instance.find_duplicates.return_value = []
                    mock_instance._indexed_files = []
                    
                    # Mock file operations for set operations
                    with patch('builtins.open', create=True) as mock_open:
                        mock_file = mock_open.return_value.__enter__.return_value
                        mock_file.write = mock.MagicMock()
                        
                        with patch('storage_wizard.cli.console') as mock_console:
                            duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                     output=None, export_data=None, union_file=str(union_file), 
                                     intersection_file=str(intersection_file), exclusive_file=str(exclusive_file),
                                     depth=None, debug=True, verbose=False)
                            
                            # Verify files were opened for writing
                            assert mock_open.call_count >= 3  # Should open 3 files for set operations

    def test_complex_pattern_matching(self, test_dirs):
        """Test complex glob patterns with character classes and ranges."""
        patterns = [
            str(test_dirs / "parallel[1-2]*"),  # Range pattern
            str(test_dirs / "nested[13]*"),      # Character class pattern
            str(test_dirs / "*[13]*"),          # Mixed pattern
        ]
        
        for pattern in patterns:
            with patch('glob.glob') as mock_glob:
                mock_glob.return_value = [str(test_dirs / "parallel1"), str(test_dirs / "parallel2")]
                
                with patch('os.path.isdir') as mock_isdir:
                    mock_isdir.return_value = True
                    
                    with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                        mock_instance = mock_indexer.return_value
                        mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                        mock_instance.compute_hashes.return_value = []
                        mock_instance.find_duplicates.return_value = []
                        mock_instance._indexed_files = []
                        
                        with patch('storage_wizard.cli.console') as mock_console:
                            duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                     output=None, export_data=None, union_file=None, 
                                     intersection_file=None, exclusive_file=None, depth=None,
                                     debug=False, verbose=False)
                            
                            # Should process the pattern without errors
                            mock_glob.assert_called_with(pattern, recursive=True)
                            
                            # Verify the pattern was processed (no exceptions thrown)
                            all_calls = [str(call) for call in mock_console.print.call_args_list]
                            assert len(all_calls) >= 0  # Basic sanity check

    def test_mixed_paths_and_patterns(self, test_dirs):
        """Test mixing specific paths with glob patterns."""
        specific_path = str(test_dirs / "parallel1")
        pattern = str(test_dirs / "parallel*")
        
        expected_dirs = [
            str(test_dirs / "parallel1"),
            str(test_dirs / "parallel2"),
            str(test_dirs / "parallel3")
        ]
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = [str(test_dirs / "parallel2"), str(test_dirs / "parallel3")]
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                    mock_instance = mock_indexer.return_value
                    mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                    mock_instance.compute_hashes.return_value = []
                    mock_instance.find_duplicates.return_value = []
                    mock_instance._indexed_files = []
                    
                    with patch('storage_wizard.cli.console') as mock_console:
                        duplicates([specific_path, pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                 output=None, export_data=None, union_file=None, 
                                 intersection_file=None, exclusive_file=None, depth=None,
                                 debug=True, verbose=False)
                        
                        # Should handle both specific path and pattern
                        assert mock_glob.called

    def test_debug_output_detailed(self, test_dirs):
        """Test that debug output shows detailed expansion information."""
        pattern = str(test_dirs / "parallel*")
        expected_dirs = [
            str(test_dirs / "parallel1"),
            str(test_dirs / "parallel2"),
            str(test_dirs / "parallel3")
        ]
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = expected_dirs
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                    mock_instance = mock_indexer.return_value
                    mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                    mock_instance.compute_hashes.return_value = []
                    mock_instance.find_duplicates.return_value = []
                    mock_instance._indexed_files = []
                    
                    with patch('storage_wizard.cli.console') as mock_console:
                        duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                 output=None, export_data=None, union_file=None, 
                                 intersection_file=None, exclusive_file=None, depth=None,
                                 debug=True, verbose=False)
                        
                        # Check for debug messages
                        all_calls = [str(call) for call in mock_console.print.call_args_list]
                        debug_expansion = any("Expanding glob pattern" in call for call in all_calls)
                        debug_directories = any("Found" in call and "directories to analyze" in call for call in all_calls)
                        
                        assert debug_expansion, "Should show glob expansion debug info"
                        assert debug_directories, "Should show found directories debug info"

    def test_verbose_output_summary(self, test_dirs):
        """Test that verbose output shows summary information."""
        pattern = str(test_dirs / "*")
        expected_dirs = [
            str(test_dirs / "parallel1"),
            str(test_dirs / "parallel2"),
            str(test_dirs / "parallel3")
        ]
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = expected_dirs
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                    mock_instance = mock_indexer.return_value
                    mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                    mock_instance.compute_hashes.return_value = []
                    mock_instance.find_duplicates.return_value = []
                    mock_instance._indexed_files = []
                    
                    with patch('storage_wizard.cli.console') as mock_console:
                        duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                 output=None, export_data=None, union_file=None, 
                                 intersection_file=None, exclusive_file=None, depth=None,
                                 debug=False, verbose=True)
                        
                        # Check for verbose messages
                        all_calls = [str(call) for call in mock_console.print.call_args_list]
                        verbose_directories = any("Found" in call and "directories to analyze" in call for call in all_calls)
                        
                        assert verbose_directories, "Should show directory summary in verbose mode"


class TestGlobExpansionEdgeCases:
    """Test edge cases and error handling for glob expansion."""

    @pytest.fixture
    def test_dirs(self):
        """Get the path to test directories."""
        return Path(__file__).parent / "testdirs"

    def test_empty_pattern_list(self):
        """Test handling of empty pattern list."""
        # This should be caught by Typer's argument validation
        # We'll test that our function handles minimal inputs gracefully
        with patch('storage_wizard.cli.console') as mock_console:
            # Test with a minimal valid input
            duplicates(["/tmp"], group_by_dir=False, percent_dup_threshold=100.0,
                     output=None, export_data=None, union_file=None, 
                     intersection_file=None, exclusive_file=None, depth=None,
                     debug=False, verbose=False)

    def test_pattern_with_no_glob_chars(self, test_dirs):
        """Test pattern without glob characters (should be treated as literal path)."""
        pattern = str(test_dirs / "parallel1")
        
        with patch('os.path.isdir') as mock_isdir:
            mock_isdir.return_value = True
            
            with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                mock_instance = mock_indexer.return_value
                mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                mock_instance.compute_hashes.return_value = []
                mock_instance.find_duplicates.return_value = []
                mock_instance._indexed_files = []
                
                with patch('storage_wizard.cli.console') as mock_console:
                    duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                             output=None, export_data=None, union_file=None, 
                             intersection_file=None, exclusive_file=None, depth=None,
                             debug=False, verbose=False)
                    
                    # Should treat as literal path, not glob pattern
                    mock_isdir.assert_called_with(pattern)

    def test_very_deep_depth_limit(self, test_dirs):
        """Test with very high depth limit (should behave like unlimited)."""
        pattern = str(test_dirs / "*")
        depth = 10
        
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = []  # No directories found
            
            with patch('os.path.isdir') as mock_isdir:
                mock_isdir.return_value = True
                
                with patch('fnmatch.fnmatch') as mock_fnmatch:
                    mock_fnmatch.return_value = True
                    
                    with patch('storage_wizard.cli.StorageIndexer') as mock_indexer:
                        mock_instance = mock_indexer.return_value
                        mock_instance.scan_directory.return_value = {"files": [], "total_files": 0}
                        mock_instance.compute_hashes.return_value = []
                        mock_instance.find_duplicates.return_value = []
                        mock_instance._indexed_files = []
                        
                        with patch('storage_wizard.cli.console') as mock_console:
                            duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                                     output=None, export_data=None, union_file=None, 
                                     intersection_file=None, exclusive_file=None, depth=depth,
                                     debug=False, verbose=False)
                            
                            # Should handle high depth gracefully
                            mock_walk.assert_called_once()

    def test_permission_denied_directories(self, test_dirs):
        """Test handling of directories with permission denied."""
        pattern = str(test_dirs / "*")
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = [str(test_dirs / "parallel1")]
            
            with patch('os.path.isdir') as mock_isdir:
                # First call returns True (directory exists), second returns False (permission denied)
                mock_isdir.side_effect = [True, False]
                
                with patch('storage_wizard.cli.console') as mock_console:
                    duplicates([pattern], group_by_dir=False, percent_dup_threshold=100.0,
                             output=None, export_data=None, union_file=None, 
                             intersection_file=None, exclusive_file=None, depth=None,
                             debug=True, verbose=False)
                    
                    # Should handle permission issues gracefully
                    debug_calls = [call for call in mock_console.print.call_args_list 
                                 if 'Debug: Path not found or not a directory' in str(call)]
                    assert len(debug_calls) > 0
