# Storage Wizard

Read-only storage indexing and optimization tool with optional Python-Rust integration for performance-critical operations.

## Features

- **Read-Only by Default**: Safe analysis without modifying files
- **Fast Directory Scanning**: Optional Rust-accelerated file indexing with parallel processing
- **Media Consolidation**: Intelligent organization analysis for photos, videos, audio, and documents
- **Duplicate Detection**: Content-based duplicate finding with hash verification
- **Cleanup Optimization**: Identification of temporary and system files for safe removal
- **Directory Tree Analysis**: Advanced analysis for storage optimization
- **Multiple Output Formats**: JSON, CSV, and bash command generation
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Rich CLI Interface**: Beautiful terminal output with progress reporting

## Installation

### Prerequisites

- Python 3.8+
- uv (fast Python package installer)
- Rust 1.70+ (optional, for performance acceleration)

### Quick Setup with uv

```bash
# Clone and navigate to project
cd storage-wizard

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
uv pip install -e .

# Test installation
storage-wizard --help
```

### Optional Rust Performance

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Install maturin and build Rust components
uv pip install maturin
maturin develop
```

## Usage

### Basic Commands

#### Scan a Directory
```bash
storage-wizard scan /path/to/directory --output results.json --verbose
```

#### Find Duplicates
```bash
storage-wizard duplicates /path/to/directory --details
```

#### Generate Consolidation Commands
```bash
storage-wizard generate /source/path --target /mnt/storage --output consolidate.sh
```

#### Comprehensive Analysis
```bash
storage-wizard analyze /path/to/directory --output analysis.json --format json
```

### Advanced Usage

#### Include Hidden Files
```bash
storage-wizard scan /path/to/directory --hidden
```

#### Different Output Formats
```bash
storage-wizard scan /path/to/directory --output report.csv --format csv
storage-wizard scan /path/to/directory --output report.json --format json
```

#### Verbose Output
```bash
storage-wizard scan /path/to/directory --verbose
```

## Commands Overview

### `scan`
Read-only directory scanning and indexing.
- **Purpose**: Analyze directory structure and file types
- **Output**: File statistics, type distribution, permission issues
- **Safety**: Completely read-only, never modifies files

### `duplicates`
Find and report duplicate files.
- **Purpose**: Identify duplicate content across directories
- **Method**: Content-based SHA-256 hashing
- **Safety**: Read-only analysis only

### `generate`
Generate bash commands for media consolidation.
- **Purpose**: Create executable scripts for file organization
- **Output**: Bash script with safety warnings
- **Safety**: Generated script requires manual review

### `analyze`
Comprehensive storage analysis with recommendations.
- **Purpose**: Full storage health check and optimization suggestions
- **Output**: Detailed analysis with actionable recommendations
- **Safety**: Read-only analysis and reporting

## Architecture

### Python-Rust Integration

The project uses optional maturin integration for performance-critical components:

- **Rust Core**: Fast file hashing, parallel scanning, memory-efficient operations
- **Python Layer**: High-level logic, CLI interface, and database management
- **PyO3 Bindings**: Seamless integration between Rust and Python

### Performance Features

- **Parallel Processing**: Multi-threaded file operations using Rayon
- **Efficient Hashing**: BLAKE3 algorithm for fast content verification
- **Memory Management**: Streaming operations for large files
- **Permission Handling**: Smart detection with minimal logging

## Project Structure

```
storage-wizard/
├── src/
│   └── rust/              # Rust performance core
│       └── lib.rs
├── python/
│   └── storage_wizard/    # Python package
│       ├── __init__.py
│       ├── core.py
│       └── cli.py
├── tests/                 # Test suite
├── Cargo.toml             # Rust dependencies
├── pyproject.toml         # Python project config
├── build.rs               # Build configuration
└── README.md
```

## Safety Features

- **Read-Only Default**: No accidental file modifications
- **Permission Awareness**: Respects access restrictions
- **Generated Script Warnings**: All generated scripts include safety notices
- **Graceful Degradation**: Works without Rust components
- **Comprehensive Logging**: Clear feedback on operations

## Output Formats

### JSON Reports
```json
{
  "scan_result": {
    "files": [...],
    "total_files": 1000,
    "permission_denied_dirs": [...]
  },
  "duplicates": [...],
  "summary": {...}
}
```

### CSV Reports
```csv
path,size,modified,file_type,is_temporary,is_system_file
/path/to/file.txt,1024,1640995200,txt,False,False
```

### Bash Scripts
```bash
#!/bin/bash
# Storage Wizard - Generated Consolidation Commands
# *** REVIEW BEFORE EXECUTING *** This tool is read-only.

# Create target directories
mkdir -p '/mnt/storage/Video'
mkdir -p '/mnt/storage/Audio'

# Move media files
cp -n '/source/video.mp4' '/mnt/storage/Video/video.mp4'
```

## Troubleshooting

### Permission Issues
The tool logs permission-denied directories once per tree, not per file:
```
Permission denied: /private/dir (skipping tree)
```

### Rust Components Not Available
If Rust components aren't built, the tool falls back to Python implementations:
```
Rust core not available; using Python-only indexing
```

### Large Directories
For very large directories, consider:
- Increasing hash batch size
- Using Rust components for better performance
- Processing in chunks with output files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the test suite
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- Issues: GitHub Issues
- Documentation: README and inline help
- Examples: `storage-wizard --help`
