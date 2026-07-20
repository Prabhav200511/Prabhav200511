#!/usr/bin/env python3
"""
make_ascii_svg.py - Animated ASCII Self-Portrait Generator for GitHub Profiles

Converts a high-resolution photo (or generates a default AI/SWE avatar) into an
animated SVG featuring:
  - macOS Terminal window styling
  - Terminal boot sequence (`> Initializing profile...`)
  - Animated typing of name & introduction
  - Sequential reveal / "typing" of the ASCII portrait with subtle monochrome tones
  - Infinite blinking cursor (`█`)
  - Footer tagline & tech stack icons/text

Usage:
    python make_ascii_svg.py [photo.jpg] [ascii.svg] [options]

Examples:
    python make_ascii_svg.py assets/photo.jpg assets/ascii.svg
    python make_ascii_svg.py --demo assets/ascii.svg
    python make_ascii_svg.py photo.jpg ascii.svg --cols 100 --remove-bg
"""

import os
import sys
import argparse
import math

try:
    from PIL import Image, ImageEnhance, ImageOps, ImageFilter
except ImportError:
    print("Error: Pillow (PIL) is required. Install via: pip install pillow", file=sys.stderr)
    sys.exit(1)

# Optional dependencies for advanced background removal & OpenCV
try:
    import numpy as np
except ImportError:
    np = None

try:
    from rembg import remove as rembg_remove
except ImportError:
    rembg_remove = None

try:
    import cv2
except ImportError:
    cv2 = None


# Extended and compact ASCII character sets (ordered from dark/dense to light/empty)
ASCII_CHARSETS = {
    "standard": "@%#*+=-:. ",
    "detailed": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "blocks": "█▓▒░ ",
    "matrix": "01#*+=:. ",
}

# Monochrome gray palette matching GitHub Dark Mode (#0d1117 / #161b22)
PALETTE_GRAYS = [
    "#f8fafc",  # 0: Brightest white/gray
    "#e2e8f0",  # 1: Very light gray
    "#cbd5e1",  # 2: Light slate
    "#94a3b8",  # 3: Medium slate
    "#64748b",  # 4: Darker slate
    "#475569",  # 5: Dark gray
    "#334155",  # 6: Deep slate
]


def remove_background_if_requested(img: Image.Image, use_rembg: bool = False) -> Image.Image:
    """Removes image background using rembg if available/requested, or returns cleaned image."""
    if use_rembg and rembg_remove is not None:
        print("-> Applying AI background removal (rembg)...")
        res = rembg_remove(img)
        if isinstance(res, Image.Image):
            bbox = res.getbbox()
            if bbox:
                res = res.crop(bbox)
            return res
    return img


def preprocess_image(img: Image.Image, cols: int = 82, char_aspect: float = 0.55, enhance_contrast: float = 1.3, max_rows: int = 42) -> Image.Image:
    """Resizes and enhances the image for optimal ASCII representation."""
    # If image has transparency, composite onto black background first
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        bg.alpha_composite(rgba)
        img = bg.convert("L")
    else:
        img = img.convert("L")
    
    # Auto-contrast and enhancement
    img = ImageOps.autocontrast(img, cutoff=1)
    if enhance_contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(enhance_contrast)
        
    # Sharpen slightly to make edges stand out in ASCII
    img = img.filter(ImageFilter.SHARPEN)
    
    # Calculate dimensions taking into account font aspect ratio (characters are taller than wide)
    orig_width, orig_height = img.size
    rows = int((orig_height / orig_width) * cols * char_aspect)
    
    # Cap rows at max_rows to prevent tall photos from making the SVG excessively tall
    if rows > max_rows:
        cols = max(30, int(max_rows / ((orig_height / orig_width) * char_aspect)))
        rows = max_rows
        
    rows = max(15, min(rows, max_rows))
    
    img = img.resize((cols, rows), Image.Resampling.LANCZOS)
    return img


