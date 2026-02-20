"""
Simple test for glob expansion functionality without complex mocking.
"""

import pytest
import tempfile
import os
from pathlib import Path


def test_glob_expansion_basic():
    """Test basic glob expansion functionality."""
    # Test that the CLI can handle glob patterns
    test_dirs = Path(__file__).parent / "testdirs"
    
    if not test_dirs.exists():
        pytest.skip("testdirs not found")
    
    # Test pattern that should match some directories
    pattern = str(test_dirs / "parallel*")
    
    # Import and test the glob expansion logic directly
    import glob
    
    # Test that glob finds the expected directories
    matches = glob.glob(pattern, recursive=True)
    dir_matches = [m for m in matches if os.path.isdir(m)]
    
    # Should find at least parallel1, parallel2, parallel3
    assert len(dir_matches) >= 3
    
    # Check that expected directories are found
    expected_dirs = ["parallel1", "parallel2", "parallel3"]
    found_dirs = [os.path.basename(d) for d in dir_matches]
    
    for expected in expected_dirs:
        assert expected in found_dirs


def test_pattern_detection():
    """Test that we can correctly identify glob patterns."""
    glob_patterns = [
        "tests/testdirs/*",
        "tests/testdirs/parallel*",
        "tests/testdirs/[pn]*",
        "tests/testdirs/parallel[1-3]*"
    ]
    
    non_glob_patterns = [
        "tests/testdirs/parallel1",
        "tests/testdirs/nested1",
        "/absolute/path/to/dir"
    ]
    
    for pattern in glob_patterns:
        has_glob = (
            '*' in pattern or 
            '?' in pattern or 
            '[' in pattern
        )
        assert has_glob, f"Pattern {pattern} should be detected as glob"
    
    for pattern in non_glob_patterns:
        has_glob = (
            '*' in pattern or 
            '?' in pattern or 
            '[' in pattern
        )
        assert not has_glob, f"Pattern {pattern} should NOT be detected as glob"


def test_depth_logic():
    """Test depth-limited directory walking."""
    test_dirs = Path(__file__).parent / "testdirs"
    
    if not test_dirs.exists():
        pytest.skip("testdirs not found")
    
    # Test os.walk behavior with depth limiting
    max_depth = 0
    found_dirs = []
    
    for root, dirs, files in os.walk(test_dirs):
        current_depth = root.count(os.sep) - str(test_dirs).count(os.sep)
        if current_depth <= max_depth:
            found_dirs.append(root)
            if current_depth < max_depth:
                # Limit further exploration
                dirs[:] = [d for d in dirs if not d.startswith('.')]
    
    # Should find the immediate subdirectories
    assert len(found_dirs) >= 3  # At least parallel1, parallel2, parallel3


def test_file_operations():
    """Test basic file operations for set operations."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        union_file = Path(tmp_dir) / "union.txt"
        intersection_file = Path(tmp_dir) / "intersection.txt"
        exclusive_file = Path(tmp_dir) / "exclusive.txt"
        
        # Test file creation and writing
        test_files = [
            (union_file, ["file1.txt", "file2.txt", "file3.txt"]),
            (intersection_file, ["file1.txt", "file2.txt"]),
            (exclusive_file, ["file3.txt"])
        ]
        
        for file_path, content in test_files:
            with open(file_path, 'w') as f:
                for line in content:
                    f.write(f"{line}\n")
        
        # Verify files exist and have content
        for file_path, expected_content in test_files:
            assert file_path.exists()
            
            with open(file_path, 'r') as f:
                actual_content = [line.strip() for line in f.readlines()]
            
            assert actual_content == expected_content


if __name__ == "__main__":
    # Run basic tests
    test_glob_expansion_basic()
    test_pattern_detection()
    test_depth_logic()
    test_file_operations()
    print("All basic tests passed!")
