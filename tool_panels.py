"""
Spectr PDF — Tool Panels
Each panel lives in a QDockWidget and operates directly on the engine.
Panels emit result_ready(bytes) when an operation produces new PDF bytes.
"""

from __future__ import annotations
import os, sys, json

# Ensure engine/ and utils/ are importable regardless of working directory
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)   # windows_app/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.range_parser import parse_ranges
from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QComboBox, QCheckBox, QGroupBox,
    QListWidget, QListWidgetItem, QTextEdit, QFileDialog,
    QMessageBox, QProgressBar, QScrollArea, QFrame,
    QSizePolicy, QSlider, QTabWidget, QDialog, QDialogButtonBox,
    QFormLayout,
)
from PyQt6.QtGui import QColor


def _section(title: str) -> QGroupBox:
    g = QGroupBox(title)
    return g


def _btn(text: str, primary: bool = False, danger: bool = False) -> QPushButton:
    b = QPushButton(text)
    if not primary:
        b.setProperty("flat", "true")
    if danger:
        b.setProperty("danger", "true")
    return b


def _label(text: str, muted: bool = False) -> QLabel:
    lb = QLabel(text)
    if muted:
        lb.setProperty("muted", "true")
    return lb


# ─────────────────────────────────────────────────────────────────────────────
# PAGES PANEL
# ─────────────────────────────────────────────────────────────────────────────

