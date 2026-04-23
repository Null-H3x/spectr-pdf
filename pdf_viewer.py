"""
Spectr PDF — PDF Viewer Widget
Renders PDF pages via PyMuPDF into a Qt scroll area.
Handles zoom, page navigation, and text selection hit areas.
"""

from __future__ import annotations

import io
from typing import Optional

from PyQt6.QtCore import (Qt, QThread, pyqtSignal, QSize, QRect, QPoint,
                           QTimer, pyqtSlot)
from PyQt6.QtGui  import QPixmap, QImage, QPainter, QColor, QPen, QCursor
from PyQt6.QtWidgets import (QWidget, QScrollArea, QVBoxLayout, QLabel,
                               QSizePolicy, QApplication)

from engine.pdf_engine import PdfEngine


# ── Background page renderer ───────────────────────────────────────────────────

class PageRenderWorker(QThread):
    """Renders a single page in a background thread."""
    done = pyqtSignal(int, bytes)   # (page_index, png_bytes)

    def __init__(self, data: bytes, page: int, dpi: float):
        super().__init__()
        self._data = data
        self._page = page
        self._dpi  = dpi

    def run(self):
        try:
            png = PdfEngine.render_page(self._data, self._page, self._dpi)
            self.done.emit(self._page, png)
        except Exception:
            pass


# ── Single page widget ─────────────────────────────────────────────────────────

