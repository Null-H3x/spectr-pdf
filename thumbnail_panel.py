"""Thumbnail panel — left sidebar listing all pages as small images."""
from __future__ import annotations
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui   import QPixmap, QImage
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                              QLabel, QSizePolicy)
from engine.pdf_engine import PdfEngine


class ThumbnailWorker(QThread):
    done = pyqtSignal(int, bytes)

    def __init__(self, data, page, max_h=140):
        super().__init__()
        self._data = data; self._page = page; self._max_h = max_h

    def run(self):
        try:
            png = PdfEngine.render_thumbnail(self._data, self._page, self._max_h)
            self.done.emit(self._page, png)
        except Exception:
            pass


class ThumbnailPanel(QWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(108)
        self.setStyleSheet("background-color: #0D1422;")
        self._data:    bytes = b""
        self._workers: list  = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("PAGES")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(28)
        header.setStyleSheet("""
            QLabel {
                background-color: #0D1422;
                color: #445566;
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 1.2px;
                border-bottom: 1px solid #1F2D40;
            }
        """)
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setSpacing(4)
        self._list.setContentsMargins(4, 4, 4, 4)
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #0D1422;
                border: none;
            }
            QListWidget::item {
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QListWidget::item:selected {
                background-color: #162035;
                border: 2px solid #00F0FF;
            }
            QListWidget::item:hover:!selected {
                background-color: #111827;
            }
        """)
        self._list.itemClicked.connect(lambda item: self.page_selected.emit(
            self._list.row(item)))
        layout.addWidget(self._list)

    def load(self, data: bytes, page_count: int):
        self._data = data
        self._list.clear()
        for i in range(page_count):
            item  = QListWidgetItem()
            label = QLabel(f"{i+1}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(88, 120)
            label.setStyleSheet("QLabel { background-color: #111827; color: #445566; font-size: 9px; }")
            item.setSizeHint(QSize(96, 128))
            self._list.addItem(item)
            self._list.setItemWidget(item, label)
            self._queue(i)

    def _queue(self, index: int):
        w = ThumbnailWorker(self._data, index)
        w.done.connect(self._apply)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        self._workers.append(w)
        w.start()

    @pyqtSlot(int, bytes)
    def _apply(self, index: int, png: bytes):
        item = self._list.item(index)
        if not item: return
        img = QImage.fromData(png)
        pm  = QPixmap.fromImage(img).scaledToWidth(84, Qt.TransformationMode.SmoothTransformation)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(88, 120)
        label.setPixmap(pm)
        label.setStyleSheet("QLabel { background-color: #111827; }")
        self._list.setItemWidget(item, label)

    def highlight(self, index: int):
        self._list.setCurrentRow(index)

    def cancel(self):
        for w in self._workers:
            w.quit(); w.wait(100)
        self._workers.clear()
