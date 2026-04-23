"""
Spectr PDF — Main Window
The top-level QMainWindow. Owns the menu bar, toolbar, viewer,
thumbnail panel, and all tool dock widgets.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore  import Qt, QTimer, pyqtSlot, QSettings
from PyQt6.QtGui   import (QAction, QIcon, QPixmap,
                            QFont, QColor)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QDockWidget, QToolBar,
    QLabel, QSpinBox, QComboBox, QSlider, QFileDialog,
    QMessageBox, QApplication, QStatusBar, QProgressBar,
    QSizePolicy,
)

from engine.pdf_engine  import PdfEngine, PdfDoc
from viewer.pdf_viewer   import PdfViewer
from viewer.thumbnail_panel import ThumbnailPanel
from panels.tool_panels  import (PagesPanel, AnnotatePanel, RedactPanel,
                                  OcrPanel, ConvertPanel, DiffPanel)
from panels.cac_panel    import CacSignPanel


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._doc:    PdfDoc | None = None
        self._modified: bool        = False

        self.setWindowTitle("Spectr PDF")
        self.resize(1280, 840)
        self.setMinimumSize(900, 600)

        # ── Settings persistence ──────────────────────────────────────────────
        self._settings = QSettings("Null-H3x", "SpectrPDF")

        # ── Viewer ────────────────────────────────────────────────────────────
        self._viewer = PdfViewer()
        self._viewer.page_changed.connect(self._on_page_changed)
        self._viewer.doc_loaded.connect(self._on_doc_loaded)
        # Connect zoom label update once here, not inside _on_doc_loaded
        self._viewer.page_changed.connect(
            lambda _: self._zoom_label.setText(
                f"{int(self._viewer._zoom * 100)}%"))

        # ── Thumbnail panel ───────────────────────────────────────────────────
        self._thumbs = ThumbnailPanel()
        self._thumbs.page_selected.connect(self._viewer.go_to_page)

        # ── Central splitter ──────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._thumbs)
        splitter.addWidget(self._viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([110, 1170])
        self.setCentralWidget(splitter)

        # ── Tool panels ───────────────────────────────────────────────────────
        self._pages_panel   = PagesPanel(PdfEngine)
        self._annot_panel   = AnnotatePanel(PdfEngine)
        self._redact_panel  = RedactPanel(PdfEngine)
        self._ocr_panel     = OcrPanel(PdfEngine)
        self._convert_panel = ConvertPanel(PdfEngine)
        self._diff_panel    = DiffPanel(PdfEngine)
        self._cac_panel     = CacSignPanel()

        # Connect result signals
        for panel in [self._pages_panel, self._annot_panel,
                      self._redact_panel, self._ocr_panel,
                      self._convert_panel, self._cac_panel]:
            panel.result_ready.connect(self._on_operation_result)
            if hasattr(panel, "status_message"):
                panel.status_message.connect(self._status)

        self._docks: dict[str, QDockWidget] = {}
        self._add_dock("Pages",    self._pages_panel)
        self._add_dock("Annotate", self._annot_panel)
        self._add_dock("Redact",   self._redact_panel)
        self._add_dock("OCR",      self._ocr_panel)
        self._add_dock("Convert",  self._convert_panel)
        self._add_dock("Diff",     self._diff_panel)
        self._add_dock("Sign / CAC", self._cac_panel)

        # Show only Pages by default, hide others
        for name, dock in self._docks.items():
            dock.setVisible(name == "Pages")

        # ── Menu + toolbar ────────────────────────────────────────────────────
        self._build_menu()
        self._build_toolbar()

        # ── Status bar ────────────────────────────────────────────────────────
        sb = self.statusBar()
        self._status_label = QLabel("Ready")
        self._zoom_label   = QLabel("100%")
        self._page_label   = QLabel("")
        sb.addWidget(self._status_label, 1)
        sb.addPermanentWidget(self._page_label)
        sb.addPermanentWidget(self._zoom_label)

        # ── Restore geometry ──────────────────────────────────────────────────
        geom = self._settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        state = self._settings.value("windowState")
        if state:
            self.restoreState(state)

    # ── Dock helpers ──────────────────────────────────────────────────────────

    def _add_dock(self, name: str, widget: QWidget) -> QDockWidget:
        dock = QDockWidget(name, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable,
        )
        dock.setMinimumWidth(240)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._docks[name] = dock

        # Tabify all docks together
        if len(self._docks) > 1:
            first_dock = list(self._docks.values())[0]
            self.tabifyDockWidget(first_dock, dock)

        return dock

    # ── Menu bar ───────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        # File
        fm = mb.addMenu("&File")
        self._act_open   = QAction("&Open…",    self); self._act_open.setShortcut("Ctrl+O")
        self._act_save   = QAction("&Save",      self); self._act_save.setShortcut("Ctrl+S")
        self._act_saveas = QAction("Save &As…", self); self._act_saveas.setShortcut("Ctrl+Shift+S")
        self._act_close  = QAction("&Close",     self); self._act_close.setShortcut("Ctrl+W")
        self._act_quit   = QAction("&Quit",      self); self._act_quit.setShortcut("Ctrl+Q")
        self._act_open.triggered.connect(self.open_file_dialog)
        self._act_save.triggered.connect(self.save_file)
        self._act_saveas.triggered.connect(self.save_file_as)
        self._act_close.triggered.connect(self.close_document)
        self._act_quit.triggered.connect(QApplication.quit)
        for a in [self._act_open, self._act_save, self._act_saveas,
                  self._act_close, None, self._act_quit]:
            if a is None: fm.addSeparator()
            else: fm.addAction(a)

        # View
        vm = mb.addMenu("&View")
        self._act_zoom_in  = QAction("Zoom &In",    self); self._act_zoom_in.setShortcut("Ctrl++")
        self._act_zoom_out = QAction("Zoom &Out",   self); self._act_zoom_out.setShortcut("Ctrl+-")
        self._act_zoom_fit = QAction("&Fit Page",   self); self._act_zoom_fit.setShortcut("Ctrl+0")
        self._act_zoom_in.triggered.connect(lambda: self._viewer.set_zoom(self._viewer._zoom + 0.25))
        self._act_zoom_out.triggered.connect(lambda: self._viewer.set_zoom(self._viewer._zoom - 0.25))
        self._act_zoom_fit.triggered.connect(lambda: self._viewer.set_zoom(1.0))
        for a in [self._act_zoom_in, self._act_zoom_out, self._act_zoom_fit]:
            vm.addAction(a)
        vm.addSeparator()
        # Toggle panels
        for name, dock in self._docks.items():
            vm.addAction(dock.toggleViewAction())

        # Tools
        tm = mb.addMenu("&Tools")
        for name, dock in self._docks.items():
            act = QAction(name, self)
            act.triggered.connect(lambda checked, d=dock: (d.show(), d.raise_()))
            tm.addAction(act)

        # Help
        hm = mb.addMenu("&Help")
        about_act = QAction("&About Spectr PDF", self)
        about_act.triggered.connect(self._show_about)
        hm.addAction(about_act)

    # ── Toolbar ────────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setObjectName("MainToolbar")
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize().__class__(20, 20))

        def btn(text: str, tip: str, slot) -> QAction:
            a = QAction(text, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        btn("Open",   "Open PDF  Ctrl+O",  self.open_file_dialog)
        btn("Save",   "Save  Ctrl+S",       self.save_file)
        tb.addSeparator()
        btn("Zoom +", "Zoom in  Ctrl++",   lambda: self._viewer.set_zoom(self._viewer._zoom + 0.25))
        btn("Zoom -", "Zoom out  Ctrl+-",  lambda: self._viewer.set_zoom(self._viewer._zoom - 0.25))
        btn("Fit",    "Fit page  Ctrl+0",  lambda: self._viewer.set_zoom(1.0))
        tb.addSeparator()

        # Page navigation
        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(1)
        self._page_spin.setFixedWidth(60)
        self._page_spin.setToolTip("Go to page")
        self._page_spin.valueChanged.connect(
            lambda v: self._viewer.go_to_page(v - 1))
        self._total_lbl = QLabel("/ 1")
        self._total_lbl.setStyleSheet("color: #8899AA; margin: 0 6px;")
        tb.addWidget(self._page_spin)
        tb.addWidget(self._total_lbl)
        tb.addSeparator()

        # Tool panel shortcuts
        for name in ["Pages", "Annotate", "Redact", "OCR", "Convert", "Sign / CAC"]:
            dock = self._docks[name]
            short_name = name.split("/")[0].strip()
            a = QAction(short_name, self)
            a.setToolTip(f"Open {name} panel")
            a.setCheckable(True)
            a.triggered.connect(lambda checked, d=dock: d.setVisible(checked))
            dock.visibilityChanged.connect(a.setChecked)
            tb.addAction(a)

    # ── File operations ────────────────────────────────────────────────────────

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf);;All Files (*)")
        if path:
            self.open_file(path)

    def open_file(self, path: str):
        try:
            doc = PdfEngine.open_file(path)
            self._load_doc(doc)
        except Exception as e:
            QMessageBox.critical(self, "Error opening file", str(e))

    def _load_doc(self, doc: PdfDoc):
        self._doc       = doc
        self._modified  = False
        self.setWindowTitle(f"Spectr PDF — {doc.filename}")

        # Update UI
        self._page_spin.setMaximum(doc.page_count)
        self._page_spin.setValue(1)
        self._total_lbl.setText(f"/ {doc.page_count}")

        # Load into panels
        for panel in [self._pages_panel, self._annot_panel,
                      self._redact_panel, self._ocr_panel,
                      self._convert_panel, self._cac_panel]:
            if hasattr(panel, "set_document"):
                panel.set_document(doc)

        # Load viewer + thumbnails
        self._thumbs.load(doc.bytes_data, doc.page_count)
        self._viewer.load_document(doc.bytes_data, doc.pages)
        self._status(f"Opened: {doc.filename}  ({doc.page_count} pages)")

    def save_file(self):
        if not self._doc: return
        if self._doc.path:
            self._write(self._doc.path)
        else:
            self.save_file_as()

    def save_file_as(self):
        if not self._doc: return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF As", self._doc.filename, "PDF Files (*.pdf)")
        if path:
            self._write(path)

    def _write(self, path: str):
        try:
            with open(path, "wb") as f:
                f.write(self._doc.bytes_data)
            self._modified = False
            self._doc = PdfEngine.open_bytes(self._doc.bytes_data, path)
            self.setWindowTitle(f"Spectr PDF — {self._doc.filename}")
            self._status(f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def close_document(self):
        if self._modified:
            reply = QMessageBox.question(
                self, "Close",
                "Document has unsaved changes. Close without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes: return
        self._doc = None
        self._modified = False
        self._viewer.load_document(b"", [])
        self._thumbs.cancel()
        self.setWindowTitle("Spectr PDF")
        self._status("Document closed")

    # ── Operation result ───────────────────────────────────────────────────────

    @pyqtSlot(bytes, str)
    def _on_operation_result(self, new_bytes: bytes, description: str):
        """Called when any panel produces a modified PDF."""
        if not new_bytes: return
        new_doc = PdfEngine.open_bytes(new_bytes, self._doc.path if self._doc else "")
        self._doc      = new_doc
        self._modified = True
        self.setWindowTitle(f"Spectr PDF — {new_doc.filename} *")

        # Refresh panels
        for panel in [self._pages_panel, self._annot_panel,
                      self._redact_panel, self._ocr_panel,
                      self._convert_panel, self._cac_panel]:
            if hasattr(panel, "set_document"):
                panel.set_document(new_doc)

        # Refresh thumbnails + viewer
        self._thumbs.cancel()
        self._thumbs.load(new_bytes, new_doc.page_count)
        self._viewer.reload(new_bytes)
        self._page_spin.setMaximum(new_doc.page_count)
        self._total_lbl.setText(f"/ {new_doc.page_count}")
        self._status(f"✓  {description}")

    # ── UI callbacks ───────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def _on_page_changed(self, page: int):
        self._page_spin.blockSignals(True)
        self._page_spin.setValue(page + 1)
        self._page_spin.blockSignals(False)
        self._thumbs.highlight(page)
        if self._doc:
            pg = self._doc.pages[page]
            self._page_label.setText(
                f"Page {page+1} / {self._doc.page_count}"
                f"  ·  {round(pg.width)}×{round(pg.height)} pt"
            )

    @pyqtSlot(int)
    def _on_doc_loaded(self, count: int):
        self._zoom_label.setText("100%")

    def _status(self, msg: str):
        self._status_label.setText(msg)
        QTimer.singleShot(6000, lambda: self._status_label.setText("Ready"))

    # ── About ──────────────────────────────────────────────────────────────────

    def _show_about(self):
        QMessageBox.about(self, "About Spectr PDF",
            "<b>Spectr PDF v1.0.0</b><br>"
            "Free PDF Suite — No cloud, no subscriptions, no BS.<br><br>"
            "Built by Null-H3x (Benjamin Bartunek)<br>"
            "<a href='https://github.com/Null-H3x/spectr-pdf'>"
            "github.com/Null-H3x/spectr-pdf</a><br><br>"
            "Engine: PyMuPDF · pikepdf · pyHanko · Tesseract · OpenCV<br>"
            "UI: PyQt6"
        )

    # ── Drag & drop ────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".pdf") for u in urls):
                event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.open_file(path)
                break

    # ── Keyboard shortcuts ─────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        n   = self._doc.page_count if self._doc else 1
        cur = self._viewer.current_page()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._viewer.go_to_page(max(0, cur - 1))
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._viewer.go_to_page(min(n - 1, cur + 1))
        elif key == Qt.Key.Key_Home:
            self._viewer.go_to_page(0)
        elif key == Qt.Key.Key_End:
            self._viewer.go_to_page(n - 1)
        else:
            super().keyPressEvent(event)

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self._modified:
            reply = QMessageBox.question(
                self, "Quit",
                "Document has unsaved changes. Quit without saving?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self.save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore(); return
        self._settings.setValue("geometry",    self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())
        self._thumbs.cancel()
        event.accept()
