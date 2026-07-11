from __future__ import annotations

import asyncio
import hmac
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request

from .config import (
    ADMIN_PASSWORD, APP_VERSION, MAX_PDF_BYTES, SESSION_SECRET,
    manual_processing, qstash_ready,
)
from .dependencies import require_csrf
from .schemas import LoginPayload

router = APIRouter()


@router.get("/api")
@router.get("/api/health")
async def health():
    checks = {
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
        "supabase": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "auth": bool(ADMIN_PASSWORD and SESSION_SECRET != "fitnutri-not-configured"),
        "dispatch": manual_processing() or qstash_ready(),
        "qstash": qstash_ready(),
        "pdf_storage": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
    }
    essential = checks["deepseek"] and checks["supabase"] and checks["auth"] and checks["dispatch"]
    return {
        "status": "operational" if essential else "degraded",
        "version": APP_VERSION,
        "processing_mode": "manual" if manual_processing() else "qstash",
        "max_pdf_bytes": MAX_PDF_BYTES,
        "checks": checks,
    }


@router.post("/api/login")
async def login(payload: LoginPayload, request: Request):
    if not ADMIN_PASSWORD or SESSION_SECRET == "fitnutri-not-configured":
        raise HTTPException(status_code=503, detail="Autenticação não configurada")
    if not hmac.compare_digest(payload.password, ADMIN_PASSWORD):
        await asyncio.sleep(0.5)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = secrets.token_urlsafe(32)
    request.session.clear()
    request.session.update({"authenticated": True, "csrf_token": token})
    return {"authenticated": True, "csrf_token": token}


@router.get("/api/session")
async def session(request: Request):
    authenticated = request.session.get("authenticated") is True
    return {
        "authenticated": authenticated,
        "csrf_token": request.session.get("csrf_token") if authenticated else None,
    }


@router.post("/api/logout", dependencies=[Depends(require_csrf)])
async def logout(request: Request):
    request.session.clear()
    return {"success": True}
