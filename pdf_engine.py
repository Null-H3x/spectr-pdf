"""
Spectr PDF — PDF Engine
Direct PyMuPDF/pikepdf/pyHanko calls. No HTTP, no server.
This module is the single source of truth for all PDF operations
in the Windows desktop app.
"""

from __future__ import annotations

import io
import os
import json
import shutil
import subprocess
import tempfile
import difflib
import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import pymupdf
import pikepdf
from PIL import Image


# ── Document model ─────────────────────────────────────────────────────────────

@dataclass
class PageInfo:
    index:    int
    width:    float
    height:   float
    rotation: int
    label:    str

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 1.0


@dataclass
class PdfDoc:
    path:       str
    bytes_data: bytes
    page_count: int
    metadata:   dict
    pages:      list[PageInfo]
    is_modified: bool = False

    @property
    def filename(self) -> str:
        return Path(self.path).name if self.path else "Untitled.pdf"

    @property
    def title(self) -> str:
        return self.metadata.get("title") or self.filename


# ── Engine ─────────────────────────────────────────────────────────────────────

class PdfEngine:
    """
    All PDF operations. Call open_file() to load a document,
    then call operation methods that return new bytes.
    The caller decides whether to replace the current document.
    """

    # ── Open / load ────────────────────────────────────────────────────────────

    @staticmethod
    def open_file(path: str) -> PdfDoc:
        with open(path, "rb") as f:
            data = f.read()
        return PdfEngine.open_bytes(data, path)

    @staticmethod
    def open_bytes(data: bytes, path: str = "") -> PdfDoc:
        doc  = pymupdf.open(stream=data, filetype="pdf")
        meta = doc.metadata or {}
        pages = [
            PageInfo(
                index=i,
                width=round(p.rect.width, 2),
                height=round(p.rect.height, 2),
                rotation=p.rotation,
                label=str(i + 1),
            )
            for i, p in enumerate(doc)
        ]
        result = PdfDoc(
            path=path,
            bytes_data=data,
            page_count=len(doc),
            metadata={
                "title":    meta.get("title", ""),
                "author":   meta.get("author", ""),
                "subject":  meta.get("subject", ""),
                "creator":  meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "created":  meta.get("creationDate", ""),
                "modified": meta.get("modDate", ""),
            },
            pages=pages,
        )
        doc.close()
        return result

    # ── Render ────────────────────────────────────────────────────────────────

    @staticmethod
    def render_page(data: bytes, page_index: int, dpi: float = 150) -> bytes:
        """Render a page as PNG bytes (for display in Qt)."""
        doc = pymupdf.open(stream=data, filetype="pdf")
        page = doc[page_index]
        mat = pymupdf.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png = pix.tobytes("png")
        doc.close()
        return png

    @staticmethod
    def render_thumbnail(data: bytes, page_index: int, max_height: int = 160) -> bytes:
        """Render a small thumbnail PNG."""
        doc = pymupdf.open(stream=data, filetype="pdf")
        page = doc[page_index]
        scale = max_height / page.rect.height
        mat = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png = pix.tobytes("png")
        doc.close()
        return png

    # ── Page operations ────────────────────────────────────────────────────────

    @staticmethod
    def merge(files: list[bytes]) -> bytes:
        out = pymupdf.open()
        for data in files:
            doc = pymupdf.open(stream=data, filetype="pdf")
            out.insert_pdf(doc)
            doc.close()
        return PdfEngine._save(out)

    @staticmethod
    def split(data: bytes, ranges: list[tuple[int, int]]) -> list[bytes]:
        """Split into multiple PDFs. ranges are (start, end) 0-indexed inclusive."""
        doc    = pymupdf.open(stream=data, filetype="pdf")
        result = []
        for start, end in ranges:
            out = pymupdf.open()
            out.insert_pdf(doc, from_page=start, to_page=end)
            result.append(PdfEngine._save(out))
        doc.close()
        return result

    @staticmethod
    def delete_pages(data: bytes, pages: list[int]) -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        doc.delete_pages(sorted(set(pages), reverse=True))
        return PdfEngine._save(doc)

    @staticmethod
    def reorder(data: bytes, new_order: list[int]) -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        doc.select(new_order)
        return PdfEngine._save(doc)

    @staticmethod
    def rotate(data: bytes, pages: list[int], degrees: int) -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        targets = pages or list(range(len(doc)))
        for i in targets:
            doc[i].set_rotation((doc[i].rotation + degrees) % 360)
        return PdfEngine._save(doc)

    # ── Annotations ───────────────────────────────────────────────────────────

    @staticmethod
    def list_annotations(data: bytes) -> list[dict]:
        doc    = pymupdf.open(stream=data, filetype="pdf")
        result = []
        for pg_num, page in enumerate(doc):
            for ann in page.annots():
                info = ann.info
                result.append({
                    "page":     pg_num,
                    "type":     ann.type[1],
                    "type_code":ann.type[0],
                    "rect":     list(ann.rect),
                    "content":  info.get("content", ""),
                    "author":   info.get("title", ""),
                    "xref":     ann.xref,
                    "color":    ann.colors.get("stroke"),
                })
        doc.close()
        return result

    @staticmethod
    def add_highlight(data: bytes, page: int, quads: list,
                      color: tuple = (1, 1, 0), annot_type: str = "highlight",
                      content: str = "", author: str = "") -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        pg  = doc[page]
        q_objs = [pymupdf.Quad(q) for q in quads]
        fn_map = {
            "highlight":  pg.add_highlight_annot,
            "underline":  pg.add_underline_annot,
            "strikeout":  pg.add_strikeout_annot,
            "squiggly":   pg.add_squiggly_annot,
        }
        ann = fn_map.get(annot_type, pg.add_highlight_annot)(q_objs)
        ann.set_colors(stroke=color)
        ann.set_info(content=content, title=author)
        ann.update()
        return PdfEngine._save(doc)

    @staticmethod
    def add_sticky_note(data: bytes, page: int, x: float, y: float,
                        content: str, author: str = "",
                        color: tuple = (1, 0.85, 0)) -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        pg  = doc[page]
        ann = pg.add_text_annot(pymupdf.Point(x, y), content, icon="Note")
        ann.set_colors(stroke=color)
        ann.set_info(title=author, content=content)
        ann.update()
        return PdfEngine._save(doc)

    @staticmethod
    def add_freetext(data: bytes, page: int, rect: list, content: str,
                     fontsize: float = 12, color: tuple = (0, 0, 0),
                     bg: tuple = (1, 1, 1), author: str = "") -> bytes:
        doc  = pymupdf.open(stream=data, filetype="pdf")
        pg   = doc[page]
        ann  = pg.add_freetext_annot(
            pymupdf.Rect(rect), content,
            fontsize=fontsize, text_color=color, fill_color=bg,
            align=pymupdf.TEXT_ALIGN_LEFT,
        )
        ann.set_info(title=author, content=content)
        ann.update()
        return PdfEngine._save(doc)

    @staticmethod
    def delete_annotation(data: bytes, page: int, xref: int) -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        pg  = doc[page]
        for ann in pg.annots():
            if ann.xref == xref:
                pg.delete_annot(ann)
                break
        return PdfEngine._save(doc)

    @staticmethod
    def flatten_annotations(data: bytes) -> bytes:
        src = pymupdf.open(stream=data, filetype="pdf")
        out = pymupdf.open()
        for page in src:
            pix  = page.get_pixmap(dpi=150, annots=True)
            np   = out.new_page(width=page.rect.width, height=page.rect.height)
            np.insert_image(np.rect, pixmap=pix)
        src.close()
        return PdfEngine._save(out)

    # ── Forms ─────────────────────────────────────────────────────────────────

    @staticmethod
    def list_fields(data: bytes) -> list[dict]:
        doc = pymupdf.open(stream=data, filetype="pdf")
        fields = []
        for pg_num, page in enumerate(doc):
            for w in page.widgets():
                fields.append({
                    "page":       pg_num,
                    "name":       w.field_name,
                    "type":       w.field_type_string,
                    "value":      w.field_value,
                    "rect":       list(w.rect),
                    "choices":    w.choice_values or [],
                    "required":   bool(w.field_flags & 2),
                    "read_only":  bool(w.field_flags & 1),
                })
        doc.close()
        return fields

    @staticmethod
    def fill_form(data: bytes, field_data: dict[str, str],
                  flatten: bool = False) -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        for page in doc:
            for w in page.widgets():
                if w.field_name in field_data:
                    w.field_value = str(field_data[w.field_name])
                    w.update()
        if flatten:
            out = pymupdf.open()
            for page in doc:
                pix = page.get_pixmap(dpi=150, annots=True)
                np  = out.new_page(width=page.rect.width, height=page.rect.height)
                np.insert_image(np.rect, pixmap=pix)
            doc.close()
            return PdfEngine._save(out)
        return PdfEngine._save(doc)

    # ── Redact & security ──────────────────────────────────────────────────────

    @staticmethod
    def find_text(data: bytes, query: str,
                  case_sensitive: bool = False) -> list[dict]:
        doc     = pymupdf.open(stream=data, filetype="pdf")
        results = []
        for pg_num, page in enumerate(doc):
            hits = page.search_for(query)
            for rect in hits:
                results.append({
                    "page": pg_num,
                    "rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                })
        doc.close()
        return results

    @staticmethod
    def apply_redactions(data: bytes,
                         redactions: list[dict],
                         fill_color: tuple = (0, 0, 0)) -> bytes:
        doc = pymupdf.open(stream=data, filetype="pdf")
        for item in redactions:
            page = doc[item["page"]]
            page.add_redact_annot(pymupdf.Rect(item["rect"]), fill=fill_color)
        for page in doc:
            page.apply_redactions()
        return PdfEngine._save(doc)

    @staticmethod
    def redact_pattern(data: bytes, pattern: str,
                       fill_color: tuple = (0, 0, 0)) -> bytes:
        doc   = pymupdf.open(stream=data, filetype="pdf")
        count = 0
        for page in doc:
            hits = page.search_for(pattern)
            for rect in hits:
                page.add_redact_annot(rect, fill=fill_color)
                count += 1
            if hits:
                page.apply_redactions()
        return PdfEngine._save(doc)

    @staticmethod
    def encrypt(data: bytes, user_password: str, owner_password: str = "",
                allow_printing: bool = True, allow_copying: bool = False,
                allow_editing: bool = False) -> bytes:
        owner_pw = owner_password or user_password
        pdf = pikepdf.open(io.BytesIO(data))
        buf = io.BytesIO()
        pdf.save(buf, encryption=pikepdf.Encryption(
            user=user_password, owner=owner_pw, R=6,
            allow=pikepdf.Permissions(
                print_highres=allow_printing, print_lowres=allow_printing,
                extract=allow_copying, modify_form=allow_editing,
                modify_other=allow_editing,
            ),
        ))
        pdf.close()
        return buf.getvalue()

    @staticmethod
    def decrypt(data: bytes, password: str) -> bytes:
        pdf = pikepdf.open(io.BytesIO(data), password=password)
        buf = io.BytesIO()
        pdf.save(buf)
        pdf.close()
        return buf.getvalue()

    @staticmethod
    def strip_metadata(data: bytes) -> bytes:
        pdf = pikepdf.open(io.BytesIO(data))
        with pdf.open_metadata(set_pikepdf_as_editor=False) as m:
            for k in ["dc:title","dc:creator","xmp:CreatorTool",
                      "xmp:CreateDate","xmp:ModifyDate","pdf:Producer",
                      "xmpMM:DocumentID","xmpMM:InstanceID"]:
                try: del m[k]
                except KeyError: pass
        buf = io.BytesIO()
        pdf.save(buf)
        pdf.close()
        return buf.getvalue()

    # ── OCR ───────────────────────────────────────────────────────────────────

    @staticmethod
    def ocr_extract(data: bytes, lang: str = "eng",
                    dpi: int = 300) -> dict:
        import pytesseract
        doc   = pymupdf.open(stream=data, filetype="pdf")
        pages = []
        for i, page in enumerate(doc):
            mat = pymupdf.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang=lang)
            pages.append({"page": i, "text": text})
        doc.close()
        return {"pages": pages, "full_text": "\n\n".join(p["text"] for p in pages)}

    @staticmethod
    def make_searchable(data: bytes, lang: str = "eng", dpi: int = 300) -> bytes:
        import pytesseract
        src  = pymupdf.open(stream=data, filetype="pdf")
        out  = pymupdf.open()
        for pg_idx, page in enumerate(src):
            iw, ih = page.rect.width, page.rect.height
            mat    = pymupdf.Matrix(dpi / 72, dpi / 72)
            pix    = page.get_pixmap(matrix=mat, alpha=False)
            pw, ph = pix.width, pix.height
            img    = Image.frombytes("RGB", [pw, ph], pix.samples)
            data_t = pytesseract.image_to_data(img, lang=lang,
                         output_type=pytesseract.Output.DICT)
            new_pg = out.new_page(width=iw, height=ih)
            bg_mat = pymupdf.Matrix(150/72, 150/72)
            bg_pix = page.get_pixmap(matrix=bg_mat, alpha=False)
            new_pg.insert_image(new_pg.rect, pixmap=bg_pix)
            sx, sy = iw / pw, ih / ph
            for k in range(len(data_t["text"])):
                word = data_t["text"][k]
                conf = int(data_t["conf"][k])
                if not word.strip() or conf < 30:
                    continue
                x0 = data_t["left"][k] * sx
                y1 = (data_t["top"][k] + data_t["height"][k]) * sy
                fs = max(4.0, data_t["height"][k] * sy * 0.85)
                try:
                    new_pg.insert_text((x0, y1), word + " ",
                        fontsize=fs, color=(1,1,1), render_mode=3)
                except Exception:
                    pass
        src.close()
        return PdfEngine._save(out)

    # ── Convert ───────────────────────────────────────────────────────────────

    @staticmethod
    def to_images(data: bytes, dpi: int = 150,
                  fmt: str = "png", pages: list[int] = None) -> list[bytes]:
        doc      = pymupdf.open(stream=data, filetype="pdf")
        targets  = pages if pages is not None else list(range(len(doc)))
        mat      = pymupdf.Matrix(dpi / 72, dpi / 72)
        result   = []
        for i in targets:
            if 0 <= i < len(doc):
                pix = doc[i].get_pixmap(matrix=mat, alpha=False)
                result.append(pix.tobytes(fmt if fmt in ("png","jpeg") else "png"))
        doc.close()
        return result

    @staticmethod
    def images_to_pdf(image_data: list[bytes]) -> bytes:
        out = pymupdf.open()
        for img_bytes in image_data:
            img     = pymupdf.open(stream=img_bytes, filetype="image")
            img_pdf = pymupdf.open("pdf", img.convert_to_pdf())
            out.insert_pdf(img_pdf)
            img.close(); img_pdf.close()
        return PdfEngine._save(out)

    @staticmethod
    def to_docx(data: bytes, output_path: str) -> str:
        """Convert PDF → DOCX via LibreOffice. Returns output path."""
        soffice = PdfEngine._find_soffice()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            tmp_in = f.name

        # Ensure output directory exists; default to temp dir if not specified
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)

        lo_profile = os.path.join(out_dir, "_lo_profile")
        os.makedirs(lo_profile, exist_ok=True)

        try:
            subprocess.run([
                soffice,
                f"-env:UserInstallation=file:///{lo_profile.replace(os.sep, '/')}",
                "--headless", "--norestore",
                "--infilter=writer_pdf_import",
                "--convert-to", "docx:MS Word 2007 XML",
                "--outdir", out_dir, tmp_in,
            ], check=True, capture_output=True, timeout=120)
        finally:
            # Windows may lock the file briefly — retry unlink
            for _ in range(5):
                try:
                    os.unlink(tmp_in)
                    break
                except PermissionError:
                    import time; time.sleep(0.5)

        stem  = Path(tmp_in).stem
        out_p = Path(out_dir) / f"{stem}.docx"
        if out_p.exists() and str(out_p) != os.path.abspath(output_path):
            shutil.move(str(out_p), output_path)
        return output_path

    @staticmethod
    def docx_to_pdf(docx_path: str, output_path: str) -> str:
        soffice = PdfEngine._find_soffice()
        out_dir = os.path.dirname(output_path)
        lo_profile = os.path.join(out_dir, "_lo_profile")
        os.makedirs(lo_profile, exist_ok=True)
        subprocess.run([
            soffice,
            f"-env:UserInstallation=file:///{lo_profile.replace(os.sep,'/')}",
            "--headless", "--norestore",
            "--convert-to", "pdf",
            "--outdir", out_dir, docx_path,
        ], check=True, capture_output=True, timeout=120)
        stem  = Path(docx_path).stem
        out_p = Path(out_dir) / f"{stem}.pdf"
        if out_p.exists() and str(out_p) != output_path:
            shutil.move(str(out_p), output_path)
        return output_path

    # ── Diff ──────────────────────────────────────────────────────────────────

    @staticmethod
    def diff_text(data_a: bytes, data_b: bytes,
                  context: int = 3) -> dict:
        def pages(d):
            doc = pymupdf.open(stream=d, filetype="pdf")
            t   = [p.get_text("text") for p in doc]
            doc.close()
            return t
        ta, tb = pages(data_a), pages(data_b)
        diffs  = []
        for i in range(max(len(ta), len(tb))):
            a = ta[i].splitlines(keepends=True) if i < len(ta) else ["[missing]\n"]
            b = tb[i].splitlines(keepends=True) if i < len(tb) else ["[missing]\n"]
            ud = list(difflib.unified_diff(a, b, fromfile=f"A:p{i+1}",
                                           tofile=f"B:p{i+1}", n=context))
            diffs.append({
                "page": i, "has_changes": bool(ud), "lines": ud,
                "adds": sum(1 for l in ud if l.startswith("+") and not l.startswith("+++")),
                "dels": sum(1 for l in ud if l.startswith("-") and not l.startswith("---")),
            })
        score = difflib.SequenceMatcher(None,
            "\n".join(ta), "\n".join(tb)).ratio()
        return {
            "pages_a": len(ta), "pages_b": len(tb),
            "changed": sum(1 for d in diffs if d["has_changes"]),
            "similarity": round(score * 100, 1),
            "diffs": diffs,
        }

    @staticmethod
    def diff_visual(data_a: bytes, data_b: bytes,
                    page: int = 0, dpi: int = 100) -> dict:
        import cv2, numpy as np
        def render(d, pg):
            doc = pymupdf.open(stream=d, filetype="pdf")
            mat = pymupdf.Matrix(dpi/72, dpi/72)
            pix = doc[min(pg, len(doc)-1)].get_pixmap(matrix=mat, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8
                    ).reshape(pix.height, pix.width, 3)
            doc.close()
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        ia, ib = render(data_a, page), render(data_b, page)
        if ia.shape != ib.shape:
            ib = cv2.resize(ib, (ia.shape[1], ia.shape[0]))
        diff   = cv2.absdiff(ia, ib)
        gray   = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, th  = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
        k      = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
        th     = cv2.dilate(th, k, iterations=2)
        amp    = cv2.convertScaleAbs(gray, alpha=4.0)
        heat   = cv2.applyColorMap(amp, cv2.COLORMAP_JET)
        mask   = cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)
        heat   = cv2.bitwise_and(heat, mask)
        blend  = cv2.addWeighted(ia, 0.45, heat, 0.55, 0)
        cnts,_ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        overlay = ia.copy()
        regions = []
        for cnt in cnts:
            if cv2.contourArea(cnt) < 50: continue
            x,y,w,h = cv2.boundingRect(cnt)
            cv2.rectangle(overlay,(x,y),(x+w,y+h),(0,0,255),2)
            regions.append({"x":x,"y":y,"w":w,"h":h})
        chg = round(int(np.sum(th>0)) / th.size * 100, 2)
        def enc(arr):
            _, buf = cv2.imencode(".png", arr)
            return buf.tobytes()
        return {
            "page": page, "change_pct": chg, "regions": len(regions),
            "img_a": enc(ia), "img_b": enc(ib),
            "heatmap": enc(blend), "overlay": enc(overlay),
        }

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _save(doc: pymupdf.Document) -> bytes:
        buf = io.BytesIO()
        doc.save(buf, garbage=4, deflate=True)
        doc.close()
        return buf.getvalue()

    @staticmethod
    def _find_soffice() -> str:
        candidates = [
            "soffice",
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            "/usr/bin/soffice",
        ]
        for c in candidates:
            if shutil.which(c) or os.path.isfile(c):
                return c
        raise FileNotFoundError(
            "LibreOffice not found. Install from https://www.libreoffice.org/download/")
