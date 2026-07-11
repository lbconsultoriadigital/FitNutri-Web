from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from .create_service import create_atendimento
from .dependencies import get_store, parse_create_request, require_auth, require_csrf
from .exam_service import finalize_exam_upload, prepare_exam_upload
from .presenter import exam_files_for_job, public_job
from .schemas import ApprovalPayload, AtendimentoCreate, ExamUploadFinalize, ExamUploadPrepare
from .store import SupabaseStore

router = APIRouter()


@router.post("/api/atendimentos", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_csrf)])
async def create_attendance(request: Request, store: SupabaseStore = Depends(get_store)):
    payload, exam_file = await parse_create_request(request)
    return await create_atendimento(payload, request, store, exam_file)


@router.post("/api/executar", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_csrf)])
async def execute_compat(payload: AtendimentoCreate, request: Request, store: SupabaseStore = Depends(get_store)):
    job = await create_atendimento(payload, request, store)
    return {
        "success": True,
        "job_id": job["id"],
        "slug": job["slug"],
        "status": job["status"],
        "requires_manual_processing": job["requires_manual_processing"],
    }


@router.get("/api/atendimentos", dependencies=[Depends(require_auth)])
async def list_attendances(limit: int = 100, store: SupabaseStore = Depends(get_store)):
    return [public_job(job) for job in await store.list_jobs(limit)]


@router.get("/api/atendimentos/{job_id}", dependencies=[Depends(require_auth)])
async def get_attendance(job_id: str, store: SupabaseStore = Depends(get_store)):
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    return public_job(job, include_artifacts=True)


@router.post("/api/atendimentos/{job_id}/exames/presign", dependencies=[Depends(require_csrf)])
async def presign_exam(
    job_id: str,
    payload: ExamUploadPrepare,
    store: SupabaseStore = Depends(get_store),
):
    return await prepare_exam_upload(job_id, payload, store)


@router.post("/api/atendimentos/{job_id}/exames/finalize", dependencies=[Depends(require_csrf)])
async def finalize_exam(
    job_id: str,
    payload: ExamUploadFinalize,
    store: SupabaseStore = Depends(get_store),
):
    return await finalize_exam_upload(job_id, payload, store)


@router.get("/api/atendimentos/{job_id}/exames/{file_id}", dependencies=[Depends(require_auth)])
async def get_exam_file(job_id: str, file_id: str, store: SupabaseStore = Depends(get_store)):
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    item = next((entry for entry in exam_files_for_job(job) if entry.get("id") == file_id), None)
    if not item or not item.get("path"):
        raise HTTPException(status_code=404, detail="PDF de exames não encontrado")
    try:
        content = await store.download_pdf(str(item["path"]))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Não foi possível carregar o PDF") from exc
    filename = str(item.get("name") or "exames.pdf")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/api/atendimentos/{job_id}/exame-pdf", dependencies=[Depends(require_auth)])
async def get_exam_pdf(job_id: str, store: SupabaseStore = Depends(get_store)):
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    files = exam_files_for_job(job)
    if not files:
        raise HTTPException(status_code=404, detail="PDF de exames não encontrado")
    item = files[0]
    try:
        content = await store.download_pdf(str(item["path"]))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Não foi possível carregar o PDF") from exc
    filename = str(item.get("name") or "exames.pdf")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/api/atendimentos/{job_id}/approve", dependencies=[Depends(require_csrf)])
async def approve_attendance(
    job_id: str,
    payload: ApprovalPayload,
    store: SupabaseStore = Depends(get_store),
):
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    if job["status"] not in {"review_required", "approved"}:
        raise HTTPException(status_code=409, detail="Atendimento ainda não está pronto para aprovação")
    now = datetime.now(timezone.utc).isoformat()
    updated = await store.update_job(job_id, {
        "status": "approved",
        "reviewer_name": payload.reviewer_name,
        "registration_type": payload.registration_type,
        "registration_number": payload.registration_number,
        "review_notes": payload.notes,
        "approved_at": now,
        "updated_at": now,
    })
    if not updated:
        raise HTTPException(status_code=500, detail="Falha ao aprovar atendimento")
    return public_job(updated, include_artifacts=True)
