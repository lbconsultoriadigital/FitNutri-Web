from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request

from fitnutri.llm.client import DeepSeekClient
from fitnutri.models.schemas import ContextoPipeline
from fitnutri.output.generator import LaudoGenerator

from .config import PIPELINE_STAGES
from .dispatch import dispatch_stage, public_base_url
from .presenter import public_job
from .store import SupabaseStore

logger = logging.getLogger("fitnutri.execution")


async def execute_stage(
    job_id: str,
    stage: int,
    request: Request,
    store: SupabaseStore,
    *,
    dispatch_next: bool,
) -> dict[str, Any]:
    claimed = await store.claim_job(job_id, stage)
    if not claimed:
        existing = await store.get_job(job_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")
        if int(existing.get("current_stage") or 0) >= stage:
            return public_job(existing, include_artifacts=True)
        raise HTTPException(status_code=409, detail="A etapa não está disponível para execução")

    try:
        raw_context = claimed.get("context_data") or {}
        context = ContextoPipeline.model_validate(raw_context) if raw_context else ContextoPipeline()
        if stage == 1:
            object.__setattr__(context, "_dados_entrada", claimed["input_data"])

        llm = DeepSeekClient(api_key=os.getenv("DEEPSEEK_API_KEY"))
        _, _, agent_class = PIPELINE_STAGES[stage]
        context = await asyncio.to_thread(agent_class(llm).executar, context)
        update: dict[str, Any] = {
            "context_data": context.model_dump(mode="json"),
            "current_stage": stage,
            "stage_attempts": 0,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if stage == 6:
            report, markdown, html = LaudoGenerator().gerar_laudo(context)
            update.update({
                "status": "review_required",
                "laudo_json": report.model_dump(mode="json"),
                "laudo_markdown": markdown,
                "laudo_html": html,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            update["status"] = "queued"

        updated = await store.update_job(job_id, update)
        if not updated:
            raise RuntimeError("Atendimento não atualizado")
        if stage < 6 and dispatch_next:
            try:
                await dispatch_stage(job_id, stage + 1, public_base_url(request))
            except Exception:
                logger.exception("Etapa concluída, mas a próxima não foi enfileirada")
        return public_job(updated, include_artifacts=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Falha no job %s etapa %s", job_id, stage)
        attempts = int(claimed.get("stage_attempts") or 1)
        await store.update_job(job_id, {
            "status": "failed" if attempts >= 3 else "queued",
            "error_message": f"Falha na etapa {stage}: {PIPELINE_STAGES[stage][1]}",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"Falha ao executar {PIPELINE_STAGES[stage][1]}") from exc
