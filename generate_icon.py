#!/usr/bin/env python3
"""Generate the Steam Audio Isolator icon as a PNG file.
   Icon: direct path from source to record target (isolated route).
   Uses Pillow only (no PyQt5). Run: pip install Pillow && python generate_icon.py"""

from PIL import Image, ImageDraw


def create_icon(size=256):
    """Create the custom icon: rounded square with source -> path -> target motif."""
    scale = size / 64.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(4 * scale)
    r = int(12 * scale)
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=r,
        fill=(0, 145, 165),
        outline=(0, 95, 125),
        width=max(1, int(1.5 * scale)),
    )

    # Speaker polygon (trapezoid) + cone rect
    sx, sy = 14 * scale, 36 * scale
    poly = [
        (sx, sy + 10 * scale),
        (sx + 12 * scale, sy + 6 * scale),
        (sx + 12 * scale, sy + 18 * scale),
        (sx, sy + 14 * scale),
    ]
    draw.polygon([(int(a), int(b)) for a, b in poly], fill=(255, 255, 255, 230), outline=(0, 90, 120))
    draw.rectangle(
        [int(sx - 4 * scale), int(sy + 8 * scale), int(sx), int(sy + 14 * scale)],
        fill=(255, 255, 255, 230),
        outline=(0, 90, 120),
    )

    # Bezier curve (approximate with line segments)
    def bezier(t):
        x0, y0 = sx + 14 * scale, sy + 12 * scale
        x1, y1 = size * 0.5, size * 0.35
        x2, y2 = size * 0.65, size * 0.25
        x3, y3 = size - 14 * scale, 14 * scale
        u = 1 - t
        x = u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3
        y = u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3
        return (int(x), int(y))

    pts = [bezier(i / 80) for i in range(81)]
    w = max(2, int(3.5 * scale))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(255, 255, 255), width=w)

    # Target circle
    cx, cy = size - 14 * scale, 14 * scale
    rad = 5 * scale
    draw.ellipse(
        [cx - rad, cy - rad, cx + rad, cy + rad],
        fill=(255, 255, 255),
        outline=(0, 90, 120),
        width=max(1, int(1.2 * scale)),
    )

    return img


if __name__ == '__main__':
    sizes = [16, 24, 32, 48, 64, 128, 256]
    for s in sizes:
        create_icon(s).save(f'steam-audio-isolator-{s}.png')
        print(f"Generated steam-audio-isolator-{s}.png")
    create_icon(256).save('steam-audio-isolator.png')
    print("Generated steam-audio-isolator.png")
