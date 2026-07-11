"""API assíncrona do FitNutri para Vercel + Supabase + QStash."""
from __future__ import annotations

import asyncio
import hmac
import os
import secrets
import unicodedata
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import quote

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.sessions import SessionMiddleware

from fitnutri.agents import (
    AgenteEducadorFisico,
    AgenteExames,
    AgenteNutricionista,
    AgenteOrquestrador,
    AgenteSuplementacao,
    AgenteTriagem,
)
from fitnutri.llm.client import DeepSeekClient
from fitnutri.models.schemas import ContextoPipeline
from fitnutri.output.generator import LaudoGenerator

APP_VERSION = "2.0.0"
STAGES = {
    1: AgenteTriagem,
    2: AgenteExames,
    3: AgenteSuplementacao,
    4: AgenteNutricionista,
    5: AgenteEducadorFisico,
    6: AgenteOrquestrador,
}
SESSION_SECRET = os.getenv("FITNUTRI_SESSION_SECRET", "fitnutri-not-configured")
ADMIN_PASSWORD = os.getenv("FITNUTRI_ADMIN_PASSWORD", "")
WORKER_TOKEN = os.getenv("FITNUTRI_WORKER_TOKEN", "")
ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "").split(",") if x.strip()]

app = FastAPI(
    title="FitNutri Web API",
    version=APP_VERSION,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/api/docs",
    redoc_url=None,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="fitnutri_session",
    max_age=8 * 60 * 60,
    same_site="strict",
    https_only=os.getenv("ENVIRONMENT", "production") == "production",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


class AtendimentoCreate(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)
    nome: str = Field(min_length=2, max_length=160)
    idade: int = Field(ge=0, le=150)
    peso_kg: float = Field(gt=0, le=500)
    altura_m: float = Field(gt=0, le=3)
    sexo: Literal["masculino", "feminino"]
    profissao: str = Field(default="", max_length=160)
    objetivo: Literal[
        "emagrecimento", "hipertrofia", "performance",
        "recomposicao_corporal", "saude_bem_estar", "outro"
    ] = "saude_bem_estar"
    objetivo_descricao: str = Field(default="", max_length=2000)
    condicoes: list[str] = Field(default_factory=list, max_length=50)
    exames_texto: str = Field(default="", max_length=30_000)
    obs: str = Field(default="", max_length=10_000)


class LoginPayload(BaseModel):
    password: str = Field(min_length=1, max_length=500)


class WorkerPayload(BaseModel):
    job_id: str
    stage: int = Field(ge=1, le=6)


class ApprovalPayload(BaseModel):
    reviewer_name: str = Field(min_length=3, max_length=160)
    registration_type: Literal["CRM", "CRN", "CREF", "outro"]
    registration_number: str = Field(min_length=2, max_length=80)
    notes: str = Field(default="", max_length=4000)


class Store:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.url or not self.key:
            raise RuntimeError("Supabase não configurado")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    async def request(self, method: str, path: str, *, params=None, json=None, prefer=None):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method, f"{self.url}{path}", params=params, json=json, headers=headers
            )
        if response.status_code >= 400:
            raise RuntimeError("Falha de persistência")
        return response.json() if response.content else None

    async def insert(self, payload: dict[str, Any]):
        rows = await self.request(
            "POST", "/rest/v1/fitnutri_jobs", json=payload, prefer="return=representation"
        )
        return rows[0]

    async def get(self, job_id: str):
        rows = await self.request(
            "GET", "/rest/v1/fitnutri_jobs",
            params={"id": f"eq.{job_id}", "select": "*", "limit": "1"},
        )
        return rows[0] if rows else None

    async def get_slug(self, slug: str):
        rows = await self.request(
            "GET", "/rest/v1/fitnutri_jobs",
            params={"slug": f"eq.{slug}", "select": "*", "limit": "1"},
        )
        return rows[0] if rows else None

    async def list(self, limit: int = 100):
        return await self.request(
            "GET", "/rest/v1/fitnutri_jobs",
            params={"select": "*", "order": "created_at.desc", "limit": str(min(limit, 200))},
        ) or []

    async def update(self, job_id: str, payload: dict[str, Any]):
        rows = await self.request(
            "PATCH", "/rest/v1/fitnutri_jobs", params={"id": f"eq.{job_id}"},
            json=payload, prefer="return=representation"
        )
        return rows[0] if rows else None

    async def claim(self, job_id: str, stage: int):
        rows = await self.request(
            "POST", "/rest/v1/rpc/claim_fitnutri_job",
            json={"p_job_id": job_id, "p_stage": stage},
        )
        return rows[0] if rows else None


