from __future__ import annotations

import hmac
import json
import os

from fastapi import HTTPException, Request
from pydantic import ValidationError

from .config import WORKER_TOKEN
from .schemas import AtendimentoCreate
from .store import SupabaseStore


def get_store() -> SupabaseStore:
    try:
        return SupabaseStore(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Persistência não configurada") from exc


def require_auth(request: Request) -> None:
    if request.session.get("authenticated") is not True:
        raise HTTPException(status_code=401, detail="Não autenticado")


def require_csrf(request: Request) -> None:
    require_auth(request)
    expected = request.session.get("csrf_token", "")
    received = request.headers.get("X-CSRF-Token", "")
    if not expected or not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="CSRF inválido")


def require_worker(request: Request) -> None:
    expected = f"Bearer {WORKER_TOKEN}" if WORKER_TOKEN else ""
    received = request.headers.get("Authorization", "")
    if not expected or not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Worker não autorizado")


async def parse_create_request(request: Request):
    content_type = request.headers.get("content-type", "")
    try:
        if "multipart/form-data" in content_type:
            form = await request.form()
            raw_payload = form.get("payload")
            if not isinstance(raw_payload, str):
                raise HTTPException(status_code=422, detail="Dados do atendimento ausentes")
            payload_data = json.loads(raw_payload)
            candidate = form.get("exame_pdf")
            exam_file = candidate if getattr(candidate, "filename", None) and hasattr(candidate, "read") else None
        else:
            payload_data = await request.json()
            exam_file = None
        return AtendimentoCreate.model_validate(payload_data), exam_file
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Dados do atendimento inválidos") from exc
