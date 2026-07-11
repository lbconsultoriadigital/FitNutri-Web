"""Cliente DeepSeek com JSON mode, modelos configuráveis e retry controlado."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Cliente compatível com a API OpenAI da DeepSeek.

    Os IDs dos modelos ficam em variáveis de ambiente para evitar dependência
    de aliases que possam mudar no provedor.
    """

    @property
    def models(self) -> dict[str, str]:
        return {
            "flash": os.getenv("DEEPSEEK_MODEL_FLASH", "deepseek-chat"),
            "pro": os.getenv("DEEPSEEK_MODEL_PRO", "deepseek-reasoner"),
        }

    def __init__(self, api_key: Optional[str] = None, timeout: int | None = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY não configurada")

        request_timeout = timeout or int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "180"))
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            timeout=request_timeout,
            max_retries=0,
        )

    def gerar(
        self,
        system_prompt: str,
        user_message: str,
        modelo: str = "flash",
        temperatura: float = 0.3,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> str:
        """Gera JSON válido e repete apenas falhas transitórias."""
        model_id = self.models.get(modelo, self.models["flash"])
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Chamando modelo %s (%s/%s)", model_id, attempt, max_retries)
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperatura,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Resposta vazia da API")

                json.loads(content)
                return content
            except Exception as exc:
                last_error = exc
                logger.warning("Falha no modelo %s: %s", model_id, exc)
                if attempt == max_retries:
                    break
                delay = min(8.0, (2 ** (attempt - 1)) + random.random())
                time.sleep(delay)

        raise RuntimeError(f"Falha após {max_retries} tentativas") from last_error