def get_store() -> Store:
    try:
        return Store()
    except RuntimeError as exc:
        raise HTTPException(503, "Persistência não configurada") from exc


def require_auth(request: Request):
    if request.session.get("authenticated") is not True:
        raise HTTPException(401, "Não autenticado")


def require_csrf(request: Request):
    require_auth(request)
    expected = request.session.get("csrf_token", "")
    received = request.headers.get("X-CSRF-Token", "")
    if not expected or not hmac.compare_digest(expected, received):
        raise HTTPException(403, "CSRF inválido")


def require_worker(request: Request):
    expected = f"Bearer {WORKER_TOKEN}" if WORKER_TOKEN else ""
    if not expected or not hmac.compare_digest(request.headers.get("Authorization", ""), expected):
        raise HTTPException(401, "Worker não autorizado")


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = "-".join("".join(c.lower() if c.isalnum() else " " for c in normalized).split())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{cleaned or 'paciente'}-{stamp}-{secrets.token_hex(3)}"


def public_url(request: Request) -> str:
    configured = os.getenv("PUBLIC_APP_URL", "").rstrip("/")
    return configured or str(request.base_url).rstrip("/")


async def dispatch(job_id: str, stage: int, base_url: str):
    qstash = os.getenv("QSTASH_TOKEN", "")
    if not qstash or not WORKER_TOKEN:
        raise RuntimeError("QStash não configurado")
    destination = quote(f"{base_url}/api/jobs/process", safe="")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"https://qstash.upstash.io/v2/publish/{destination}",
            json={"job_id": job_id, "stage": stage},
            headers={
                "Authorization": f"Bearer {qstash}",
                "Content-Type": "application/json",
                "Upstash-Forward-Authorization": f"Bearer {WORKER_TOKEN}",
                "Upstash-Retries": "3",
            },
        )
    if response.status_code >= 400:
        raise RuntimeError("Falha ao enfileirar etapa")


def present(job: dict[str, Any], artifacts: bool = False):
    data = {
        "id": job["id"], "slug": job["slug"], "patient_name": job["patient_name"],
        "status": job["status"], "current_stage": job["current_stage"],
        "error_message": job.get("error_message"), "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"), "approved_at": job.get("approved_at"),
        "reviewer_name": job.get("reviewer_name"),
        "registration_type": job.get("registration_type"),
        "registration_number": job.get("registration_number"),
    }
    if artifacts:
        data.update({
            "laudo_json": job.get("laudo_json"),
            "laudo_markdown": job.get("laudo_markdown"),
            "laudo_html": job.get("laudo_html"),
        })
    return data


@app.get("/api/health")
async def health():
    checks = {
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
        "supabase": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "qstash": bool(os.getenv("QSTASH_TOKEN")),
        "auth": bool(ADMIN_PASSWORD and SESSION_SECRET != "fitnutri-not-configured"),
        "worker": bool(WORKER_TOKEN),
    }
    return {"status": "operational" if all(checks.values()) else "degraded", "version": APP_VERSION, "checks": checks}


@app.post("/api/login")
async def login(payload: LoginPayload, request: Request):
    if not ADMIN_PASSWORD or SESSION_SECRET == "fitnutri-not-configured":
        raise HTTPException(503, "Autenticação não configurada")
    if not hmac.compare_digest(payload.password, ADMIN_PASSWORD):
        await asyncio.sleep(0.5)
        raise HTTPException(401, "Credenciais inválidas")
    token = secrets.token_urlsafe(32)
    request.session.clear()
    request.session.update({"authenticated": True, "csrf_token": token})
    return {"authenticated": True, "csrf_token": token}


@app.get("/api/session")
async def session(request: Request):
    authenticated = request.session.get("authenticated") is True
    return {"authenticated": authenticated, "csrf_token": request.session.get("csrf_token") if authenticated else None}


@app.post("/api/logout", dependencies=[Depends(require_csrf)])
async def logout(request: Request):
    request.session.clear()
    return {"success": True}


async def create_job(payload: AtendimentoCreate, request: Request, store: Store):
    now = datetime.now(timezone.utc).isoformat()
    job = await store.insert({
        "slug": slugify(payload.nome), "patient_name": payload.nome,
        "input_data": payload.model_dump(mode="json"), "context_data": {},
        "status": "queued", "current_stage": 0, "stage_attempts": 0,
        "created_at": now, "updated_at": now,
    })
    try:
        await dispatch(job["id"], 1, public_url(request))
    except Exception:
        await store.update(job["id"], {"status": "failed", "error_message": "Falha ao iniciar processamento", "updated_at": now})
        raise HTTPException(503, "Não foi possível iniciar o processamento")
    return present(job)


