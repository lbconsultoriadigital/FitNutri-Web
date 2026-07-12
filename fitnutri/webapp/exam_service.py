from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from .config import MAX_EXAM_FILES, MAX_EXTRACTED_TEXT, MAX_PDF_BYTES, safe_filename
from .pdf_tools import extract_pdf_text
from .presenter import exam_files_for_job, public_job
from .schemas import ExamUploadFinalize, ExamUploadPrepare
from .store import SupabaseStore


def _assert_editable(job: dict[str, Any]) -> None:
    if int(job.get("current_stage") or 0) > 0:
        raise HTTPException(status_code=409, detail="Os exames não podem ser alterados após o início dos agentes")
    if job.get("status") not in {"queued", "failed"}:
        raise HTTPException(status_code=409, detail="Atendimento indisponível para anexos")


async def _register_exam_content(
    job_id: str,
    filename: str,
    content: bytes,
    store: SupabaseStore,
    *,
    file_id: str | None = None,
    storage_path: str | None = None,
    already_uploaded: bool = False,
) -> dict[str, Any]:
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    _assert_editable(job)

    files = exam_files_for_job(job)
    if len(files) >= MAX_EXAM_FILES:
        raise HTTPException(status_code=409, detail=f"Limite de {MAX_EXAM_FILES} PDFs por atendimento")

    safe_name = safe_filename(filename)
    resolved_file_id = file_id or uuid.uuid4().hex
    path = storage_path or f"jobs/{job_id}/{resolved_file_id}-{safe_name}"

    if any(item.get("id") == resolved_file_id for item in files):
        return public_job(job, include_artifacts=True)
    if not content:
        raise HTTPException(status_code=422, detail="O PDF enviado está vazio")
    if len(content) > MAX_PDF_BYTES:
        if already_uploaded:
            await store.delete_pdf(path)
        raise HTTPException(status_code=413, detail="Cada PDF deve ter no máximo 4 MB")
    if not content.startswith(b"%PDF-"):
        if already_uploaded:
            await store.delete_pdf(path)
        raise HTTPException(status_code=422, detail="O arquivo enviado não é um PDF válido")

    uploaded = already_uploaded
    try:
        extracted, page_count, warning = extract_pdf_text(content)
        if not uploaded:
            await store.upload_pdf(path, content)
            uploaded = True

        metadata = {
            "id": resolved_file_id,
            "path": path,
            "name": safe_name,
            "size": len(content),
            "page_count": page_count,
            "text_length": len(extracted),
            "warning": warning,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        files.append(metadata)

        input_data = dict(job.get("input_data") or {})
        current_text = str(input_data.get("exames_texto") or "").strip()
        if extracted:
            section = f"CONTEÚDO EXTRAÍDO DO PDF '{safe_name}':\n{extracted}"
            input_data["exames_texto"] = "\n\n".join(filter(None, [current_text, section]))[:MAX_EXTRACTED_TEXT]

        update: dict[str, Any] = {
            "exam_files": files,
            "input_data": input_data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if not job.get("exam_file_path"):
            update.update({
                "exam_file_path": path,
                "exam_file_name": safe_name,
                "exam_file_size": len(content),
                "exam_page_count": page_count,
                "exam_text_length": len(extracted),
                "exam_extract_warning": warning,
            })

        updated = await store.update_job(job_id, update)
        if not updated:
            raise RuntimeError("Atualização vazia")
        return public_job(updated, include_artifacts=True)
    except HTTPException:
        if uploaded:
            await store.delete_pdf(path)
        raise
    except Exception as exc:
        if uploaded:
            await store.delete_pdf(path)
        raise HTTPException(status_code=500, detail="Não foi possível registrar o PDF") from exc


async def upload_exam_content(
    job_id: str,
    filename: str,
    content: bytes,
    store: SupabaseStore,
) -> dict[str, Any]:
    return await _register_exam_content(job_id, filename, content, store)


async def prepare_exam_upload(
    job_id: str,
    payload: ExamUploadPrepare,
    store: SupabaseStore,
) -> dict[str, Any]:
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    _assert_editable(job)
    if len(exam_files_for_job(job)) >= MAX_EXAM_FILES:
        raise HTTPException(status_code=409, detail=f"Limite de {MAX_EXAM_FILES} PDFs por atendimento")

    filename = safe_filename(payload.filename)
    file_id = uuid.uuid4().hex
    path = f"jobs/{job_id}/{file_id}-{filename}"
    try:
        signed_url = await store.create_signed_upload_url(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Não foi possível preparar o upload do PDF") from exc
    return {
        "file_id": file_id,
        "filename": filename,
        "path": path,
        "signed_url": signed_url,
        "max_bytes": MAX_PDF_BYTES,
    }


async def finalize_exam_upload(
    job_id: str,
    payload: ExamUploadFinalize,
    store: SupabaseStore,
) -> dict[str, Any]:
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    _assert_editable(job)

    filename = safe_filename(payload.filename)
    path = f"jobs/{job_id}/{payload.file_id}-{filename}"
    if any(item.get("id") == payload.file_id for item in exam_files_for_job(job)):
        return public_job(job, include_artifacts=True)
    try:
        content = await store.download_pdf(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="O PDF não foi encontrado após o upload") from exc

    return await _register_exam_content(
        job_id,
        filename,
        content,
        store,
        file_id=payload.file_id,
        storage_path=path,
        already_uploaded=True,
    )
