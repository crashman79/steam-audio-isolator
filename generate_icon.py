#!/usr/bin/env python3
"""Generate the Steam Audio Isolator icon as a PNG file"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QPen, QBrush, QPolygon
from PyQt5.QtCore import Qt, QPoint
import sys

def create_icon(size=256):
    """Create the custom colored icon"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Scale factor for larger icon
    scale = size / 64.0
    
    # Create gradient (teal/cyan color scheme)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor(0, 180, 180))  # Cyan
    gradient.setColorAt(1, QColor(0, 120, 160))  # Teal
    
    # Draw speaker base (trapezoid) - scaled
    painter.setBrush(QBrush(gradient))
    painter.setPen(QPen(QColor(0, 100, 120), int(2 * scale)))
    speaker_points = [
        QPoint(int(12 * scale), int(20 * scale)),
        QPoint(int(28 * scale), int(16 * scale)),
        QPoint(int(28 * scale), int(48 * scale)),
        QPoint(int(12 * scale), int(44 * scale))
    ]
    painter.drawPolygon(QPolygon(speaker_points))
    
    # Draw speaker cone (small rectangle on left) - scaled
    painter.drawRect(int(8 * scale), int(26 * scale), int(6 * scale), int(12 * scale))
    
    # Draw sound waves (arcs) - scaled
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(0, 200, 200), int(3 * scale)))
    painter.drawArc(int(32 * scale), int(24 * scale), int(8 * scale), int(16 * scale), 90 * 16, 180 * 16)
    painter.drawArc(int(38 * scale), int(20 * scale), int(14 * scale), int(24 * scale), 90 * 16, 180 * 16)
    painter.drawArc(int(44 * scale), int(16 * scale), int(18 * scale), int(32 * scale), 90 * 16, 180 * 16)
    
    painter.end()
    
    return pixmap

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Generate multiple sizes for different use cases
    sizes = [16, 24, 32, 48, 64, 128, 256]
    
    for size in sizes:
        icon = create_icon(size)
        filename = f'steam-audio-isolator-{size}.png'
        icon.save(filename)
        print(f"Generated {filename}")
    
    # Also generate the standard icon name
    icon = create_icon(256)
    icon.save('steam-audio-isolator.png')
    print("Generated steam-audio-isolator.png")