@app.post("/api/atendimentos", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_csrf)])
async def create_atendimento(payload: AtendimentoCreate, request: Request, store: Store = Depends(get_store)):
    return await create_job(payload, request, store)


@app.post("/api/executar", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_csrf)])
async def executar(payload: AtendimentoCreate, request: Request, store: Store = Depends(get_store)):
    job = await create_job(payload, request, store)
    return {"success": True, "job_id": job["id"], "slug": job["slug"], "status": job["status"]}


@app.get("/api/atendimentos", dependencies=[Depends(require_auth)])
async def list_atendimentos(limit: int = 100, store: Store = Depends(get_store)):
    return [present(job) for job in await store.list(limit)]


@app.get("/api/atendimentos/{job_id}", dependencies=[Depends(require_auth)])
async def get_atendimento(job_id: str, store: Store = Depends(get_store)):
    job = await store.get(job_id)
    if not job:
        raise HTTPException(404, "Atendimento não encontrado")
    return present(job, True)


@app.post("/api/atendimentos/{job_id}/approve", dependencies=[Depends(require_csrf)])
async def approve(job_id: str, payload: ApprovalPayload, store: Store = Depends(get_store)):
    job = await store.get(job_id)
    if not job:
        raise HTTPException(404, "Atendimento não encontrado")
    if job["status"] not in {"review_required", "approved"}:
        raise HTTPException(409, "Atendimento ainda não está pronto para aprovação")
    updated = await store.update(job_id, {
        "status": "approved", "reviewer_name": payload.reviewer_name,
        "registration_type": payload.registration_type,
        "registration_number": payload.registration_number,
        "review_notes": payload.notes,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return present(updated, True)


@app.get("/api/pacientes", dependencies=[Depends(require_auth)])
async def pacientes(store: Store = Depends(get_store)):
    return [{
        "id": j["id"], "slug": j["slug"], "nome": j["patient_name"],
        "data": (j.get("created_at") or "")[:10], "status": j["status"],
        "tem_laudo": j.get("current_stage") == 6,
    } for j in await store.list()]


@app.get("/api/paciente", dependencies=[Depends(require_auth)])
async def paciente(slug: str, store: Store = Depends(get_store)):
    job = await store.get_slug(slug)
    if not job:
        raise HTTPException(404, "Paciente não encontrado")
    return {"slug": slug, "laudo_json": job.get("laudo_json"), "laudo_md": job.get("laudo_markdown"), "laudo_html": job.get("laudo_html"), "status": job["status"]}


@app.get("/api/laudo-html", dependencies=[Depends(require_auth)], response_class=HTMLResponse)
async def laudo_html(slug: str, store: Store = Depends(get_store)):
    job = await store.get_slug(slug)
    if not job or not job.get("laudo_html"):
        raise HTTPException(404, "Laudo não encontrado")
    return HTMLResponse(job["laudo_html"])


@app.post("/api/jobs/process", dependencies=[Depends(require_worker)])
async def process(payload: WorkerPayload, request: Request, store: Store = Depends(get_store)):
    claimed = await store.claim(payload.job_id, payload.stage)
    if not claimed:
        return {"accepted": False, "reason": "duplicate_or_invalid_stage"}
    try:
        raw_context = claimed.get("context_data") or {}
        context = ContextoPipeline.model_validate(raw_context) if raw_context else ContextoPipeline()
        if payload.stage == 1:
            object.__setattr__(context, "_dados_entrada", claimed["input_data"])
        agent = STAGES[payload.stage](DeepSeekClient(api_key=os.getenv("DEEPSEEK_API_KEY")))
        context = await asyncio.to_thread(agent.executar, context)
        update: dict[str, Any] = {
            "context_data": context.model_dump(mode="json"),
            "current_stage": payload.stage,
            "stage_attempts": 0,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if payload.stage == 6:
            laudo, markdown, html = LaudoGenerator().gerar_laudo(context)
            update.update({
                "status": "review_required",
                "laudo_json": laudo.model_dump(mode="json"),
                "laudo_markdown": markdown,
                "laudo_html": html,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            update["status"] = "queued"
        await store.update(payload.job_id, update)
        if payload.stage < 6:
            await dispatch(payload.job_id, payload.stage + 1, public_url(request))
        return {"accepted": True, "job_id": payload.job_id, "stage": payload.stage}
    except Exception as exc:
        attempts = int(claimed.get("stage_attempts") or 1)
        await store.update(payload.job_id, {
            "status": "failed" if attempts >= 3 else "queued",
            "error_message": "Falha no processamento da etapa",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        raise HTTPException(500, "Falha no processamento") from exc
