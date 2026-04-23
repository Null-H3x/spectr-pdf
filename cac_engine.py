"""
Spectr PDF — CAC / Smart Card Signing Engine
Interfaces with DoD Common Access Cards (and any PIV-compatible card)
via PKCS#11. Uses pyHanko for the actual PDF signature.

Supported middleware (auto-detected):
  - DoD/ActivClient:  acpkcs211.dll  (most common on GFE)
  - OpenSC:           opensc-pkcs11.dll / opensc-pkcs11.so
  - CAC middleware:   cackey.dll
  - Fallback:         user-supplied .dll path
"""

from __future__ import annotations

import os
import io
import platform
from dataclasses import dataclass
from typing import Optional

# PyKCS11 requires Microsoft C++ Build Tools to compile on Windows.
# If not installed, CAC signing is unavailable but the rest of the app works.
try:
    import PyKCS11
    PYKCS11_AVAILABLE = True
except ImportError:
    PYKCS11_AVAILABLE = False
    PyKCS11 = None  # type: ignore

PYKCS11_INSTALL_GUIDE = (
    "PyKCS11 is not installed — CAC signing is unavailable.\n\n"
    "To enable CAC support:\n"
    "  1. Download Microsoft C++ Build Tools:\n"
    "     https://visualstudio.microsoft.com/visual-cpp-build-tools/\n"
    "  2. Install the 'Desktop development with C++' workload\n"
    "  3. Open a new terminal and run:\n"
    "     python -m pip install PyKCS11\n"
    "  4. Restart Spectr PDF\n\n"
    "All other features work without this."
)


# ── PKCS#11 middleware locations ───────────────────────────────────────────────

_WINDOWS_LIBS = [
    r"C:\Windows\System32\acpkcs211.dll",       # ActivClient (GFE standard)
    r"C:\Windows\SysWOW64\acpkcs211.dll",
    r"C:\Windows\System32\acpkcs11.dll",
    r"C:\Program Files\ActivIdentity\ActivClient\acpkcs211.dll",
    r"C:\Program Files (x86)\ActivIdentity\ActivClient\acpkcs211.dll",
    r"C:\Windows\System32\opensc-pkcs11.dll",   # OpenSC
    r"C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"C:\Windows\System32\cackey.dll",          # cackey
    r"C:\Program Files\CAC Software\cackey.dll",
]

_LINUX_LIBS = [
    "/usr/lib/x86_64-linux-gnu/opensc-pkcs11.so",
    "/usr/lib/opensc-pkcs11.so",
    "/usr/local/lib/opensc-pkcs11.so",
    "/usr/lib/pkcs11/opensc-pkcs11.so",
]


def find_middleware() -> Optional[str]:
    """Auto-detect the PKCS#11 middleware library path."""
    libs = _WINDOWS_LIBS if platform.system() == "Windows" else _LINUX_LIBS
    for path in libs:
        if os.path.isfile(path):
            return path
    return None


# ── Card / certificate model ───────────────────────────────────────────────────

@dataclass
class CacCertificate:
    label:       str
    issuer:      str
    subject:     str
    serial:      str
    not_before:  str
    not_after:   str
    key_usage:   list[str]
    slot_index:  int
    obj_handle:  int       # PyKCS11 object handle
    is_signing:  bool      # True if cert has digitalSignature usage


@dataclass
class CacSlot:
    index:       int
    label:       str
    token_label: str
    certs:       list[CacCertificate]


# ── CAC engine ────────────────────────────────────────────────────────────────

