"""Probe native and local OCR text extraction for PDFs without saving resume text."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.parser import _ocr_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="统计 PDF 原生文本与 OCR 可读率")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    files = sorted(path for path in args.corpus.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")
    native = ocr = 0
    failed: list[str] = []
    for path in files:
        with pdfplumber.open(str(path)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        improved, _ = _ocr_pdf(path)
        native += int(bool(text.strip()))
        ocr += int(bool(improved.strip()))
        if not improved.strip():
            failed.append(path.name)
    rate = lambda value: round(value / len(files), 4) if files else 0.0
    result = {
        "pdf_files": len(files),
        "native_text_ok": native,
        "native_rate": rate(native),
        "ocr_text_ok": ocr,
        "ocr_rate": rate(ocr),
        "ocr_failed_count": len(failed),
        "ocr_failed_names": failed[:10],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
