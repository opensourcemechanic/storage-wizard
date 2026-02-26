#!/usr/bin/env python3
"""
Generate simple, readable QR codes from cached treemap data.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

STORE_DIR = Path.home() / ".storage-wizard" / "treemaps"

def create_minimal_qr_payload(label):
    """Create a minimal QR payload with just essential info."""
    treemap_file = STORE_DIR / f"{label}.json"
    
    if not treemap_file.exists():
        print(f"No treemap found for label: {label}")
        return None
    
    # Load the treemap data
    data = json.loads(treemap_file.read_text(encoding="utf-8"))
    
    # Create minimal payload
    tree = data['tree']
    
    # Only include top 5 largest directories
    children = []
    for child in sorted(tree.get('children', []), key=lambda c: c.get('size', 0), reverse=True)[:5]:
        size_str = format_size(child.get('size', 0))
        children.append({
            "name": child['name'],
            "size": size_str,
            "files": child.get('file_count', 0)
        })
    
    payload = {
        "label": data['label'],
        "scanned": data['scanned_at'][:10],  # Just the date
        "path": data['root_path'].split('/')[-1],  # Just the folder name
        "total": format_size(tree.get('size', 0)),
        "files": tree.get('file_count', 0),
        "top": children
    }
    
    return json.dumps(payload, separators=(",", ":"))

def format_size(bytes_val):
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}PB"

def generate_simple_qr(label, output_file=None):
    """Generate a simple QR code from cached treemap."""
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    
    payload = create_minimal_qr_payload(label)
    if not payload:
        return False
    
    print(f"Payload length: {len(payload)} characters")
    print(f"Payload: {payload}")
    print()
    
    # Create QR code with larger modules for better readability
    qr = qrcode.QRCode(
        version=5,  # Smaller version = fewer modules
        error_correction=ERROR_CORRECT_M,  # Medium error correction
        box_size=8,  # Larger modules
        border=2,
    )
    
    qr.add_data(payload)
    qr.make(fit=True)
    
    # Generate image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Set DPI for printing
    if hasattr(img, 'info'):
        img.info['dpi'] = (300, 300)
    
    # Save file
    if not output_file:
        output_file = f"{label}_simple_qr.png"
    
    img.save(output_file)
    
    # Get image dimensions
    width, height = img.size
    print(f"QR code saved: {output_file}")
    print(f"Size: {width} x {height} pixels")
    print(f"Physical size: {width/300:.2f}\" x {height/300:.2f}\" at 300 DPI")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_qr_generator.py <label> [output_file]")
        print("Available labels:")
        
        # List available treemaps
        if STORE_DIR.exists():
            for file in sorted(STORE_DIR.glob("*.json")):
                label = file.stem
                print(f"  - {label}")
        return
    
    label = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Generating simple QR code for: {label}")
    print()
    
    success = generate_simple_qr(label, output_file)
    
    if success:
        print("\n✓ QR code generated successfully!")
        print("This QR code should be much more readable by phones.")
    else:
        print("\n✗ Failed to generate QR code")

if __name__ == "__main__":
    main()
