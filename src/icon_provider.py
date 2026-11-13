from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFileInfo
import os

class KDEFileIconProvider(QFileIconProvider):
    def icon(self, info: QFileInfo):
        if isinstance(info, str):
            info = QFileInfo(info)
            
        if info.isDir():
            return QIcon.fromTheme("folder", super().icon(info))
            
        ext = info.suffix().lower()
        
        # Map file extensions to standard KDE/Freedesktop icon names
        icon_map = {
            "py": "text-x-python",
            "md": "text-markdown",
            "txt": "text-plain",
            "png": "image-x-generic",
            "jpg": "image-x-generic",
            "ico": "image-x-generic",
            "json": "text-x-generic",
            "sh": "application-x-executable",
        }
        
        icon_name = icon_map.get(ext)
        if icon_name and QIcon.hasThemeIcon(icon_name):
            return QIcon.fromTheme(icon_name)
            
        # Fallback to default provider if no theme icon matches
        return super().icon(info)