def generate_demo_avatar(cols: int = 86, rows: int = 42) -> list[str]:
    """Generates a high-tech silhouette / code-matrix avatar when no photo is provided."""
    grid = []
    center_x = cols / 2.0
    center_y = rows / 2.2
    
    chars = ASCII_CHARSETS["detailed"]
    for y in range(rows):
        line_chars = []
        for x in range(cols):
            # Normalised distances
            dx = (x - center_x) / (cols * 0.35)
            dy = (y - center_y) / (rows * 0.45)
            
            # Head circle
            head_dist = math.sqrt(dx**2 + (dy + 0.2)**2)
            # Shoulders / torso ellipse
            torso_dist = math.sqrt((dx * 0.7)**2 + max(0, dy - 0.35)**2)
            
            # Combine shapes
            val = min(head_dist / 0.65, torso_dist / 0.85)
            
            # Add subtle geometric patterns/matrix texture
            pattern = math.sin(x * 0.4) * math.cos(y * 0.6) * 0.15
            val = val + pattern
            
            if val < 0.6:
                # Dense core
                char_idx = int((val / 0.6) * (len(chars) * 0.5))
            elif val < 1.0:
                # Outer glow / edges
                char_idx = int(len(chars) * 0.5 + ((val - 0.6) / 0.4) * (len(chars) * 0.5 - 1))
            else:
                char_idx = len(chars) - 1
                
            char_idx = max(0, min(len(chars) - 1, char_idx))
            line_chars.append(chars[char_idx])
        grid.append("".join(line_chars))
    return grid


def image_to_ascii_grid(img: Image.Image, charset_name: str = "detailed", invert: bool = False) -> list[tuple[str, int]]:
    """Converts a PIL grayscale image into a list of lines with color/intensity index."""
    chars = ASCII_CHARSETS.get(charset_name, ASCII_CHARSETS["detailed"])
    if invert:
        chars = chars[::-1]
        
    width, height = img.size
    pixels = img.load()
    
    ascii_grid = []
    for y in range(height):
        line_str = []
        for x in range(width):
            pixel_val = pixels[x, y]
            # Map pixel 0-255 to character set
            char_idx = int((pixel_val / 255.0) * (len(chars) - 1))
            char = chars[char_idx]
            # Escape XML/SVG special characters
            if char == "&": char = "&amp;"
            elif char == "<": char = "&lt;"
            elif char == ">": char = "&gt;"
            elif char == '"': char = "&quot;"
            elif char == " ": char = "&#160;"  # Non-breaking space for alignment
            line_str.append(char)
        ascii_grid.append("".join(line_str))
    return ascii_grid