class PagesPanel(QWidget):
    result_ready     = pyqtSignal(bytes, str)   # (new_pdf, description)
    request_file     = pyqtSignal()             # trigger open-file dialog
    status_message   = pyqtSignal(str)

    def __init__(self, engine_ref, parent=None):
        super().__init__(parent)
        self._eng   = engine_ref
        self._doc   = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Merge ────────────────────────────────────────────────────────────
        mg = _section("Merge PDFs")
        ml = QVBoxLayout(mg)
        self._merge_list = QListWidget()
        self._merge_list.setFixedHeight(90)
        ml.addWidget(self._merge_list)
        brow = QHBoxLayout()
        b_add = _btn("Add Files…"); b_add.clicked.connect(self._add_merge_files)
        b_clr = _btn("Clear");      b_clr.clicked.connect(self._merge_list.clear)
        b_mrg = QPushButton("Merge"); b_mrg.clicked.connect(self._run_merge)
        brow.addWidget(b_add); brow.addWidget(b_clr); brow.addStretch()
        brow.addWidget(b_mrg)
        ml.addLayout(brow)
        layout.addWidget(mg)

        # ── Split ─────────────────────────────────────────────────────────────
        sg = _section("Split PDF")
        sl = QVBoxLayout(sg)
        sl.addWidget(_label("Page ranges  (e.g.  1-3, 5, 8-end)", muted=True))
        self._split_edit = QLineEdit(); self._split_edit.setPlaceholderText("1-3, 4-end")
        b_split = QPushButton("Split to ZIP"); b_split.clicked.connect(self._run_split)
        sl.addWidget(self._split_edit); sl.addWidget(b_split)
        layout.addWidget(sg)

        # ── Rotate ────────────────────────────────────────────────────────────
        rg = _section("Rotate Pages")
        rl = QHBoxLayout(rg)
        self._rot_cb = QComboBox()
        self._rot_cb.addItems(["All pages", "Odd pages", "Even pages"])
        self._rot_deg = QComboBox()
        self._rot_deg.addItems(["90° CW", "180°", "90° CCW"])
        b_rot = QPushButton("Rotate"); b_rot.clicked.connect(self._run_rotate)
        rl.addWidget(self._rot_cb); rl.addWidget(self._rot_deg)
        rl.addStretch(); rl.addWidget(b_rot)
        layout.addWidget(rg)

        # ── Delete ────────────────────────────────────────────────────────────
        dg = _section("Delete Pages")
        dl = QVBoxLayout(dg)
        dl.addWidget(_label("Page numbers to delete  (e.g.  1, 3, 5-7)", muted=True))
        self._del_edit = QLineEdit(); self._del_edit.setPlaceholderText("2, 4-6")
        b_del = QPushButton("Delete")
        b_del.setProperty("danger","true"); b_del.clicked.connect(self._run_delete)
        dl.addWidget(self._del_edit); dl.addWidget(b_del)
        layout.addWidget(dg)

        layout.addStretch()

    def set_document(self, doc): self._doc = doc

    def _add_merge_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDFs to merge", "", "PDF Files (*.pdf)")
        for f in files:
            self._merge_list.addItem(f)

    def _run_merge(self):
        paths = [self._merge_list.item(i).text()
                 for i in range(self._merge_list.count())]
        if len(paths) < 2:
            QMessageBox.information(self, "Merge", "Add at least 2 PDF files."); return
        try:
            from engine.pdf_engine import PdfEngine
            blobs = []
            for p in paths:
                with open(p, "rb") as f:
                    blobs.append(f.read())
            result = PdfEngine.merge(blobs)
            self.result_ready.emit(result, f"Merged {len(blobs)} PDFs")
            self._merge_list.clear()
        except Exception as e:
            QMessageBox.critical(self, "Merge failed", str(e))

    def _run_split(self):
        if not self._doc: return
        text = self._split_edit.text().strip()
        if not text: return
        try:
            ranges = parse_ranges(text, self._doc.page_count)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid ranges", str(e)); return
        try:
            from engine.pdf_engine import PdfEngine
            import zipfile, io
            parts  = PdfEngine.split(self._doc.bytes_data, ranges)
            out, _ = QFileDialog.getSaveFileName(
                self,"Save Split ZIP","split_output.zip","ZIP (*.zip)")
            if not out: return
            with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as zf:
                for i, part in enumerate(parts):
                    zf.writestr(f"part_{i+1}.pdf", part)
            self.status_message.emit(f"Split → {out}")
        except Exception as e:
            QMessageBox.critical(self,"Split failed",str(e))

    def _run_rotate(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        sel     = self._rot_cb.currentIndex()
        deg_map = {0: 90, 1: 180, 2: 270}
        deg     = deg_map[self._rot_deg.currentIndex()]
        count   = self._doc.page_count
        if sel == 0:   pages = []
        elif sel == 1: pages = list(range(0, count, 2))
        else:          pages = list(range(1, count, 2))
        try:
            result = PdfEngine.rotate(self._doc.bytes_data, pages, deg)
            self.result_ready.emit(result, f"Rotated {deg}°")
        except Exception as e:
            QMessageBox.critical(self,"Rotate failed",str(e))

    def _run_delete(self):
        if not self._doc: return
        text = self._del_edit.text().strip()
        if not text: return
        try:
            ranges = parse_ranges(text, self._doc.page_count)
            pages  = sorted(set(p for s,e in ranges for p in range(s,e+1)))
        except ValueError as e:
            QMessageBox.warning(self,"Invalid pages",str(e)); return
        reply = QMessageBox.question(self,"Confirm Delete",
            f"Permanently delete {len(pages)} page(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        from engine.pdf_engine import PdfEngine
        try:
            result = PdfEngine.delete_pages(self._doc.bytes_data, pages)
            self.result_ready.emit(result, f"Deleted {len(pages)} page(s)")
            self._del_edit.clear()
        except Exception as e:
            QMessageBox.critical(self,"Delete failed",str(e))


# ─────────────────────────────────────────────────────────────────────────────
# ANNOTATE PANEL
# ─────────────────────────────────────────────────────────────────────────────

class AnnotatePanel(QWidget):
    result_ready   = pyqtSignal(bytes, str)
    status_message = pyqtSignal(str)
    # Mode changed — viewer enters annotation capture mode
    annotation_mode = pyqtSignal(str)  # "sticky_note", "freetext", "highlight", ""

    def __init__(self, engine_ref, parent=None):
        super().__init__(parent)
        self._eng = engine_ref; self._doc = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8,8,8,8); layout.setSpacing(8)

        # ── Sticky note ───────────────────────────────────────────────────────
        sg = _section("Sticky Note")
        sl = QVBoxLayout(sg)
        self._note_page   = QSpinBox(); self._note_page.setMinimum(1)
        self._note_author = QLineEdit(); self._note_author.setPlaceholderText("Author")
        self._note_text   = QTextEdit(); self._note_text.setPlaceholderText("Note content…")
        self._note_text.setFixedHeight(70)
        fr = QFormLayout()
        fr.addRow("Page:", self._note_page)
        fr.addRow("Author:", self._note_author)
        sl.addLayout(fr); sl.addWidget(self._note_text)
        b_note = QPushButton("Add Sticky Note")
        b_note.clicked.connect(self._add_sticky)
        sl.addWidget(b_note)
        layout.addWidget(sg)

        # ── Freetext ──────────────────────────────────────────────────────────
        fg = _section("Text Box")
        fl = QVBoxLayout(fg)
        self._ft_page    = QSpinBox(); self._ft_page.setMinimum(1)
        self._ft_text    = QLineEdit(); self._ft_text.setPlaceholderText("Text content")
        self._ft_x       = QSpinBox(); self._ft_x.setRange(0,2000); self._ft_x.setValue(72)
        self._ft_y       = QSpinBox(); self._ft_y.setRange(0,3000); self._ft_y.setValue(200)
        self._ft_size    = QSpinBox(); self._ft_size.setRange(6,72); self._ft_size.setValue(12)
        fr2 = QFormLayout()
        fr2.addRow("Page:", self._ft_page); fr2.addRow("Text:", self._ft_text)
        fr2.addRow("X (pt):", self._ft_x); fr2.addRow("Y (pt):", self._ft_y)
        fr2.addRow("Font size:", self._ft_size)
        fl.addLayout(fr2)
        b_ft = QPushButton("Add Text Box")
        b_ft.clicked.connect(self._add_freetext)
        fl.addWidget(b_ft)
        layout.addWidget(fg)

        # ── Manage ────────────────────────────────────────────────────────────
        mg = _section("Manage")
        ml = QVBoxLayout(mg)
        b_list    = _btn("List All Annotations"); b_list.clicked.connect(self._list_annots)
        b_flatten = _btn("Flatten (bake permanently)")
        b_flatten.clicked.connect(self._flatten)
        ml.addWidget(b_list); ml.addWidget(b_flatten)
        layout.addWidget(mg)

        layout.addStretch()

    def set_document(self, doc):
        self._doc = doc
        if doc:
            self._note_page.setMaximum(doc.page_count)
            self._ft_page.setMaximum(doc.page_count)

    def _add_sticky(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        pg   = self._note_page.value() - 1
        text = self._note_text.toPlainText().strip()
        if not text: return
        try:
            result = PdfEngine.add_sticky_note(
                self._doc.bytes_data, pg, 72, 100,
                text, author=self._note_author.text())
            self.result_ready.emit(result, "Sticky note added")
            self._note_text.clear()
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))

    def _add_freetext(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        pg   = self._ft_page.value() - 1
        text = self._ft_text.text().strip()
        if not text: return
        x    = float(self._ft_x.value())
        y    = float(self._ft_y.value())
        fs   = float(self._ft_size.value())
        rect = [x, y, x + fs * len(text) * 0.6, y + fs * 1.4]
        try:
            result = PdfEngine.add_freetext(
                self._doc.bytes_data, pg, rect, text, fontsize=fs)
            self.result_ready.emit(result, "Text box added")
            self._ft_text.clear()
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))

    def _list_annots(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        annots = PdfEngine.list_annotations(self._doc.bytes_data)
        msg = f"{len(annots)} annotation(s):\n\n"
        for a in annots[:20]:
            msg += f"  p{a['page']+1}  {a['type']}  {a.get('content','')[:40]}\n"
        if len(annots) > 20:
            msg += f"\n  ... and {len(annots)-20} more"
        QMessageBox.information(self, "Annotations", msg)

    def _flatten(self):
        if not self._doc: return
        reply = QMessageBox.question(self,"Flatten","Bake all annotations permanently? This cannot be undone.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        from engine.pdf_engine import PdfEngine
        try:
            result = PdfEngine.flatten_annotations(self._doc.bytes_data)
            self.result_ready.emit(result,"Annotations flattened")
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))


