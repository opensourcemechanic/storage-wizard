#!/usr/bin/env python3
"""
Decode QR code from image file and extract the JSON payload.
"""

import sys
from pathlib import Path
try:
    from PIL import Image
    import qrcode
    from pyzbar import pyzbar
    import json
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pillow qrcode[pil] pyzbar")
    sys.exit(1)

def decode_qr_image(image_path):
    """Decode QR code from image file."""
    try:
        # Open the image
        image = Image.open(image_path)
        print(f"Image size: {image.size}")
        print(f"Image mode: {image.mode}")
        print()
        
        # Decode QR codes
        qr_codes = pyzbar.decode(image)
        
        if not qr_codes:
            print("No QR codes found in image.")
            return None
        
        for i, qr_code in enumerate(qr_codes):
            print(f"QR Code {i+1}:")
            print(f"  Type: {qr_code.type}")
            print(f"  Quality: {qr_code.quality}")
            print(f"  Rectangle: {qr_code.rect}")
            print(f"  Polygon: {qr_code.polygon}")
            print()
            
            # Get the data
            qr_data = qr_code.data.decode('utf-8')
            print(f"Raw data length: {len(qr_data)} characters")
            print()
            
            # Try to parse as JSON
            try:
                payload = json.loads(qr_data)
                print("=== DECODED JSON PAYLOAD ===")
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return payload
            except json.JSONDecodeError as e:
                print(f"Failed to parse as JSON: {e}")
                print("=== RAW DATA ===")
                print(qr_data)
                return qr_data
        
    except Exception as e:
        print(f"Error decoding QR code: {e}")
        return None

def analyze_qr_structure(image_path):
    """Analyze the QR code structure and density."""
    try:
        image = Image.open(image_path)
        
        # Convert to grayscale for analysis
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image
        
        # Get basic stats
        width, height = gray.size
        pixels = list(gray.getdata())
        
        # Count black vs white pixels (QR codes are binary)
        threshold = 128
        black_pixels = sum(1 for p in pixels if p < threshold)
        white_pixels = len(pixels) - black_pixels
        
        print("=== QR CODE ANALYSIS ===")
        print(f"Image dimensions: {width} x {height}")
        print(f"Total pixels: {len(pixels):,}")
        print(f"Black pixels: {black_pixels:,} ({black_pixels/len(pixels)*100:.1f}%)")
        print(f"White pixels: {white_pixels:,} ({white_pixels/len(pixels)*100:.1f}%)")
        print()
        
        # Estimate QR version (size)
        if width == height:
            # QR codes are square, estimate version based on size
            # Version 1: 21x21 modules, each version adds 4 modules
            estimated_modules = width // 10  # Rough estimate: 10 pixels per module
            if estimated_modules >= 21:
                version = (estimated_modules - 21) // 4 + 1
                max_data_bytes = {
                    1: 17, 2: 32, 5: 106, 10: 174, 20: 274, 25: 378, 40: 4296
                }.get(version, "Unknown")
                print(f"Estimated QR version: {version}")
                print(f"Max data capacity: ~{max_data_bytes} bytes")
        
        return True
        
    except Exception as e:
        print(f"Error analyzing QR code: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python decode_qr.py <qr_image_path>")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Image file not found: {image_path}")
        sys.exit(1)
    
    print(f"Decoding QR code from: {image_path}")
    print()
    
    # Analyze the QR code structure
    analyze_qr_structure(image_path)
    print()
    
    # Decode the QR code
    result = decode_qr_image(image_path)
    
    if result is None:
        print("\n=== TROUBLESHOOTING ===")
        print("If the QR code cannot be read, try:")
        print("1. Increasing image resolution")
        print("2. Improving contrast")
        print("3. Reducing data payload size")
        print("4. Using a larger QR code size")
        print("5. Checking for image distortion")

if __name__ == "__main__":
    main()
