from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request, UploadFile

from .config import MAX_EXTRACTED_TEXT, MAX_PDF_BYTES, manual_processing, safe_filename, slugify
from .dispatch import dispatch_stage, public_base_url
from .pdf_tools import extract_pdf_text
from .presenter import public_job
from .schemas import AtendimentoCreate
from .store import SupabaseStore

logger = logging.getLogger("fitnutri.create")


async def create_atendimento(
    payload: AtendimentoCreate,
    request: Request,
    store: SupabaseStore,
    exam_file: UploadFile | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    job_id = str(uuid.uuid4())
    storage_path: str | None = None
    exam_metadata: dict[str, Any] = {}
    payload_data = payload.model_dump(mode="json")

    if exam_file and exam_file.filename:
        filename = safe_filename(exam_file.filename)
        content = await exam_file.read(MAX_PDF_BYTES + 1)
        await exam_file.close()
        if len(content) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="O PDF deve ter no máximo 4 MB")
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail="O arquivo anexado não é um PDF válido")
        extracted, page_count, warning = extract_pdf_text(content)
        manual_text = payload_data.get("exames_texto", "").strip()
        if extracted:
            section = f"CONTEÚDO EXTRAÍDO DO PDF '{filename}':\n{extracted}"
            payload_data["exames_texto"] = "\n\n".join(filter(None, [manual_text, section]))[:MAX_EXTRACTED_TEXT]
        storage_path = f"jobs/{job_id}/{filename}"
        await store.upload_pdf(storage_path, content)
        exam_metadata = {
            "exam_file_path": storage_path,
            "exam_file_name": filename,
            "exam_file_size": len(content),
            "exam_page_count": page_count,
            "exam_text_length": len(extracted),
            "exam_extract_warning": warning,
        }

    try:
        job = await store.insert_job({
            "id": job_id,
            "slug": slugify(payload.nome),
            "patient_name": payload.nome,
            "input_data": payload_data,
            "context_data": {},
            "status": "queued",
            "current_stage": 0,
            "stage_attempts": 0,
            "created_at": now,
            "updated_at": now,
            **exam_metadata,
        })
    except Exception:
        if storage_path:
            await store.delete_pdf(storage_path)
        raise HTTPException(status_code=500, detail="Não foi possível criar o atendimento")

    if not manual_processing():
        try:
            await dispatch_stage(job["id"], 1, public_base_url(request))
        except Exception:
            logger.exception("QStash indisponível; o caso poderá ser executado pelo painel")
    return public_job(job, include_artifacts=True)