# ─────────────────────────────────────────────────────────────────────────────
# REDACT PANEL
# ─────────────────────────────────────────────────────────────────────────────

class RedactPanel(QWidget):
    result_ready   = pyqtSignal(bytes, str)
    status_message = pyqtSignal(str)

    def __init__(self, engine_ref, parent=None):
        super().__init__(parent)
        self._eng = engine_ref; self._doc = None
        self._hits = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8,8,8,8); layout.setSpacing(8)

        # ── Find & redact ─────────────────────────────────────────────────────
        fg = _section("Find & Redact Text")
        fl = QVBoxLayout(fg)
        fl.addWidget(_label("Search for text to redact everywhere it appears:", muted=True))
        row = QHBoxLayout()
        self._search = QLineEdit(); self._search.setPlaceholderText("Text to redact…")
        self._cs     = QCheckBox("Case-sensitive")
        b_find       = QPushButton("Find"); b_find.clicked.connect(self._find)
        row.addWidget(self._search); row.addWidget(self._cs); row.addWidget(b_find)
        fl.addLayout(row)
        self._hits_label = _label("", muted=True)
        b_redact = QPushButton("Redact All Matches")
        b_redact.setProperty("danger","true"); b_redact.clicked.connect(self._redact)
        fl.addWidget(self._hits_label); fl.addWidget(b_redact)
        layout.addWidget(fg)

        # ── Encrypt ───────────────────────────────────────────────────────────
        eg = _section("Password Protect (AES-256)")
        el = QVBoxLayout(eg)
        self._pass1 = QLineEdit(); self._pass1.setPlaceholderText("Password"); self._pass1.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass2 = QLineEdit(); self._pass2.setPlaceholderText("Confirm password"); self._pass2.setEchoMode(QLineEdit.EchoMode.Password)
        self._allow_print = QCheckBox("Allow printing"); self._allow_print.setChecked(True)
        self._allow_copy  = QCheckBox("Allow copying")
        self._allow_edit  = QCheckBox("Allow editing")
        b_enc = QPushButton("Encrypt PDF"); b_enc.clicked.connect(self._encrypt)
        el.addWidget(self._pass1); el.addWidget(self._pass2)
        el.addWidget(self._allow_print); el.addWidget(self._allow_copy)
        el.addWidget(self._allow_edit); el.addWidget(b_enc)
        layout.addWidget(eg)

        # ── Strip metadata ────────────────────────────────────────────────────
        smg = _section("Strip Metadata")
        sml = QVBoxLayout(smg)
        sml.addWidget(_label("Remove author, date, software info.", muted=True))
        b_strip = _btn("Strip Metadata"); b_strip.clicked.connect(self._strip)
        sml.addWidget(b_strip)
        layout.addWidget(smg)

        layout.addStretch()

    def set_document(self, doc): self._doc = doc; self._hits = []

    def _find(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        q = self._search.text().strip()
        if not q: return
        self._hits = PdfEngine.find_text(self._doc.bytes_data, q)
        n = len(self._hits)
        self._hits_label.setText(
            f"Found {n} occurrence(s)" if n else "No matches found")

    def _redact(self):
        if not self._doc or not self._hits: return
        reply = QMessageBox.question(self,"Confirm Redaction",
            f"Permanently redact {len(self._hits)} occurrence(s)? This cannot be undone.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        from engine.pdf_engine import PdfEngine
        try:
            result = PdfEngine.apply_redactions(self._doc.bytes_data, self._hits)
            self.result_ready.emit(result, f"Redacted {len(self._hits)} occurrence(s)")
            self._hits = []; self._hits_label.setText(""); self._search.clear()
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))

    def _encrypt(self):
        if not self._doc: return
        p1 = self._pass1.text(); p2 = self._pass2.text()
        if not p1: QMessageBox.warning(self,"Encrypt","Enter a password."); return
        if p1 != p2: QMessageBox.warning(self,"Encrypt","Passwords don't match."); return
        from engine.pdf_engine import PdfEngine
        try:
            result = PdfEngine.encrypt(self._doc.bytes_data, p1,
                allow_printing=self._allow_print.isChecked(),
                allow_copying=self._allow_copy.isChecked(),
                allow_editing=self._allow_edit.isChecked())
            self.result_ready.emit(result,"PDF encrypted")
            self._pass1.clear(); self._pass2.clear()
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))

    def _strip(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        try:
            result = PdfEngine.strip_metadata(self._doc.bytes_data)
            self.result_ready.emit(result,"Metadata stripped")
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))


