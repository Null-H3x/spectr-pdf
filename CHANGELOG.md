# Changelog

All notable changes to Spectr PDF are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2025

### Added — Backend

**Phase 1 — Core viewer**
- PDF metadata extraction (page count, dimensions, TOC, author, dates)
- Per-page thumbnail rendering at configurable DPI (base64 PNG)
- Bulk thumbnail endpoint for small documents

**Phase 2 — Page operations & security**
- Merge 2+ PDFs preserving bookmarks and page order
- Split by page ranges (`1-3, 5, 8-end` syntax) → ZIP output
- Extract specific pages into new PDF
- Drag-reorder pages
- Rotate pages 90 / 180 / 270° (all pages or selection)
- Delete pages
- Add highlight, underline, strikeout, squiggly annotations
- Add sticky notes and freetext overlay boxes
- List, delete, and flatten annotations
- Search for text → bounding boxes per page
- Apply redaction rectangles (permanent content removal)
- Auto-redact all occurrences of a text pattern
- AES-256 password encryption with granular permissions
- PDF decryption

**Phase 3 — Digital signatures**
- Generate self-signed PKCS#12 certificates (`.p12`)
- Add visible signature field widgets to pages
- Apply cryptographic signatures via pyHanko (async)
- Verify existing signatures (valid / intact / trusted / coverage)

**Phase 4 — OCR**
- Tesseract availability check + language pack enumeration
- Extract text from scanned/image-based pages with confidence scores
- Make scanned PDFs searchable (invisible text layer overlay)
- Per-page analysis (native text vs scanned, word count, confidence)
- Language/orientation detection via Tesseract OSD

**Phase 5 — Format conversion**
- PDF → Images (PNG/JPEG, any DPI) → ZIP
- Images → PDF (PNG, JPEG, WEBP, BMP, TIFF)
- PDF → DOCX via LibreOffice headless (writer_pdf_import filter)
- DOCX/ODT/RTF → PDF via LibreOffice headless
- PDF → HTML via LibreOffice
- PDF → plain text (fast, PyMuPDF native)
- Strip all metadata (author, dates, software info)

**Phase 7 — Format diff**
- Unified text diff per page pair (git diff for PDFs)
- Pixel-level visual diff with OpenCV heatmap + contour bounding boxes
- Structural diff (fonts, page dimensions, image counts)
- Similarity score (0–100%, text + visual weighted)
- Self-contained HTML diff report (SPECTR-themed, no internet required)

### Added — Flutter UI

**Phase 6 — UI shell**
- SPECTR cyberpunk theme (Space Grotesk, JetBrains Mono, cyan/violet/pink palette)
- 64px icon sidebar with 10 navigation items + backend status dot
- Home screen with drop zone, feature pills, offline warning
- PDF viewer: backend-rendered pages, thumbnail strip, zoom controls, status bar
- Pages screen: merge with drag-to-reorder list, split with live range validation,
  rotate (all/selection), delete via thumbnail grid, reorder via drag list
- Annotate screen: sticky note form, annotation list dialog, flatten
- Forms screen: detect fields, dynamic fill inputs
- Signing screen: cert generation, sign, verify (3-tab)
- OCR screen: Tesseract status, language/DPI picker, extract text, make searchable
- Redact screen: find+count+redact, AES-256 encrypt with permission toggles
- Convert screen: PDF→images, images→PDF, PDF↔DOCX, strip metadata
- Diff screen: 4-tab (Text / Visual / Structure / Summary), HTML report export
- Reusable `PageSelectorGrid` (multi-select + drag-reorder)
- `ResultSheet` bottom sheet (replace doc / save to Downloads / dismiss)
- Cross-platform `FileSaver` (Downloads folder on desktop, share sheet on Android)
- Page range parser (`1-3, 5, 8-end` → 0-indexed arrays with validation)

### Added — Packaging

- Windows system tray launcher (pystray)
- Dependency pre-flight table at startup
- Multi-resolution `.ico` (7 sizes, 16–256px) generated from SPECTR palette
- SPECTR-themed Inno Setup installer (164×314 sidebar, 497×55 header)
- Auto-detects Tesseract/LibreOffice, warns with download URLs if missing
- Desktop shortcut, optional Windows startup entry
- PyInstaller spec bundling all 7 phases of dependencies

---

## [Unreleased]

- Android Chaquopy packaging (Phase 8)
- LibreOffice headless bundled in installer (optional component)
- Drag-and-drop file accept from Windows Explorer
- Batch operations (process multiple files)
- Recent files list
