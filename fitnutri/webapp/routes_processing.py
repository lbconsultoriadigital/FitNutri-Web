from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from .dependencies import get_store, require_csrf, require_worker
from .execution_service import execute_stage
from .presenter import public_job
from .schemas import WorkerPayload
from .store import SupabaseStore

router = APIRouter()


@router.post("/api/atendimentos/{job_id}/advance", dependencies=[Depends(require_csrf)])
async def advance_attendance(job_id: str, request: Request, store: SupabaseStore = Depends(get_store)):
    job = await store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    current_stage = int(job.get("current_stage") or 0)
    if job["status"] in {"review_required", "approved"} or current_stage >= 6:
        return public_job(job, include_artifacts=True)
    if job["status"] == "failed":
        await store.update_job(job_id, {
            "status": "queued",
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return await execute_stage(job_id, current_stage + 1, request, store, dispatch_next=False)


@router.post("/api/jobs/process", dependencies=[Depends(require_worker)])
async def process_job(payload: WorkerPayload, request: Request, store: SupabaseStore = Depends(get_store)):
    return await execute_stage(payload.job_id, payload.stage, request, store, dispatch_next=True)
