from __future__ import annotations

import hashlib
import os
import secrets
import unicodedata
from datetime import datetime, timezone

from fitnutri.agents import (
    AgenteEducadorFisico,
    AgenteExames,
    AgenteNutricionista,
    AgenteOrquestrador,
    AgenteSuplementacao,
    AgenteTriagem,
)

APP_VERSION = "2.1.1"
PDF_BUCKET = os.getenv("FITNUTRI_EXAM_BUCKET", "fitnutri-exames")
MAX_PDF_BYTES = min(int(os.getenv("FITNUTRI_MAX_PDF_BYTES", "4000000")), 4_000_000)
MAX_EXTRACTED_TEXT = int(os.getenv("FITNUTRI_MAX_EXAM_TEXT", "60000"))
DISPATCH_MODE = os.getenv("FITNUTRI_DISPATCH_MODE", "manual").strip().lower()
ADMIN_PASSWORD = os.getenv("FITNUTRI_ADMIN_PASSWORD", "")
_explicit_session_secret = os.getenv("FITNUTRI_SESSION_SECRET", "")
SESSION_SECRET = (
    _explicit_session_secret
    or (
        hashlib.sha256(f"fitnutri-session-v1:{ADMIN_PASSWORD}".encode("utf-8")).hexdigest()
        if ADMIN_PASSWORD
        else "fitnutri-not-configured"
    )
)
WORKER_TOKEN = os.getenv("FITNUTRI_WORKER_TOKEN", "")
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "").split(",") if x.strip()]

PIPELINE_STAGES: dict[int, tuple[str, str, type]] = {
    1: ("triagem", "Agente de Triagem", AgenteTriagem),
    2: ("exames", "Agente de Exames", AgenteExames),
    3: ("suplementacao", "Agente de Suplementação", AgenteSuplementacao),
    4: ("nutricao", "Agente Nutricionista", AgenteNutricionista),
    5: ("treino", "Agente de Treino", AgenteEducadorFisico),
    6: ("consolidacao", "Orquestrador Clínico", AgenteOrquestrador),
}


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in normalized).split())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{cleaned or 'paciente'}-{stamp}-{secrets.token_hex(3)}"


def safe_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    normalized = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    cleaned = "-".join("".join(ch.lower() if ch.isalnum() or ch in ".-_" else " " for ch in normalized).split())
    if not cleaned.endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned[:120] or "exames.pdf"


def qstash_ready() -> bool:
    return bool(os.getenv("QSTASH_TOKEN") and WORKER_TOKEN)


def manual_processing() -> bool:
    return DISPATCH_MODE != "qstash" or not qstash_ready()
