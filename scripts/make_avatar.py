#!/usr/bin/env python3
"""Process photo for GitHub profile: crop, circle-mask, optimize."""

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import sys
import os

def process_photo(input_path: str, output_path: str, size: int = 400):
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size

    # Crop tighter around face/shoulders (center crop, biased slightly upward)
    crop_size = min(w, h)
    left = (w - crop_size) // 2
    top = max(0, (h - crop_size) // 2 - int(crop_size * 0.05))  # bias upward
    right = left + crop_size
    bottom = top + crop_size
    bottom = min(bottom, h)
    top = bottom - crop_size
    top = max(0, top)
    img = img.crop((left, top, right, bottom))

    # Resize to target
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    # Slightly increase brightness and contrast, reduce harsh highlights
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.05)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)

    # Create circular mask
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    # Anti-alias the mask edge
    mask = mask.filter(ImageFilter.GaussianBlur(1.5))

    # Apply mask
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)

    # Save as PNG (transparency for circle)
    output.save(output_path, "PNG", optimize=True)
    print(f"-> Saved circular portrait: {output_path} ({size}x{size}px)")

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "assets/Photo.jpeg"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "assets/avatar.png"
    sz = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    process_photo(input_file, output_file, sz)
