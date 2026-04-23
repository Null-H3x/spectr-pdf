"""
Spectr PDF — CAC Signing Panel & Dialogs
Handles DoD Common Access Card signing, verification,
and deletion of the authenticated user's own signatures.
"""

from __future__ import annotations
import os
from PyQt6.QtCore    import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGroupBox, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QFormLayout, QMessageBox,
    QFileDialog, QCheckBox, QProgressBar, QTextEdit,
)
from engine.cac_engine import (CacEngine, CacCertificate, find_middleware,
                               PYKCS11_AVAILABLE, PYKCS11_INSTALL_GUIDE)


# ── PIN dialog ─────────────────────────────────────────────────────────────────

class PinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CAC PIN Required")
        self.setFixedSize(320, 140)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter your CAC PIN:"))
        self._pin = QLineEdit()
        self._pin.setEchoMode(QLineEdit.EchoMode.Password)
        self._pin.setPlaceholderText("6–8 digit PIN")
        layout.addWidget(self._pin)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def pin(self) -> str:
        return self._pin.text()


# ── Middleware path dialog ─────────────────────────────────────────────────────

class MiddlewareDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select CAC Middleware")
        self.setFixedSize(480, 180)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Spectr PDF could not auto-detect your CAC middleware.\n"
            "Specify the path to your PKCS#11 .dll file:"))
        row = QHBoxLayout()
        self._path = QLineEdit()
        self._path.setPlaceholderText(r"C:\Windows\System32\acpkcs211.dll")
        b_browse = QPushButton("Browse…")
        b_browse.clicked.connect(self._browse)
        row.addWidget(self._path); row.addWidget(b_browse)
        layout.addLayout(row)
        layout.addWidget(QLabel(
            "Common locations:\n"
            "  ActivClient:  C:\\Windows\\System32\\acpkcs211.dll\n"
            "  OpenSC:       C:\\Windows\\System32\\opensc-pkcs11.dll",
        ))
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select PKCS#11 DLL", r"C:\Windows\System32",
            "DLL files (*.dll);;All files (*)")
        if f:
            self._path.setText(f)

    def path(self) -> str:
        return self._path.text().strip()


# ── Background sign worker ─────────────────────────────────────────────────────

class SignWorker(QThread):
    done  = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, engine: CacEngine, pdf: bytes, cert: CacCertificate,
                 field: str, reason: str, location: str, name: str, page: int):
        super().__init__()
        self._engine = engine
        self._pdf = pdf; self._cert = cert; self._field = field
        self._reason = reason; self._location = location
        self._name = name; self._page = page

    def run(self):
        try:
            result = self._engine.sign_pdf(
                self._pdf, self._cert,
                field_name=self._field,
                reason=self._reason,
                location=self._location,
                signer_name=self._name,
                page=self._page,
            )
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ── Main CAC signing panel ─────────────────────────────────────────────────────

