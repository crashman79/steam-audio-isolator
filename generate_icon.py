#!/usr/bin/env python3
"""Generate the Steam Audio Isolator icon as a PNG file.
   Icon: direct path from source to record target (isolated route) — distinct from generic Steam/audio icons."""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QLinearGradient, QPen, QBrush,
    QPolygon, QPainterPath
)
from PyQt5.QtCore import Qt, QPoint, QRectF
import sys


def create_icon(size=256):
    """Create the custom icon: rounded square with 'source -> direct path -> target' motif."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    scale = size / 64.0

    # Rounded rect background (slightly inset) — app-icon shape
    margin = 4 * scale
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor(0, 175, 175))
    gradient.setColorAt(1, QColor(0, 115, 155))
    painter.setBrush(QBrush(gradient))
    painter.setPen(QPen(QColor(0, 95, 125), max(1, int(1.5 * scale))))
    painter.drawRoundedRect(rect, 12 * scale, 12 * scale)

    # Source: minimal speaker (small trapezoid + cone) bottom-left
    sx, sy = 14 * scale, 36 * scale
    speaker_points = [
        QPoint(int(sx), int(sy + 10 * scale)),
        QPoint(int(sx + 12 * scale), int(sy + 6 * scale)),
        QPoint(int(sx + 12 * scale), int(sy + 18 * scale)),
        QPoint(int(sx), int(sy + 14 * scale)),
    ]
    painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
    painter.setPen(QPen(QColor(0, 90, 120), max(1, int(1.2 * scale))))
    painter.drawPolygon(QPolygon(speaker_points))
    painter.drawRect(int(sx - 4 * scale), int(sy + 8 * scale), int(4 * scale), int(6 * scale))

    # Direct path: single curved line from source to target (top-right)
    path = QPainterPath()
    path.moveTo(sx + 14 * scale, sy + 12 * scale)
    path.cubicTo(
        size * 0.5, size * 0.35,
        size * 0.65, size * 0.25,
        size - 14 * scale, 14 * scale
    )
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255), max(2, int(3.5 * scale))))
    painter.drawPath(path)

    # Target: small circle (record destination) top-right
    cx = size - 14 * scale
    cy = 14 * scale
    r = 5 * scale
    painter.setBrush(QBrush(QColor(255, 255, 255)))
    painter.setPen(QPen(QColor(0, 90, 120), max(1, int(1.2 * scale))))
    painter.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))

    painter.end()
    return pixmap


if __name__ == '__main__':
    app = QApplication(sys.argv)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    for s in sizes:
        create_icon(s).save(f'steam-audio-isolator-{s}.png')
        print(f"Generated steam-audio-isolator-{s}.png")

    create_icon(256).save('steam-audio-isolator.png')
    print("Generated steam-audio-isolator.png")