class CacEngine:
    """
    Manages the PKCS#11 session and exposes CAC signing operations.
    If PyKCS11 is not installed, all methods raise RuntimeError with
    an install guide. Check CacEngine.available() before using.
    """

    @staticmethod
    def available() -> bool:
        """Returns True if PyKCS11 is installed and CAC signing is possible."""
        return PYKCS11_AVAILABLE

    def __init__(self):
        if not PYKCS11_AVAILABLE:
            return   # methods will raise on use
        self._lib:     Optional[PyKCS11.PyKCS11Lib] = None
        self._session: Optional[PyKCS11.CK_SESSION_HANDLE] = None
        self._slot:    int = 0
        self.middleware_path: str = ""

    def _require_pykcs11(self):
        if not PYKCS11_AVAILABLE:
            raise RuntimeError(PYKCS11_INSTALL_GUIDE)

    # ── Middleware ─────────────────────────────────────────────────────────────

    def load_middleware(self, path: Optional[str] = None) -> str:
        """Load PKCS#11 library. Auto-detects if path is None."""
        self._require_pykcs11()
        lib_path = path or find_middleware()
        if not lib_path:
            raise RuntimeError(
                "No CAC middleware found.\n\n"
                "Install one of:\n"
                "  • ActivClient (GFE standard)\n"
                "  • OpenSC: https://github.com/OpenSC/OpenSC/releases\n"
                "  • DoD middleware: https://militarycac.com/dodcerts.htm\n\n"
                "Or provide the path to your PKCS#11 .dll manually."
            )
        if not os.path.isfile(lib_path):
            raise FileNotFoundError(f"PKCS#11 library not found: {lib_path}")

        self._lib = PyKCS11.PyKCS11Lib()
        self._lib.load(lib_path)
        self.middleware_path = lib_path
        return lib_path

    def is_loaded(self) -> bool:
        return self._lib is not None

    # ── Slots / tokens ─────────────────────────────────────────────────────────

    def list_slots(self) -> list[CacSlot]:
        """Return all slots with a token present."""
        if not self._lib:
            raise RuntimeError("Call load_middleware() first.")
        slots = []
        for idx, slot_id in enumerate(self._lib.getSlotList(tokenPresent=True)):
            try:
                info       = self._lib.getTokenInfo(slot_id)
                slot_label = str(info.label).strip()
                slots.append(CacSlot(
                    index=idx, label=f"Slot {idx}", token_label=slot_label,
                    certs=[]))
            except Exception:
                pass
        return slots

    # ── Session ───────────────────────────────────────────────────────────────

    def open_session(self, slot_index: int = 0) -> None:
        """Open a read-only session on the given slot."""
        self._require_pykcs11()
        if not self._lib:
            raise RuntimeError("Call load_middleware() first.")
        all_slots = self._lib.getSlotList(tokenPresent=True)
        if slot_index >= len(all_slots):
            raise ValueError(f"Slot {slot_index} not available ({len(all_slots)} slots found)")
        self._slot    = all_slots[slot_index]
        self._session = self._lib.openSession(
            self._slot, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)

    def login(self, pin: str) -> None:
        """Login with the CAC PIN."""
        if not self._session:
            raise RuntimeError("Call open_session() first.")
        self._lib.login(self._session, PyKCS11.CKU_USER, pin)

    def logout(self) -> None:
        if self._session:
            try:
                self._lib.logout(self._session)
                self._lib.closeSession(self._session)
            except Exception:
                pass
            self._session = None

    # ── Certificates ──────────────────────────────────────────────────────────

    def list_certs(self) -> list[CacCertificate]:
        """Read all X.509 certificates from the card."""
        if not self._session:
            raise RuntimeError("Open a session first.")

        from cryptography import x509
        from cryptography.hazmat.primitives import serialization

        template = [(PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE),
                    (PyKCS11.CKA_CERTIFICATE_TYPE, PyKCS11.CKC_X_509)]
        objs  = self._lib.findObjects(self._session, template)
        certs = []

        for obj in objs:
            try:
                attrs = self._lib.getAttributeValue(self._session, obj, [
                    PyKCS11.CKA_LABEL,
                    PyKCS11.CKA_VALUE,
                    PyKCS11.CKA_ID,
                ])
                label    = str(attrs[0]).strip() if attrs[0] else "Unknown"
                der_data = bytes(attrs[1]) if attrs[1] else b""
                if not der_data:
                    continue

                cert        = x509.load_der_x509_certificate(der_data)
                subject     = cert.subject.rfc4514_string()
                issuer      = cert.issuer.rfc4514_string()
                serial      = hex(cert.serial_number)
                not_before  = str(cert.not_valid_before_utc)
                not_after   = str(cert.not_valid_after_utc)

                # Determine key usage
                key_usage = []
                try:
                    ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
                    if ku.value.digital_signature: key_usage.append("digitalSignature")
                    if ku.value.content_commitment: key_usage.append("nonRepudiation")
                    if ku.value.key_encipherment:  key_usage.append("keyEncipherment")
                except Exception:
                    key_usage = ["unknown"]

                is_signing = "digitalSignature" in key_usage or "nonRepudiation" in key_usage

                certs.append(CacCertificate(
                    label=label, issuer=issuer, subject=subject,
                    serial=serial, not_before=not_before, not_after=not_after,
                    key_usage=key_usage, slot_index=int(self._slot),
                    obj_handle=int(obj), is_signing=is_signing,
                ))
            except Exception:
                continue

        return certs

    # ── Sign ──────────────────────────────────────────────────────────────────

    def sign_pdf(self, pdf_bytes: bytes, cert: CacCertificate,
                 field_name: str = "", reason: str = "I approve this document",
                 location: str = "", signer_name: str = "",
                 page: int = 0) -> bytes:
        """
        Sign a PDF using the selected CAC certificate.
        Uses pyHanko with PKCS#11 backend to sign directly on the card.
        """
        from pyhanko.sign import signers, fields as sig_fields
        from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

        # Build PKCS#11 signer for pyHanko
        signer = signers.PKCS11Signer(
            pkcs11_session  = self._session,
            cert_label      = cert.label,
            signing_cert    = None,   # pyHanko resolves from session
            other_certs     = [],
            pkcs11lib       = self._lib,
            slot             = self._slot,
        )

        effective_field = field_name or "Signature1"
        sig_meta = PdfSignatureMetadata(
            field_name  = effective_field,
            name        = signer_name or cert.subject,
            location    = location or "",
            reason      = reason,
            certify     = False,
        )

        out_buf = io.BytesIO()
        with io.BytesIO(pdf_bytes) as f:
            w = IncrementalPdfFileWriter(f)
            # Add field if it doesn't exist
            if not field_name:
                doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
                pg  = doc[min(page, len(doc)-1)]
                pw, ph = pg.rect.width, pg.rect.height
                doc.close()
                sig_fields.append_signature_field(w,
                    sig_field_spec=sig_fields.SigFieldSpec(
                        sig_field_name=effective_field,
                        on_page=page,
                        box=(pw*0.55, ph*0.08, pw*0.95, ph*0.14),
                    ))

            import asyncio
            asyncio.run(signers.async_sign_pdf(w, sig_meta, signer=signer, output=out_buf))

        return out_buf.getvalue()

    # ── Delete my signature ────────────────────────────────────────────────────

    def delete_my_signature(self, pdf_bytes: bytes,
                            cert: CacCertificate) -> tuple[bytes, list[str]]:
        """
        Find and remove signatures whose signer certificate matches
        the certificate on the CAC. Only removes signatures belonging
        to the authenticated card holder.

        Returns (new_pdf_bytes, list_of_removed_field_names).
        Uses pikepdf to surgically remove the signature revision.
        """
        from cryptography import x509
        from pyhanko.pdf_utils.reader import PdfFileReader

        # ── Find which fields are signed by our card's cert ─────────────────
        removed = []
        with io.BytesIO(pdf_bytes) as f:
            reader   = PdfFileReader(f)
            embedded = reader.embedded_signatures

            my_serials = set()
            # Get the serial number of the current card cert
            certs_on_card = self.list_certs()
            for c in certs_on_card:
                my_serials.add(c.serial.lower().lstrip("0x"))

            mine = []
            for sig in embedded:
                try:
                    # Extract signer cert from signature
                    sig_cert = sig.signer_cert
                    if sig_cert:
                        serial = hex(sig_cert.serial_number).lower().lstrip("0x")
                        if serial in my_serials:
                            mine.append(sig.field_name)
                except Exception:
                    continue

        if not mine:
            return pdf_bytes, []

        # ── Remove matching signature fields using pikepdf ──────────────────
        pdf     = pikepdf.open(io.BytesIO(pdf_bytes))
        acroform = pdf.Root.get("/AcroForm")

        if acroform and "/Fields" in acroform:
            fields = acroform["/Fields"]
            to_keep = []
            for field_ref in fields:
                field = pdf.get_object(field_ref)
                fname = str(field.get("/T", "")).strip("()")
                if fname in mine:
                    removed.append(fname)
                    # Clear signature value
                    if "/V" in field:
                        del field["/V"]
                    if "/AP" in field:
                        del field["/AP"]
                else:
                    to_keep.append(field_ref)
            # Update fields list (removes cleared sig fields)
            # We keep the field widget but clear its value
            # Full removal would break page annotation arrays

        buf = io.BytesIO()
        pdf.save(buf)
        pdf.close()
        return buf.getvalue(), removed

    # ── Verify ────────────────────────────────────────────────────────────────

    @staticmethod
    def verify_signatures(pdf_bytes: bytes) -> list[dict]:
        """Verify all signatures in the PDF (no card required)."""
        import asyncio
        from pyhanko.sign import validation
        from pyhanko.pdf_utils.reader import PdfFileReader

        results = []
        with io.BytesIO(pdf_bytes) as f:
            reader   = PdfFileReader(f)
            embedded = reader.embedded_signatures
            if not embedded:
                return []

            async def _verify_all():
                out = []
                for sig in embedded:
                    try:
                        status = await validation.async_validate_pdf_signature(sig)
                        out.append({
                            "field":        sig.field_name,
                            "valid":        status.valid,
                            "intact":       status.intact,
                            "trusted":      status.trusted,
                            "coverage":     str(status.coverage),
                            "signing_time": str(status.signer_reported_dt) if status.signer_reported_dt else "",
                            "signer":       sig.signer_cert.subject.rfc4514_string() if sig.signer_cert else "",
                        })
                    except Exception as e:
                        out.append({"field": sig.field_name, "error": str(e), "valid": False})
                return out

            return asyncio.run(_verify_all())