class CacSignPanel(QWidget):
    result_ready   = pyqtSignal(bytes, str)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine  = CacEngine()
        self._doc     = None
        self._certs:  list[CacCertificate] = []
        self._worker: SignWorker | None    = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Show install guide if PyKCS11 not available ───────────────────────
        if not PYKCS11_AVAILABLE:
            banner = QWidget()
            banner.setStyleSheet("""
                QWidget { background-color: #1A1400;
                          border: 1px solid #FFB800;
                          border-radius: 8px; }
            """)
            bl = QVBoxLayout(banner)
            bl.setContentsMargins(14, 12, 14, 12)
            bl.setSpacing(8)
            title = QLabel("⚠  CAC Signing Unavailable")
            title.setStyleSheet("color: #FFB800; font-weight: 600; font-size: 13px; background: transparent; border: none;")
            body = QLabel(PYKCS11_INSTALL_GUIDE)
            body.setStyleSheet("color: #8899AA; font-size: 11px; background: transparent; border: none;")
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            bl.addWidget(title)
            bl.addWidget(body)
            layout.addWidget(banner)
            layout.addStretch()
            return

        # ── Card connection ───────────────────────────────────────────────────
        cg = QGroupBox("Smart Card")
        cl = QVBoxLayout(cg)

        self._status_lbl = QLabel("No card connected")
        self._status_lbl.setProperty("muted", "true")

        row = QHBoxLayout()
        self._mw_lbl  = QLabel("Auto-detect middleware")
        self._mw_lbl.setProperty("muted", "true")
        b_load = QPushButton("Connect Card")
        b_load.clicked.connect(self._connect_card)
        row.addWidget(self._mw_lbl); row.addStretch(); row.addWidget(b_load)

        self._slot_combo = QComboBox()
        self._slot_combo.setEnabled(False)

        cl.addWidget(self._status_lbl)
        cl.addLayout(row)
        cl.addWidget(QLabel("Slot:"))
        cl.addWidget(self._slot_combo)
        layout.addWidget(cg)

        # ── Certificate selection ─────────────────────────────────────────────
        certs_g = QGroupBox("Signing Certificate")
        certs_l = QVBoxLayout(certs_g)
        self._cert_list = QListWidget()
        self._cert_list.setFixedHeight(100)
        self._cert_list.itemClicked.connect(self._on_cert_selected)
        self._cert_detail = QLabel("Select a certificate above")
        self._cert_detail.setProperty("muted", "true")
        self._cert_detail.setWordWrap(True)
        certs_l.addWidget(self._cert_list)
        certs_l.addWidget(self._cert_detail)
        layout.addWidget(certs_g)

        # ── Sign options ──────────────────────────────────────────────────────
        sig_g = QGroupBox("Sign PDF")
        sig_l = QFormLayout(sig_g)
        self._reason   = QLineEdit("I approve this document")
        self._location = QLineEdit()
        self._location.setPlaceholderText("e.g. Fort Meade, MD")
        self._field    = QLineEdit()
        self._field.setPlaceholderText("Leave blank to auto-place")
        sig_l.addRow("Reason:", self._reason)
        sig_l.addRow("Location:", self._location)
        sig_l.addRow("Field name:", self._field)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)

        b_sign = QPushButton("Sign PDF with CAC")
        b_sign.clicked.connect(self._sign)

        sig_body = QVBoxLayout()
        sig_body.addWidget(sig_g)
        sig_body.addWidget(self._progress)
        sig_body.addWidget(b_sign)
        layout.addLayout(sig_body)

        # ── Verify ────────────────────────────────────────────────────────────
        vg = QGroupBox("Verify Signatures")
        vl = QVBoxLayout(vg)
        vl.addWidget(QLabel("Check all signatures in the open document:"))
        b_verify = QPushButton("Verify All Signatures")
        b_verify.clicked.connect(self._verify)
        vl.addWidget(b_verify)
        layout.addWidget(vg)

        # ── Delete MY signature ───────────────────────────────────────────────
        dg = QGroupBox("Delete My Signature")
        dl = QVBoxLayout(dg)
        dl.addWidget(QLabel(
            "Remove only the signature(s) belonging to\n"
            "the authenticated CAC card holder.\n"
            "Requires an active card session and PIN.",
        ))
        b_del = QPushButton("Delete My Signature(s)")
        b_del.setProperty("danger", "true")
        b_del.clicked.connect(self._delete_mine)
        dl.addWidget(b_del)
        layout.addWidget(dg)

        layout.addStretch()

    def set_document(self, doc): self._doc = doc

    # ── Connection ─────────────────────────────────────────────────────────────

    def _connect_card(self):
        mw_path = find_middleware()
        if not mw_path:
            dlg = MiddlewareDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted: return
            mw_path = dlg.path()
            if not mw_path: return

        try:
            self._engine.load_middleware(mw_path)
        except Exception as e:
            QMessageBox.critical(self, "Middleware Error", str(e)); return

        self._mw_lbl.setText(os.path.basename(mw_path))

        try:
            slots = self._engine.list_slots()
        except Exception as e:
            QMessageBox.critical(self, "Card Error", str(e)); return

        if not slots:
            QMessageBox.information(self, "No Card",
                "No smart card detected. Insert your CAC and try again.")
            return

        self._slot_combo.clear()
        for s in slots:
            self._slot_combo.addItem(f"Slot {s.index}: {s.token_label}")
        self._slot_combo.setEnabled(True)

        # Auto-open first slot
        self._engine.open_session(0)

        # Ask for PIN
        pin_dlg = PinDialog(self)
        if pin_dlg.exec() != QDialog.DialogCode.Accepted: return
        pin = pin_dlg.pin()
        if not pin: return

        try:
            self._engine.login(pin)
        except Exception as e:
            QMessageBox.critical(self, "PIN Error",
                f"Login failed: {e}\n\nCheck your PIN and try again.")
            return

        # Load certificates
        try:
            certs = self._engine.list_certs()
        except Exception as e:
            QMessageBox.critical(self, "Certificate Error", str(e)); return

        self._certs = [c for c in certs if c.is_signing]
        self._cert_list.clear()
        for c in self._certs:
            item = QListWidgetItem(f"{c.label}  —  expires {c.not_after[:10]}")
            self._cert_list.addItem(item)

        if not self._certs:
            QMessageBox.warning(self, "No Signing Certs",
                "No signing certificates found on this card.")
        else:
            n = len(self._certs)
            self._status_lbl.setText(f"Connected — {n} signing cert(s) available")
            self.status_message.emit(f"CAC connected: {n} signing certificate(s) loaded")

    def _on_cert_selected(self, item: QListWidgetItem):
        idx  = self._cert_list.row(item)
        cert = self._certs[idx]
        self._cert_detail.setText(
            f"Subject:  {cert.subject}\n"
            f"Issuer:   {cert.issuer[:60]}\n"
            f"Valid:    {cert.not_before[:10]}  →  {cert.not_after[:10]}\n"
            f"Usage:    {', '.join(cert.key_usage)}"
        )

    # ── Sign ───────────────────────────────────────────────────────────────────

    def _sign(self):
        if not self._doc:
            QMessageBox.information(self,"Sign","Open a PDF first."); return
        if not self._engine.is_loaded():
            QMessageBox.information(self,"Sign","Connect your CAC card first."); return

        sel = self._cert_list.currentRow()
        if sel < 0 or sel >= len(self._certs):
            QMessageBox.information(self,"Sign","Select a certificate first."); return

        cert = self._certs[sel]
        self._progress.setVisible(True)
        self._worker = SignWorker(
            self._engine, self._doc.bytes_data, cert,
            field=self._field.text().strip(),
            reason=self._reason.text(),
            location=self._location.text(),
            name=cert.subject.split("CN=")[-1].split(",")[0] if "CN=" in cert.subject else cert.label,
            page=0,
        )
        self._worker.done.connect(self._on_signed)
        self._worker.error.connect(self._on_sign_error)
        self._worker.start()

    def _on_signed(self, result: bytes):
        self._progress.setVisible(False)
        self.result_ready.emit(result, "PDF signed with CAC")

    def _on_sign_error(self, msg: str):
        self._progress.setVisible(False)
        QMessageBox.critical(self, "Signing Failed", msg)

    # ── Verify ─────────────────────────────────────────────────────────────────

    def _verify(self):
        if not self._doc:
            QMessageBox.information(self,"Verify","Open a PDF first."); return
        try:
            sigs = CacEngine.verify_signatures(self._doc.bytes_data)
        except Exception as e:
            QMessageBox.critical(self,"Verify Error",str(e)); return

        if not sigs:
            QMessageBox.information(self,"Verify","No digital signatures found in this document.")
            return

        lines = []
        for s in sigs:
            status = "✓ VALID" if s.get("valid") and s.get("intact") else "✗ INVALID"
            lines.append(
                f"{status}  —  {s['field']}\n"
                f"  Signer:   {s.get('signer','unknown')[:70]}\n"
                f"  Time:     {s.get('signing_time','')}\n"
                f"  Coverage: {s.get('coverage','')}\n"
                + (f"  Error:    {s['error']}\n" if "error" in s else "")
            )
        QMessageBox.information(self, f"Signatures ({len(sigs)} found)",
                                "\n".join(lines))

    # ── Delete mine ────────────────────────────────────────────────────────────

    def _delete_mine(self):
        if not self._doc:
            QMessageBox.information(self,"Delete","Open a PDF first."); return
        if not self._engine.is_loaded():
            QMessageBox.information(self,"Delete","Connect your CAC card first."); return
        if not self._certs:
            QMessageBox.information(self,"Delete","No certificates loaded from card."); return

        reply = QMessageBox.question(
            self, "Delete My Signature",
            "This will remove signature(s) belonging to the authenticated\n"
            "CAC card holder. Other signatures are not affected.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes: return

        try:
            new_bytes, removed = self._engine.delete_my_signature(
                self._doc.bytes_data, self._certs[0])
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e)); return

        if not removed:
            QMessageBox.information(self,"Delete",
                "No signatures belonging to this card were found in the document.")
            return

        self.result_ready.emit(
            new_bytes,
            f"Removed signature(s): {', '.join(removed)}")
        QMessageBox.information(self,"Done",
            f"Removed {len(removed)} signature(s): {', '.join(removed)}")
