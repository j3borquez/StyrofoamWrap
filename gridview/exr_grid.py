#!/usr/bin/env python3
"""
exr_grid.py: Read all .exr files in its own folder, arrange them in a grid
on a dark grey background, label each tile with its filename (without extension),
and save as PNG in the same folder.

Usage:
    python exr_grid.py [--cols N] [--input-dir DIR] [--output FILE]

Dependencies:
    pip install OpenEXR Imath numpy pillow
"""
import os
import glob
import math
import argparse

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Requires the OpenEXR module
try:
    import OpenEXR
    import Imath
except ImportError:
    raise ImportError(
        "OpenEXR bindings required. Install with 'pip install OpenEXR Imath'."
    )


def load_exr(path):
    """Load an EXR file and return an 8-bit RGB numpy array."""
    exr_file = OpenEXR.InputFile(path)
    header = exr_file.header()
    dw = header['dataWindow']
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1

    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    channels = []
    try:
        channels = exr_file.channels(['R', 'G', 'B'], pt)
    except Exception:
        # Fallback: single channel
        chan = exr_file.channels(['Y'], pt)[0]
        channels = [chan, chan, chan]

    arrays = [
        np.frombuffer(chan, dtype=np.float32).reshape(height, width)
        for chan in channels
    ]
    img = np.stack(arrays, axis=2)
    img = np.clip(img, 0.0, 1.0)
    return (img * 255).astype(np.uint8)


def create_grid(images, cols, bgcolor=(50, 50, 50)):
    """Compose images into a grid on a colored background."""
    n, h, w = len(images), images[0].shape[0], images[0].shape[1]
    rows = int(math.ceil(n / cols))

    canvas_h, canvas_w = rows * h, cols * w
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[:] = bgcolor

    for idx, img in enumerate(images):
        r, c = divmod(idx, cols)
        y, x = r * h, c * w
        canvas[y:y+h, x:x+w] = img

    return canvas, w, h, rows


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser(
        description="Arrange EXR files in a grid and export labeled PNG using OpenEXR."
    )
    parser.add_argument(
        '--input-dir', default=script_dir,
        help="Directory containing .exr files (default: script directory)"
    )
    parser.add_argument(
        '--output', default=os.path.join(script_dir, 'grid.png'),
        help="Output PNG file path (default: grid.png in script directory)"
    )
    parser.add_argument(
        '--cols', type=int,
        help="Number of columns in grid (default: auto)"
    )
    args = parser.parse_args()

    exr_paths = sorted(glob.glob(os.path.join(args.input_dir, '*.exr')))
    if not exr_paths:
        print(f"No EXR files found in {args.input_dir}")
        return

    imgs = [load_exr(p) for p in exr_paths]

    # Determine columns
    cols = args.cols if args.cols else int(math.ceil(math.sqrt(len(imgs))))

    # Create grid
    grid_np, w, h, rows = create_grid(imgs, cols)

    # Convert to PIL image for labeling
    grid_img = Image.fromarray(grid_np)
    draw = ImageDraw.Draw(grid_img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Label each tile
    for idx, path in enumerate(exr_paths):
        name = os.path.splitext(os.path.basename(path))[0]
        r, c = divmod(idx, cols)
        x = c * w + 5
        y = r * h + 5
        draw.text((x, y), name, fill=(255, 255, 255), font=font)

    # Save result
    grid_img.save(args.output)
    print(f"Saved labeled grid image to {args.output}")


if __name__ == '__main__':
    main()