def escape_xml(text: str) -> str:
    """Escapes strings for XML/SVG output."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def generate_animated_svg(
    ascii_lines: list[str],
    output_path: str,
    name: str = "KRISHNA PRABHAV",
    title: str = "SWE & AI Systems Engineer",
    tagline: str = "Building scalable software one commit at a time • Distributed Systems • AI",
    stack: str = "Go • Python • TypeScript • Redis • PostgreSQL • PyTorch",
    font_size: int = 11,
    line_height: int = 13,
    padding: int = 30
):
    """Generates the full self-contained animated SVG with terminal boot sequence and typing effects."""
    num_rows = len(ascii_lines)
    max_line_len = max(len(line.replace("&#160;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')) for line in ascii_lines)
    
    # Calculate SVG dimensions
    # Monospace character width is typically ~0.6 * font_size
    char_width = font_size * 0.602
    content_width = max(820, int(max_line_len * char_width) + padding * 2 + 40)
    
    header_height = 170  # Window bar + Boot sequence + Name/Title
    portrait_height = num_rows * line_height
    footer_height = 90   # Tagline + Stack + padding
    total_height = header_height + portrait_height + footer_height
    
    # Animation timings
    t_boot1 = 0.2
    t_boot2 = 0.8
    t_boot3 = 1.4
    t_boot4 = 2.0
    t_name = 2.6
    t_portrait_start = 3.2
    t_portrait_duration = 2.4
    t_row_step = t_portrait_duration / max(1, num_rows)
    t_footer = t_portrait_start + t_portrait_duration + 0.4
    
    svg_parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {content_width} {total_height}" width="100%" height="100%" style="background: #0d1117; font-family: \'JetBrains Mono\', \'Fira Code\', Consolas, \'Courier New\', monospace;">',
        f'  <defs>',
        f'    <style>',
        f'      @import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&amp;display=swap");',
        f'      .bg-rect {{ fill: #0d1117; stroke: #30363d; stroke-width: 1.5px; rx: 12px; }}',
        f'      .header-bar {{ fill: #161b22; }}',
        f'      .title-text {{ font-size: 13px; fill: #8b949e; font-weight: 600; text-anchor: middle; }}',
        f'      .boot-text {{ font-size: 13px; fill: #58a6ff; font-weight: 600; opacity: 0; }}',
        f'      .boot-success {{ fill: #3fb950; }}',
        f'      .name-text {{ font-size: 22px; fill: #f0f6fc; font-weight: 700; letter-spacing: 2px; opacity: 0; }}',
        f'      .role-text {{ font-size: 14px; fill: #a5d6ff; font-weight: 600; opacity: 0; }}',
        f'      .ascii-row {{ font-size: {font_size}px; font-weight: 600; letter-spacing: 0px; white-space: pre; opacity: 0; }}',
        f'      .footer-tagline {{ font-size: 13.5px; fill: #e2e8f0; font-weight: 600; text-anchor: middle; opacity: 0; }}',
        f'      .footer-stack {{ font-size: 12.5px; fill: #7d8590; font-weight: 400; text-anchor: middle; opacity: 0; }}',
        f'      .cursor {{ fill: #58a6ff; font-weight: 700; animation: blink 1s infinite; }}',
        f'      ',
        f'      @keyframes fadeIn {{',
        f'        0% {{ opacity: 0; transform: translateY(3px); }}',
        f'        100% {{ opacity: 1; transform: translateY(0); }}',
        f'      }}',
        f'      @keyframes blink {{',
        f'        0%, 49% {{ opacity: 1; }}',
        f'        50%, 100% {{ opacity: 0; }}',
        f'      }}',
        f'      ',
        f'      .boot-1 {{ animation: fadeIn 0.4s ease forwards {t_boot1:.2f}s; }}',
        f'      .boot-2 {{ animation: fadeIn 0.4s ease forwards {t_boot2:.2f}s; }}',
        f'      .boot-3 {{ animation: fadeIn 0.4s ease forwards {t_boot3:.2f}s; }}',
        f'      .boot-4 {{ animation: fadeIn 0.4s ease forwards {t_boot4:.2f}s; }}',
        f'      .name-anim {{ animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards {t_name:.2f}s; }}',
        f'      .role-anim {{ animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards {t_name + 0.2:.2f}s; }}',
        f'      .footer-anim {{ animation: fadeIn 0.8s ease forwards {t_footer:.2f}s; }}',
        f'    </style>',
        f'  </defs>',
        f'  ',
        f'  <!-- Terminal Window Container -->',
        f'  <rect class="bg-rect" x="4" y="4" width="{content_width - 8}" height="{total_height - 8}" />',
        f'  <path class="header-bar" d="M 5 16 A 11 11 0 0 1 16 5 L {content_width - 16} 5 A 11 11 0 0 1 {content_width - 5} 16 L {content_width - 5} 36 L 5 36 Z" />',
        f'  <line x1="5" y1="36" x2="{content_width - 5}" y2="36" stroke="#30363d" stroke-width="1" />',
        f'  ',
        f'  <!-- macOS Window Control Buttons -->',
        f'  <circle cx="26" cy="20" r="6" fill="#ff5f56" />',
        f'  <circle cx="46" cy="20" r="6" fill="#ffbd2e" />',
        f'  <circle cx="66" cy="20" r="6" fill="#27c93f" />',
        f'  <text class="title-text" x="{content_width / 2}" y="24">krishna-prabhav@systems-node ~ profile --render</text>',
        f'  ',
        f'  <!-- Boot Sequence -->',
        f'  <g transform="translate({padding + 10}, 62)">',
        f'    <text class="boot-text boot-1" y="0">&gt; Initializing profile environment...</text>',
        f'    <text class="boot-text boot-2" y="19">&gt; Loading engineer specifications: <tspan fill="#f0f6fc">SWE + AI Systems Engineer</tspan>...</text>',
        f'    <text class="boot-text boot-3" y="38">&gt; Loading distributed systems modules &amp; neural weights...</text>',
        f'    <text class="boot-text boot-4" y="57">&gt; Rendering ASCII self-portrait... <tspan class="boot-success">[OK]</tspan></text>',
        f'  </g>',
        f'  ',
        f'  <!-- Name & Title Banner -->',
        f'  <g transform="translate({padding + 10}, 145)">',
        f'    <text class="name-text name-anim" y="0">{escape_xml(name)}</text>',
        f'    <text class="role-text role-anim" x="{len(name) * 13 + 20}" y="-2">// {escape_xml(title)}</text>',
        f'  </g>',
        f'  ',
        f'  <!-- Animated ASCII Portrait Container -->',
        f'  <g transform="translate({padding + 10}, {header_height})">'
    ]
    
    # Add ASCII lines with staggered animation and subtle gray palette mapping
    for idx, line in enumerate(ascii_lines):
        delay = t_portrait_start + (idx * t_row_step)
        y_pos = (idx + 1) * line_height
        
        # Vary gray shade slightly by row or intensity to create rich depth
        gray_color = PALETTE_GRAYS[idx % len(PALETTE_GRAYS)] if idx % 3 == 0 else "#cbd5e1"
        if idx < num_rows * 0.15 or idx > num_rows * 0.85:
            gray_color = "#64748b"
        elif idx % 2 == 0:
            gray_color = "#94a3b8"
            
        row_style = f'animation: fadeIn 0.35s ease forwards {delay:.3f}s; fill: {gray_color};'
        svg_parts.append(f'    <text class="ascii-row" x="0" y="{y_pos}" style="{row_style}">{line}</text>')
        
    # Add blinking cursor after portrait finishes
    cursor_x = max(10, min(content_width - padding * 2, int(max_line_len * char_width) + 12))
    cursor_y = num_rows * line_height
    svg_parts.append(f'    <text class="ascii-row cursor" x="{cursor_x}" y="{cursor_y}" style="animation: fadeIn 0.1s forwards {t_footer:.2f}s, blink 1s infinite {t_footer:.2f}s;">█</text>')
    svg_parts.append('  </g>')
    
    # Footer Section (Tagline & Tech Stack)
    footer_y = header_height + portrait_height + 40
    svg_parts.extend([
        f'  <line x1="{padding}" y1="{footer_y - 18}" x2="{content_width - padding}" y2="{footer_y - 18}" stroke="#21262d" stroke-width="1" />',
        f'  <g class="footer-anim" transform="translate({content_width / 2}, {footer_y})">',
        f'    <text class="footer-tagline" y="8">{escape_xml(tagline)}</text>',
        f'    <text class="footer-stack" y="32">{escape_xml(stack)}</text>',
        f'  </g>',
        f'</svg>'
    ])
    
    # Ensure directory exists and write
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))
    print(f"-> Successfully generated animated SVG: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Animated ASCII Self-Portrait SVG for GitHub Profile")
    parser.add_argument("input", nargs="?", default="", help="Path to input photo (e.g. assets/photo.jpg)")
    parser.add_argument("output", nargs="?", default="assets/ascii.svg", help="Path to output SVG (default: assets/ascii.svg)")
    parser.add_argument("--demo", action="store_true", help="Generate demo avatar silhouette without an input photo")
    parser.add_argument("--cols", type=int, default=82, help="Number of character columns (default: 82)")
    parser.add_argument("--max-rows", type=int, default=42, help="Maximum portrait rows/height (default: 42)")
    parser.add_argument("--charset", choices=list(ASCII_CHARSETS.keys()), default="detailed", help="Character density set to use")
    parser.add_argument("--remove-bg", action="store_true", help="Use rembg AI background removal before processing")
    parser.add_argument("--name", default="KRISHNA PRABHAV", help="Name to display on header")
    parser.add_argument("--title", default="SWE & AI Systems Engineer", help="Role/Title subtitle")
    parser.add_argument("--tagline", default="Building scalable software • Distributed Systems • AI", help="Footer tagline text")
    parser.add_argument("--stack", default="Go • Python • TypeScript • Redis • PostgreSQL • PyTorch • ONNX", help="Tech stack summary")
    parser.add_argument("--contrast", type=float, default=1.3, help="Contrast enhancement factor (default: 1.3)")
    parser.add_argument("--invert", action="store_true", help="Invert ASCII density mapping")

    args = parser.parse_args()
    
    print("==========================================================")
    print("  Animated ASCII Self-Portrait SVG Generator (`make_ascii_svg.py`)")
    print("==========================================================")

    if not args.input or args.demo or not os.path.exists(args.input):
        if args.input and not args.demo:
            print(f"Notice: Input file '{args.input}' not found. Generating high-tech demo avatar silhouette...")
        else:
            print("Notice: Generating high-tech demo avatar silhouette (use `python make_ascii_svg.py assets/photo.jpg assets/ascii.svg` when ready with your photo)...")
        ascii_grid = generate_demo_avatar(cols=args.cols, rows=min(args.max_rows, int(args.cols * 0.48)))
    else:
        print(f"-> Loading image: {args.input}")
        img = Image.open(args.input)
        img = remove_background_if_requested(img, use_rembg=args.remove_bg)
        print("-> Preprocessing image and mapping to high-density ASCII grid...")
        img = preprocess_image(img, cols=args.cols, enhance_contrast=args.contrast, max_rows=args.max_rows)
        ascii_grid = image_to_ascii_grid(img, charset_name=args.charset, invert=args.invert)
        
    print(f"-> Generating SVG animation ({len(ascii_grid)} lines x ~{len(ascii_grid[0])} chars)...")
    generate_animated_svg(
        ascii_lines=ascii_grid,
        output_path=args.output,
        name=args.name,
        title=args.title,
        tagline=args.tagline,
        stack=args.stack
    )
    print("==========================================================")
    print("All done! Embed `<img src=\"./assets/ascii.svg\" width=\"860\"/>` inside your README.md.")


if __name__ == "__main__":
    main()
