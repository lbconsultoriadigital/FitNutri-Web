from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from .dependencies import get_store, require_auth
from .store import SupabaseStore

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/api/pacientes")
async def legacy_patients(store: SupabaseStore = Depends(get_store)):
    return [{
        "id": job["id"],
        "slug": job["slug"],
        "nome": job["patient_name"],
        "data": (job.get("created_at") or "")[:10],
        "status": job["status"],
        "tem_laudo": int(job.get("current_stage") or 0) == 6,
    } for job in await store.list_jobs(100)]


@router.get("/api/paciente")
async def legacy_patient(slug: str, store: SupabaseStore = Depends(get_store)):
    job = await store.get_job_by_slug(slug)
    if not job:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return {
        "slug": job["slug"],
        "laudo_json": job.get("laudo_json"),
        "laudo_md": job.get("laudo_markdown"),
        "laudo_html": job.get("laudo_html"),
        "status": job["status"],
    }


@router.get("/api/laudo-html", response_class=HTMLResponse)
async def legacy_html(slug: str, store: SupabaseStore = Depends(get_store)):
    job = await store.get_job_by_slug(slug)
    if not job or not job.get("laudo_html"):
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    return HTMLResponse(job["laudo_html"])
