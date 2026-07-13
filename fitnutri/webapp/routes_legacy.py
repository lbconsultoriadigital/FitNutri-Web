from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from fitnutri.output.html_renderer import render_report_html

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
    markdown_text = job.get("laudo_markdown")
    report_html = render_report_html(str(markdown_text)) if markdown_text else job.get("laudo_html")
    return {
        "slug": job["slug"],
        "laudo_json": job.get("laudo_json"),
        "laudo_md": markdown_text,
        "laudo_html": report_html,
        "status": job["status"],
    }


@router.get("/api/laudo-html", response_class=HTMLResponse)
async def legacy_html(slug: str, store: SupabaseStore = Depends(get_store)):
    job = await store.get_job_by_slug(slug)
    if not job:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    markdown_text = job.get("laudo_markdown")
    report_html = render_report_html(str(markdown_text)) if markdown_text else job.get("laudo_html")
    if not report_html:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")
    return HTMLResponse(report_html)
