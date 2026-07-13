from __future__ import annotations

import logging
import os
from urllib.parse import quote

import httpx
from fastapi import Request

from .config import WORKER_TOKEN

logger = logging.getLogger("fitnutri.dispatch")


def public_base_url(request: Request) -> str:
    configured = os.getenv("PUBLIC_APP_URL", "").strip()
    return configured.rstrip("/") if configured else str(request.base_url).rstrip("/")


async def dispatch_stage(job_id: str, stage: int, public_url: str) -> None:
    token = os.getenv("QSTASH_TOKEN", "")
    if not token or not WORKER_TOKEN:
        raise RuntimeError("QStash/worker não configurado")
    destination = quote(f"{public_url.rstrip('/')}/api/jobs/process", safe="")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"https://qstash.upstash.io/v2/publish/{destination}",
            json={"job_id": job_id, "stage": stage},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Upstash-Forward-Authorization": f"Bearer {WORKER_TOKEN}",
                "Upstash-Retries": "3",
            },
        )
    if response.status_code >= 300:
        logger.error("QStash error %s: %s", response.status_code, response.text[:500])
        raise RuntimeError("Falha ao enfileirar etapa")
