from __future__ import annotations

from typing import Any

from .config import PIPELINE_STAGES, manual_processing


def extract_agent_outputs(context_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "triagem": context_data.get("paciente"),
        "exames": context_data.get("analise_exames"),
        "suplementacao": context_data.get("protocolo_suplementacao"),
        "nutricao": context_data.get("plano_alimentar"),
        "treino": context_data.get("plano_treino"),
        "consolidacao": context_data.get("laudo_final"),
    }


def public_job(job: dict[str, Any], include_artifacts: bool = False) -> dict[str, Any]:
    current_stage = int(job.get("current_stage") or 0)
    stage = PIPELINE_STAGES.get(current_stage, ("aguardando", "Aguardando", None))
    result = {
        "id": job["id"],
        "slug": job["slug"],
        "patient_name": job["patient_name"],
        "status": job["status"],
        "current_stage": current_stage,
        "next_stage": current_stage + 1 if current_stage < 6 else None,
        "stage_name": stage[0],
        "stage_label": stage[1],
        "error_message": job.get("error_message"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "approved_at": job.get("approved_at"),
        "reviewer_name": job.get("reviewer_name"),
        "registration_type": job.get("registration_type"),
        "registration_number": job.get("registration_number"),
        "has_exam_pdf": bool(job.get("exam_file_path")),
        "exam_file_name": job.get("exam_file_name"),
        "exam_file_size": job.get("exam_file_size"),
        "exam_page_count": job.get("exam_page_count"),
        "exam_text_length": job.get("exam_text_length"),
        "exam_extract_warning": job.get("exam_extract_warning"),
        "processing_mode": "manual" if manual_processing() else "qstash",
        "requires_manual_processing": manual_processing() and current_stage < 6,
    }
    if include_artifacts:
        context_data = job.get("context_data") or {}
        result.update({
            "agent_outputs": extract_agent_outputs(context_data),
            "laudo_json": job.get("laudo_json"),
            "laudo_markdown": job.get("laudo_markdown"),
            "laudo_html": job.get("laudo_html"),
        })
    return result
