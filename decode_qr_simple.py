#!/usr/bin/env python3
"""
Decode QR code using qrcode library and PIL.
"""

import sys
from pathlib import Path
try:
    from PIL import Image
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pillow qrcode[pil]")
    sys.exit(1)

def decode_qr_with_qrcode(image_path):
    """Try to decode QR code using qrcode library."""
    try:
        # Open the image
        image = Image.open(image_path)
        print(f"Image size: {image.size}")
        print(f"Image mode: {image.mode}")
        print()
        
        # Convert to grayscale if needed
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image
        
        # Try to decode using qrcode
        qr = qrcode.QRCode()
        
        # The qrcode library doesn't have built-in decoding, so we'll use a different approach
        # Let's try to analyze the image structure
        
        return analyze_image_structure(gray)
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def analyze_image_structure(image):
    """Analyze the QR code image structure."""
    width, height = image.size
    pixels = list(image.getdata())
    
    print("=== IMAGE ANALYSIS ===")
    print(f"Dimensions: {width} x {height}")
    print(f"Total pixels: {len(pixels):,}")
    
    # Threshold for black/white
    threshold = 128
    black_pixels = sum(1 for p in pixels if p < threshold)
    white_pixels = len(pixels) - black_pixels
    
    print(f"Black pixels: {black_pixels:,} ({black_pixels/len(pixels)*100:.1f}%)")
    print(f"White pixels: {white_pixels:,} ({white_pixels/len(pixels)*100:.1f}%)")
    print()
    
    # Try to estimate QR module size
    # Look for patterns that suggest QR code structure
    if width == height:
        print("Image is square - likely a QR code")
        
        # Estimate module size by looking for pattern repetition
        # This is a simplified approach
        module_estimate = width // 25  # Rough guess for version 2-3 QR codes
        print(f"Estimated module size: ~{module_estimate} pixels")
        
        # Try to extract the QR data matrix
        modules_per_side = width // module_estimate
        print(f"Estimated modules per side: {modules_per_side}")
        
        if modules_per_side >= 21:  # Minimum for QR code
            qr_version = (modules_per_side - 21) // 4 + 1
            print(f"Estimated QR version: {qr_version}")
            
            # Try to create a binary matrix
            matrix = []
            for y in range(0, height, module_estimate):
                row = []
                for x in range(0, width, module_estimate):
                    if x < width and y < height:
                        pixel_value = pixels[y * width + x]
                        row.append(1 if pixel_value < threshold else 0)
                matrix.append(row)
            
            print(f"Extracted matrix: {len(matrix)} x {len(matrix[0]) if matrix else 0}")
            
            # Try to decode this matrix (simplified)
            try:
                # Create a QR code object and try to reconstruct
                qr = qrcode.QRCode(
                    version=qr_version,
                    error_correction=ERROR_CORRECT_L,
                    box_size=1,
                    border=0,
                )
                
                # This won't actually decode, but shows the structure
                print("QR code structure detected, but decoding requires specialized library")
                return True
                
            except Exception as e:
                print(f"Matrix analysis failed: {e}")
    
    return False

def try_alternative_decoders(image_path):
    """Try alternative approaches to decode the QR code."""
    print("\n=== ALTERNATIVE APPROACHES ===")
    print("1. Try using online QR decoder:")
    print("   - Upload the image to https://zxing.org/w/decode.jspx")
    print("   - Or use https://qr-code-scanner.com/")
    print()
    print("2. Try mobile QR scanner apps:")
    print("   - QR Code Reader by Scan")
    print("   - QR Scanner for iPhone")
    print("   - QR Code Reader for Android")
    print()
    print("3. Try command-line tools:")
    print("   - zbarimg: sudo apt install zbar-tools && zbarimg image.png")
    print("   - dmtxread: sudo apt install libdmtx-utils && dmtxread image.png")

def main():
    if len(sys.argv) != 2:
        print("Usage: python decode_qr_simple.py <qr_image_path>")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Image file not found: {image_path}")
        sys.exit(1)
    
    print(f"Analyzing QR code from: {image_path}")
    print()
    
    result = decode_qr_with_qrcode(image_path)
    
    if not result:
        try_alternative_decoders(image_path)

if __name__ == "__main__":
    main()
