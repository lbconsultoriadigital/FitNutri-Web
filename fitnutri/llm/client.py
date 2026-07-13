"""Cliente DeepSeek com JSON mode, validação e recuperação controlada."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Cliente compatível com a API OpenAI da DeepSeek."""

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

        request_timeout = timeout or int(
            os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "180")
        )
        self.default_max_tokens = int(
            os.getenv("DEEPSEEK_MAX_TOKENS", "8192")
        )
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=os.getenv(
                "DEEPSEEK_BASE_URL",
                "https://api.deepseek.com/v1",
            ),
            timeout=request_timeout,
            max_retries=0,
        )

    def gerar(
        self,
        system_prompt: str,
        user_message: str,
        modelo: str = "flash",
        temperatura: float = 0.3,
        max_tokens: int | None = None,
        max_retries: int = 3,
    ) -> str:
        """Gera um objeto JSON completo, repetindo respostas inválidas."""
        model_id = self.models.get(modelo, self.models["flash"])
        base_tokens = max_tokens or self.default_max_tokens
        last_error: Exception | None = None
        correction = ""

        for attempt in range(1, max_retries + 1):
            token_budget = min(base_tokens + (attempt - 1) * 2048, 16384)
            effective_temperature = temperatura if attempt == 1 else 0.0
            effective_message = user_message + correction

            try:
                logger.info(
                    "Chamando modelo %s (%s/%s, max_tokens=%s)",
                    model_id,
                    attempt,
                    max_retries,
                    token_budget,
                )
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": effective_message},
                    ],
                    temperature=effective_temperature,
                    max_tokens=token_budget,
                    response_format={"type": "json_object"},
                )

                choice = response.choices[0]
                content = choice.message.content
                if not content:
                    raise ValueError("Resposta vazia da API")

                normalized = self._normalizar_json(content)
                self._validar_json(normalized)
                return normalized

            except json.JSONDecodeError as exc:
                last_error = exc
                finish_reason = locals().get("choice")
                finish_reason = (
                    getattr(finish_reason, "finish_reason", None)
                    if finish_reason
                    else None
                )
                logger.warning(
                    "JSON inválido do modelo %s: %s; finish_reason=%s; "
                    "posição=%s",
                    model_id,
                    exc.msg,
                    finish_reason,
                    exc.pos,
                )
                correction = (
                    "\n\nCORREÇÃO OBRIGATÓRIA PARA ESTA NOVA TENTATIVA:\n"
                    "- A resposta anterior não era um JSON válido.\n"
                    "- Responda com um único objeto JSON completo.\n"
                    "- Não use Markdown, comentários ou texto fora do JSON.\n"
                    "- Evite aspas duplas dentro dos textos; quando necessárias, "
                    "escape-as.\n"
                    "- Mantenha descrições concisas para concluir antes do limite.\n"
                    "- Feche todas as strings, listas e chaves."
                )
            except Exception as exc:
                last_error = exc
                logger.warning("Falha no modelo %s: %s", model_id, exc)

            if attempt < max_retries:
                delay = min(8.0, (2 ** (attempt - 1)) + random.random())
                time.sleep(delay)

        raise RuntimeError(
            f"Falha ao obter JSON válido após {max_retries} tentativas"
        ) from last_error

    @staticmethod
    def _normalizar_json(content: str) -> str:
        text = content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            text = text[first:last + 1]
        return text.strip()

    @staticmethod
    def _validar_json(content: str) -> None:
        try:
            json.loads(content)
        except json.JSONDecodeError:
            # Alguns provedores retornam quebras de linha literais dentro de
            # strings mesmo em JSON mode. strict=False aceita esses controles,
            # sem aceitar estruturas incompletas.
            json.loads(content, strict=False)