# ─────────────────────────────────────────────────────────────────────────────
# OCR PANEL
# ─────────────────────────────────────────────────────────────────────────────

class OcrPanel(QWidget):
    result_ready   = pyqtSignal(bytes, str)
    status_message = pyqtSignal(str)

    def __init__(self, engine_ref, parent=None):
        super().__init__(parent)
        self._eng = engine_ref; self._doc = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8,8,8,8); layout.setSpacing(8)

        sg = _section("OCR Settings")
        sl = QFormLayout(sg)
        self._lang = QLineEdit("eng"); self._lang.setToolTip("Tesseract language code. eng+fra for multiple.")
        self._dpi  = QComboBox(); self._dpi.addItems(["150","200","300"])
        self._dpi.setCurrentIndex(1)
        sl.addRow("Language:", self._lang)
        sl.addRow("DPI:", self._dpi)
        layout.addWidget(sg)

        eg = _section("Extract Text")
        el = QVBoxLayout(eg)
        el.addWidget(_label("Run OCR and extract text from all pages.", muted=True))
        b_ext = QPushButton("Extract Text"); b_ext.clicked.connect(self._extract)
        self._text_out = QTextEdit()
        self._text_out.setReadOnly(True); self._text_out.setFixedHeight(120)
        self._text_out.setPlaceholderText("Extracted text will appear here…")
        el.addWidget(b_ext); el.addWidget(self._text_out)
        layout.addWidget(eg)

        mg = _section("Make Searchable")
        ml = QVBoxLayout(mg)
        ml.addWidget(_label(
            "Overlay invisible text layer over scanned pages.\n"
            "PDF looks the same but text becomes selectable.", muted=True))
        b_srch = QPushButton("Make Searchable PDF"); b_srch.clicked.connect(self._make_searchable)
        ml.addWidget(b_srch)
        layout.addWidget(mg)

        layout.addStretch()

    def set_document(self, doc): self._doc = doc

    def _extract(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        try:
            r = PdfEngine.ocr_extract(
                self._doc.bytes_data,
                lang=self._lang.text() or "eng",
                dpi=int(self._dpi.currentText()))
            self._text_out.setPlainText(r["full_text"])
            self.status_message.emit(f"OCR: extracted text from {len(r['pages'])} page(s)")
        except Exception as e:
            QMessageBox.critical(self,"OCR failed",str(e))

    def _make_searchable(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        try:
            result = PdfEngine.make_searchable(
                self._doc.bytes_data,
                lang=self._lang.text() or "eng",
                dpi=int(self._dpi.currentText()))
            self.result_ready.emit(result,"PDF made searchable")
        except Exception as e:
            QMessageBox.critical(self,"OCR failed",str(e))


# ─────────────────────────────────────────────────────────────────────────────
# CONVERT PANEL
# ─────────────────────────────────────────────────────────────────────────────

class ConvertPanel(QWidget):
    result_ready   = pyqtSignal(bytes, str)
    status_message = pyqtSignal(str)

    def __init__(self, engine_ref, parent=None):
        super().__init__(parent)
        self._eng = engine_ref; self._doc = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8,8,8,8); layout.setSpacing(8)

        ig = _section("PDF → Images")
        il = QVBoxLayout(ig)
        row = QHBoxLayout()
        il.addWidget(_label("DPI:", muted=True))
        self._img_dpi = QComboBox(); self._img_dpi.addItems(["72","150","300"])
        self._img_dpi.setCurrentIndex(1)
        self._img_fmt = QComboBox(); self._img_fmt.addItems(["PNG","JPEG"])
        row.addWidget(self._img_dpi); row.addWidget(self._img_fmt); row.addStretch()
        il.addLayout(row)
        b_img = QPushButton("Export as Images…"); b_img.clicked.connect(self._export_images)
        il.addWidget(b_img)
        layout.addWidget(ig)

        dg = _section("PDF ↔ Word (.docx)")
        dl = QVBoxLayout(dg)
        dl.addWidget(_label("Requires LibreOffice.", muted=True))
        b_docx = QPushButton("Export PDF → DOCX…"); b_docx.clicked.connect(self._to_docx)
        b_imp  = QPushButton("Import DOCX → PDF…"); b_imp.clicked.connect(self._from_docx)
        dl.addWidget(b_docx); dl.addWidget(b_imp)
        layout.addWidget(dg)

        layout.addStretch()

    def set_document(self, doc): self._doc = doc

    def _export_images(self):
        if not self._doc: return
        from engine.pdf_engine import PdfEngine
        import zipfile
        out, _ = QFileDialog.getSaveFileName(self,"Save Images ZIP","images.zip","ZIP (*.zip)")
        if not out: return
        dpi = int(self._img_dpi.currentText())
        fmt = self._img_fmt.currentText().lower()
        try:
            imgs = PdfEngine.to_images(self._doc.bytes_data, dpi=dpi, fmt=fmt)
            ext  = "jpg" if fmt=="jpeg" else "png"
            with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as zf:
                for i, img in enumerate(imgs):
                    zf.writestr(f"page_{i+1:04d}.{ext}", img)
            self.status_message.emit(f"Exported {len(imgs)} images → {out}")
        except Exception as e:
            QMessageBox.critical(self,"Export failed",str(e))

    def _to_docx(self):
        if not self._doc: return
        import tempfile, shutil
        from engine.pdf_engine import PdfEngine
        out, _ = QFileDialog.getSaveFileName(self,"Save DOCX","document.docx","Word (*.docx)")
        if not out: return
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf",delete=False) as f:
                f.write(self._doc.bytes_data); tmp = f.name
            PdfEngine.to_docx(self._doc.bytes_data, out)
            os.unlink(tmp)
            self.status_message.emit(f"Saved → {out}")
        except Exception as e:
            QMessageBox.critical(self,"Conversion failed",str(e))

    def _from_docx(self):
        src, _ = QFileDialog.getOpenFileName(self,"Select DOCX","","Word (*.docx *.odt *.rtf)")
        if not src: return
        out, _ = QFileDialog.getSaveFileName(self,"Save PDF","document.pdf","PDF (*.pdf)")
        if not out: return
        from engine.pdf_engine import PdfEngine
        try:
            PdfEngine.docx_to_pdf(src, out)
            result = open(out,"rb").read()
            self.result_ready.emit(result, f"Converted {os.path.basename(src)} → PDF")
        except Exception as e:
            QMessageBox.critical(self,"Conversion failed",str(e))


# ─────────────────────────────────────────────────────────────────────────────
# DIFF PANEL
# ─────────────────────────────────────────────────────────────────────────────

class DiffPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, engine_ref, parent=None):
        super().__init__(parent)
        self._eng = engine_ref
        self._file_a: bytes = b""
        self._file_b: bytes = b""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8,8,8,8); layout.setSpacing(8)

        fg = _section("Select Files")
        fl = QVBoxLayout(fg)
        row_a = QHBoxLayout()
        self._lbl_a = _label("File A: (not selected)", muted=True)
        b_a = _btn("Browse…"); b_a.clicked.connect(lambda: self._pick(True))
        row_a.addWidget(self._lbl_a); row_a.addWidget(b_a)
        row_b = QHBoxLayout()
        self._lbl_b = _label("File B: (not selected)", muted=True)
        b_b = _btn("Browse…"); b_b.clicked.connect(lambda: self._pick(False))
        row_b.addWidget(self._lbl_b); row_b.addWidget(b_b)
        fl.addLayout(row_a); fl.addLayout(row_b)
        layout.addWidget(fg)

        rg = _section("Run")
        rl = QVBoxLayout(rg)
        b_text  = QPushButton("Text Diff");      b_text.clicked.connect(self._run_text)
        b_vis   = QPushButton("Visual Diff");    b_vis.clicked.connect(self._run_visual)
        rl.addWidget(b_text); rl.addWidget(b_vis)
        layout.addWidget(rg)

        self._out = QTextEdit()
        self._out.setReadOnly(True)
        self._out.setPlaceholderText("Diff results appear here…")
        layout.addWidget(self._out)
        layout.addStretch()

    def _pick(self, is_a: bool):
        f, _ = QFileDialog.getOpenFileName(self,"Select PDF","","PDF (*.pdf)")
        if not f: return
        data = open(f,"rb").read()
        if is_a:
            self._file_a = data
            self._lbl_a.setText(f"File A: {os.path.basename(f)}")
        else:
            self._file_b = data
            self._lbl_b.setText(f"File B: {os.path.basename(f)}")

    def _run_text(self):
        if not self._file_a or not self._file_b:
            QMessageBox.information(self,"Diff","Select both files first."); return
        from engine.pdf_engine import PdfEngine
        try:
            r = PdfEngine.diff_text(self._file_a, self._file_b)
            out = (f"Similarity: {r['similarity']}%\n"
                   f"Pages A: {r['pages_a']}  Pages B: {r['pages_b']}\n"
                   f"Pages with changes: {r['changed']}\n\n")
            for d in r["diffs"]:
                if d["has_changes"]:
                    out += f"── Page {d['page']+1}  (+{d['adds']} / -{d['dels']}) ──\n"
                    out += "".join(d["lines"][:30])
                    out += "\n"
            self._out.setPlainText(out)
        except Exception as e:
            QMessageBox.critical(self,"Diff failed",str(e))

    def _run_visual(self):
        if not self._file_a or not self._file_b:
            QMessageBox.information(self,"Diff","Select both files first."); return
        from engine.pdf_engine import PdfEngine
        from PyQt6.QtGui import QImage, QPixmap
        from PyQt6.QtWidgets import QDialog, QLabel, QHBoxLayout
        try:
            r = PdfEngine.diff_visual(self._file_a, self._file_b, page=0, dpi=80)
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Visual Diff — {r['change_pct']}% changed")
            dlg.resize(900, 400)
            h = QHBoxLayout(dlg)
            for key, title in [("img_a","File A"),("img_b","File B"),("heatmap","Heatmap")]:
                col = QVBoxLayout()
                lbl_title = QLabel(title)
                lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_lbl = QLabel()
                pm = QPixmap.fromImage(QImage.fromData(r[key]))
                img_lbl.setPixmap(pm.scaledToHeight(320, Qt.TransformationMode.SmoothTransformation))
                col.addWidget(lbl_title); col.addWidget(img_lbl)
                h.addLayout(col)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self,"Diff failed",str(e))
