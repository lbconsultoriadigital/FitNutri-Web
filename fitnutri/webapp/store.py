from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from .config import PDF_BUCKET

logger = logging.getLogger("fitnutri.store")


class SupabaseStore:
    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        if not self.base_url or not self.service_key:
            raise RuntimeError("Supabase não configurado")
        self.auth_headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: Any = None,
        prefer: str | None = None,
    ) -> Any:
        headers = {**self.auth_headers, "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )
        if response.status_code >= 400:
            logger.error("Supabase error %s: %s", response.status_code, response.text[:500])
            raise RuntimeError("Falha de persistência")
        return response.json() if response.content else None

    async def insert_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self._request(
            "POST", "/rest/v1/fitnutri_jobs",
            json_body=payload, prefer="return=representation",
        )
        if not rows:
            raise RuntimeError("Atendimento não criado")
        return rows[0]

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        rows = await self._request(
            "GET", "/rest/v1/fitnutri_jobs",
            params={"id": f"eq.{job_id}", "select": "*", "limit": "1"},
        )
        return rows[0] if rows else None

    async def get_job_by_slug(self, slug: str) -> dict[str, Any] | None:
        rows = await self._request(
            "GET", "/rest/v1/fitnutri_jobs",
            params={"slug": f"eq.{slug}", "select": "*", "limit": "1"},
        )
        return rows[0] if rows else None

    async def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        fields = (
            "id,slug,patient_name,status,current_stage,error_message,created_at,updated_at,"
            "approved_at,reviewer_name,registration_type,registration_number,exam_files,"
            "exam_file_path,exam_file_name,exam_file_size,exam_page_count,exam_text_length,exam_extract_warning"
        )
        rows = await self._request(
            "GET", "/rest/v1/fitnutri_jobs",
            params={"select": fields, "order": "created_at.desc", "limit": str(min(max(limit, 1), 200))},
        )
        return rows or []

    async def update_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        rows = await self._request(
            "PATCH", "/rest/v1/fitnutri_jobs",
            params={"id": f"eq.{job_id}"}, json_body=payload, prefer="return=representation",
        )
        return rows[0] if rows else None

    async def claim_job(self, job_id: str, stage: int) -> dict[str, Any] | None:
        rows = await self._request(
            "POST", "/rest/v1/rpc/claim_fitnutri_job",
            json_body={"p_job_id": job_id, "p_stage": stage},
        )
        return rows[0] if rows else None

    async def create_signed_upload_url(self, path: str) -> str:
        encoded = quote(f"{PDF_BUCKET}/{path}", safe="/")
        headers = {**self.auth_headers, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/storage/v1/object/upload/sign/{encoded}",
                headers=headers,
                json={},
            )
        if response.status_code >= 300:
            logger.error("Signed upload error %s: %s", response.status_code, response.text[:500])
            raise RuntimeError("Falha ao preparar upload")
        relative = (response.json() or {}).get("url")
        if not relative:
            raise RuntimeError("URL de upload ausente")
        if relative.startswith("http://") or relative.startswith("https://"):
            return relative
        if relative.startswith("/storage/v1"):
            return f"{self.base_url}{relative}"
        prefix = relative if relative.startswith("/") else f"/{relative}"
        return f"{self.base_url}/storage/v1{prefix}"

    async def upload_pdf(self, path: str, content: bytes) -> None:
        encoded_path = quote(path, safe="/")
        headers = {**self.auth_headers, "Content-Type": "application/pdf", "x-upsert": "false"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/storage/v1/object/{PDF_BUCKET}/{encoded_path}",
                headers=headers, content=content,
            )
        if response.status_code >= 300:
            logger.error("Storage upload error %s: %s", response.status_code, response.text[:500])
            raise RuntimeError("Falha ao armazenar PDF")

    async def download_pdf(self, path: str) -> bytes:
        encoded_path = quote(path, safe="/")
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{self.base_url}/storage/v1/object/authenticated/{PDF_BUCKET}/{encoded_path}",
                headers=self.auth_headers,
            )
        if response.status_code >= 300:
            raise RuntimeError("Falha ao obter PDF")
        return response.content

    async def delete_pdf(self, path: str) -> None:
        try:
            await self._request(
                "DELETE", f"/storage/v1/object/{PDF_BUCKET}",
                json_body={"prefixes": [path]},
            )
        except Exception:
            logger.warning("Não foi possível remover PDF órfão: %s", path)