class PageWidget(QLabel):
    """Displays one rendered PDF page."""

    page_clicked = pyqtSignal(int, float, float)  # page, x_pt, y_pt

    def __init__(self, page_index: int, parent=None):
        super().__init__(parent)
        self._page_index = page_index
        self._pt_width   = 595.0
        self._pt_height  = 842.0
        self._dpi        = 150.0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QLabel {
                background-color: white;
                border: none;
            }
        """)
        self._show_loading()

    def _show_loading(self):
        w = int(self._pt_width * self._dpi / 72)
        h = int(self._pt_height * self._dpi / 72)
        pm = QPixmap(w, h)
        pm.fill(QColor("#F8F8F8"))
        self.setPixmap(pm)
        self.setFixedSize(w, h)

    def set_image(self, png_bytes: bytes, pt_width: float,
                  pt_height: float, dpi: float):
        self._pt_width  = pt_width
        self._pt_height = pt_height
        self._dpi       = dpi
        img = QImage.fromData(png_bytes)
        pm  = QPixmap.fromImage(img)
        self.setPixmap(pm)
        self.setFixedSize(pm.size())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pm = self.pixmap()
            if pm and not pm.isNull():
                scale = self._pt_width / pm.width()
                x_pt  = event.position().x() * scale
                y_pt  = event.position().y() * scale
                self.page_clicked.emit(self._page_index, x_pt, y_pt)
        super().mousePressEvent(event)


# ── Main viewer ────────────────────────────────────────────────────────────────

class PdfViewer(QScrollArea):
    """
    Scrollable PDF viewer. Pages are rendered in background threads
    and cached. Zoom level is adjustable.
    """

    page_changed   = pyqtSignal(int)          # current visible page index
    page_clicked   = pyqtSignal(int, float, float)  # page, x_pt, y_pt
    doc_loaded     = pyqtSignal(int)          # page_count

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data:     Optional[bytes] = None
        self._pages:    list            = []   # PageInfo list
        self._zoom:     float           = 1.0
        self._dpi:      float           = 150.0
        self._cache:    dict[int, bytes]= {}   # page_index → png bytes
        self._workers:  list            = []
        self._widgets:  list[PageWidget]= []
        self._current:  int             = 0

        # Central container
        self._container = QWidget()
        self._container.setStyleSheet("background-color: #070B14;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setSpacing(16)
        self._layout.setContentsMargins(40, 24, 40, 24)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setStyleSheet("QScrollArea { border: none; background-color: #070B14; }")

        # Scroll → update current page indicator
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    # ── Public API ─────────────────────────────────────────────────────────────

    def load_document(self, data: bytes, pages: list) -> None:
        """Load a new document. pages = list of PageInfo."""
        # Cancel workers FIRST so they don't write into the new doc's widgets
        self._cancel_workers()
        self._data    = data
        self._pages   = pages
        self._cache   = {}
        self._current = 0

        # Clear old widgets
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets = []

        if not data or not pages:
            self.doc_loaded.emit(0)
            return

        # Create placeholder widgets
        for i, pg in enumerate(pages):
            w = PageWidget(i)
            w._pt_width  = pg.width
            w._pt_height = pg.height
            w._show_loading()
            w.page_clicked.connect(self.page_clicked)
            self._layout.addWidget(w, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._widgets.append(w)

        self.doc_loaded.emit(len(pages))
        QTimer.singleShot(100, self._render_visible)

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.25, min(zoom, 5.0))
        self._cache.clear()
        self._cancel_workers()
        for w in self._widgets:
            w._show_loading()
        QTimer.singleShot(50, self._render_visible)

    def go_to_page(self, index: int) -> None:
        if not self._widgets or index < 0 or index >= len(self._widgets):
            return
        w = self._widgets[index]
        self.ensureWidgetVisible(w)
        self._current = index
        self.page_changed.emit(index)

    def current_page(self) -> int:
        return self._current

    def reload(self, new_data: bytes) -> None:
        """Reload with updated PDF bytes (after an operation)."""
        self._cancel_workers()
        self._cache.clear()
        self._data = new_data
        for w in self._widgets:
            w._show_loading()
        QTimer.singleShot(100, self._render_visible)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _effective_dpi(self) -> float:
        return self._dpi * self._zoom

    def _render_visible(self) -> None:
        """Queue rendering for pages currently in the viewport."""
        if not self._data or not self._widgets:
            return
        viewport_rect = QRect(
            self.horizontalScrollBar().value(),
            self.verticalScrollBar().value(),
            self.viewport().width(),
            self.viewport().height(),
        )
        dpi = self._effective_dpi()
        for i, w in enumerate(self._widgets):
            if i in self._cache:
                self._apply_cache(i)
                continue
            widget_rect = QRect(
                w.pos().x(), w.pos().y(), w.width(), w.height())
            if viewport_rect.intersects(widget_rect):
                self._queue_render(i, dpi)

    def _queue_render(self, index: int, dpi: float) -> None:
        worker = PageRenderWorker(self._data, index, dpi)
        worker.done.connect(self._on_page_rendered)
        worker.finished.connect(lambda: self._workers.remove(worker)
                                if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(int, bytes)
    def _on_page_rendered(self, index: int, png_bytes: bytes) -> None:
        self._cache[index] = png_bytes
        self._apply_cache(index)

    def _apply_cache(self, index: int) -> None:
        if index >= len(self._widgets) or index not in self._cache:
            return
        w   = self._widgets[index]
        pg  = self._pages[index]
        dpi = self._effective_dpi()
        w.set_image(self._cache[index], pg.width, pg.height, dpi)

    def _cancel_workers(self) -> None:
        for w in self._workers:
            w.quit()
            if not w.wait(200):   # 200ms grace period
                w.terminate()
                w.wait(100)
        self._workers.clear()

    def _on_scroll(self) -> None:
        """Update current page indicator on scroll."""
        if not self._widgets:
            return
        vp_center = (self.verticalScrollBar().value()
                     + self.viewport().height() // 2)
        for i, w in enumerate(self._widgets):
            top = w.pos().y()
            if top <= vp_center <= top + w.height():
                if i != self._current:
                    self._current = i
                    self.page_changed.emit(i)
                    # Lazy-render nearby pages
                    for j in range(max(0,i-1), min(len(self._widgets),i+3)):
                        if j not in self._cache:
                            self._queue_render(j, self._effective_dpi())
                break

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_zoom(self._zoom + 0.1)
            else:
                self.set_zoom(self._zoom - 0.1)
            event.accept()
        else:
            super().wheelEvent(event)
