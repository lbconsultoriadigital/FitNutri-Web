from __future__ import annotations

import io
import logging

from fastapi import HTTPException
from pypdf import PdfReader

from .config import MAX_EXTRACTED_TEXT

logger = logging.getLogger("fitnutri.pdf")


def extract_pdf_text(content: bytes) -> tuple[str, int, str | None]:
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise HTTPException(status_code=422, detail="O PDF está protegido por senha") from exc
        if len(reader.pages) > 60:
            raise HTTPException(status_code=422, detail="O PDF possui páginas demais para o protótipo")

        chunks: list[str] = []
        length = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                page_text = page.extract_text() or ""
            page_text = page_text.replace("\x00", "").strip()
            if page_text:
                chunk = f"--- Página {page_number} ---\n{page_text}"
                chunks.append(chunk)
                length += len(chunk)
            if length >= MAX_EXTRACTED_TEXT:
                break

        extracted = "\n\n".join(chunks)[:MAX_EXTRACTED_TEXT]
        warning = None
        if len(extracted.strip()) < 80:
            warning = "Pouco texto foi extraído. O PDF pode ser digitalizado como imagem e exigir OCR ou transcrição."
        return extracted, len(reader.pages), warning
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Falha ao ler PDF")
        raise HTTPException(status_code=422, detail="Não foi possível interpretar o PDF enviado") from exc
