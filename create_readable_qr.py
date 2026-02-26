#!/usr/bin/env python3
"""
Create a new treemap scan and generate a readable QR code with minimal data.
"""

import subprocess
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_readable_qr.py <directory_path> [label]")
        print("Example: python create_readable_qr.py /media/h/Users/bri MyDrive")
        sys.exit(1)
    
    directory = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else Path(directory).name
    
    print(f"Scanning directory: {directory}")
    print(f"Label: {label}")
    print()
    
    # Step 1: Scan and save the treemap
    print("=== Step 1: Scanning and saving treemap ===")
    scan_cmd = [
        "storage-wizard", "treemap", "scan", 
        directory, 
        "--label", label,
        "--store", "~/.storage-wizard/treemaps"
    ]
    
    try:
        result = subprocess.run(scan_cmd, capture_output=True, text=True, check=True)
        print("✓ Scan completed successfully")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"✗ Scan failed: {e}")
        print(e.stderr)
        return
    
    print()
    
    # Step 2: Generate QR code with minimal data
    print("=== Step 2: Generating readable QR code ===")
    
    # Generate a small QR code (0.75" for better readability)
    qr_cmd = [
        "storage-wizard", "treemap", "label",
        label,
        "--qr-image", f"{label}_readable_qr.png",
        "--qr-size", "0.75",  # Smaller size = denser QR
        "--qr-dpi", "300"
    ]
    
    try:
        result = subprocess.run(qr_cmd, capture_output=True, text=True, check=True)
        print("✓ QR code generated successfully")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"✗ QR generation failed: {e}")
        print(e.stderr)
        return
    
    print()
    
    # Step 3: Extract hash statistics
    print("=== Step 3: Extracting hash statistics ===")
    extract_cmd = ["python", "extract_hashes.py", label]
    
    try:
        result = subprocess.run(extract_cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"✗ Hash extraction failed: {e}")
        print(e.stderr)
    
    print()
    print("=== Summary ===")
    print(f"✓ Treemap saved as: {label}")
    print(f"✓ QR code saved as: {label}_readable_qr.png")
    print(f"✓ Full hash data available in: ~/.storage-wizard/treemaps/{label}.json")

if __name__ == "__main__":
    main()
