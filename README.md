# Storage Wizard

Read-only storage indexing and optimization tool with optional Python-Rust integration for performance-critical operations.

## Author

**Brian Nitz** - Developed using [Windsurf](https://code.windsurf.ai/) with SWE-1.5 and Claude code models for AI-assisted development.

### Development Approach

This project was created using modern AI-assisted development practices:

- **IDE**: [Windsurf](https://code.windsurf.ai/) - AI-powered development environment
- **AI Assistant**: SWE-1.5 (Software Engineering) specialized code model
- **Code Models**: Claude 3.5 Sonnet and Claude 3 Opus for code generation and analysis
- **Methodology**: Iterative AI-human collaboration with checkpoint-based development
- **Version Control**: Git with comprehensive documentation and feature checkpoints

### AI-Assisted Development Features

- **Intelligent Code Generation**: AI-powered implementation of complex algorithms
- **Rapid Prototyping**: Fast iteration on features and optimizations
- **Performance Optimization**: AI-suggested improvements for speed and memory efficiency
- **Documentation**: AI-generated comprehensive documentation and examples
- **Testing**: AI-assisted test case generation and validation

## ⚠️ Disclaimer

**THIS SOFTWARE IS EXPERIMENTAL AND PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.**

The user assumes **ALL RISKS** associated with the use of this software, including but not limited to:

- **Data Loss**: While designed to be read-only, bugs or misuse could potentially cause data corruption or loss
- **System Performance**: Scanning large directories or computing file hashes may consume significant system resources
- **Generated Scripts**: Any generated bash scripts or commands must be manually reviewed before execution
- **Third-Party Dependencies**: This tool relies on external libraries that may have their own limitations and bugs

**BY USING THIS SOFTWARE, YOU ACKNOWLEDGE AND AGREE THAT:**
1. You are solely responsible for backing up your data before use
2. The authors and contributors are not liable for any damages or losses
3. You will review all generated commands before execution
4. You use this software at your own risk

**RECOMMENDATIONS:**
- Always backup important data before running any storage analysis
- Test on non-critical directories first
- Review generated scripts thoroughly before execution
- Monitor system resources during large scans

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

## Development

### AI-Assisted Development Process

This project showcases modern AI-assisted software development practices:

#### Development Environment
- **Primary IDE**: [Windsurf](https://code.windsurf.ai/) with SWE-1.5
- **AI Models**: Claude 3.5 Sonnet (primary), Claude 3 Opus (analysis)
- **Methodology**: Iterative AI-human collaboration
- **Version Control**: Git with comprehensive checkpoint documentation

#### Development Checkpoints
The project uses checkpoint-based development with comprehensive documentation:

- **v0.3.7**: Multi-path fast treemap with cross-device duplicate analysis
- **v0.3.6**: Fast treemap with duplicate detection (20x speedup)
- **v0.3.5**: Ultra-fast metadata scanner (125x speedup)
- **v0.3.4**: Cache versioning and safety improvements
- **v0.3**: Advanced set operations and WSL integration

#### AI-Generated Features
- **Performance Optimizations**: AI-suggested algorithm improvements
- **Code Architecture**: AI-designed modular structure
- **Documentation**: AI-generated comprehensive guides
- **Testing**: AI-assisted test case creation and validation

### Code Quality

- **Type Hints**: Full type annotation coverage
- **Documentation**: Comprehensive docstrings and guides
- **Error Handling**: Robust error management and user feedback
- **Performance**: Optimized for large-scale storage analysis
- **Testing**: AI-assisted test coverage and validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the test suite
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Brian Nitz

## Support

- Issues: GitHub Issues
- Documentation: README and inline help
- Examples: `storage-wizard --help`
