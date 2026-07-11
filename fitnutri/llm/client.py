"""
FitNutri Local - Cliente DeepSeek API
Abstração para chamadas aos modelos Flash e Pro.
"""

import os
import time
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Cliente para API do DeepSeek.

    Suporta:
    - DeepSeek V4 Flash (rápido, baixo custo) → "deepseek-chat"
    - DeepSeek V4 Pro (análise profunda) → "deepseek-reasoner"
    """

    MODELS = {
        "flash": "deepseek-chat",
        "pro": "deepseek-reasoner",
    }

    def __init__(self, api_key: Optional[str] = None, timeout: int = 60):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY não encontrada. "
                "Configure no .env ou passe via parâmetro."
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com/v1",
            timeout=timeout,
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
        """Gera resposta do modelo DeepSeek com retry automático."""
        model_id = self.MODELS.get(modelo, self.MODELS["flash"])
        tentativa = 0

        while tentativa < max_retries:
            try:
                tentativa += 1
                logger.info(
                    f"🔄 Chamando DeepSeek {model_id} "
                    f"(tentativa {tentativa}/{max_retries})"
                )

                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperatura,
                    max_tokens=max_tokens,
                )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Resposta vazia da API")

                logger.info(f"✅ Resposta recebida ({len(content)} chars)")
                return content

            except Exception as e:
                logger.warning(f"❌ Tentativa {tentativa} falhou: {e}")
                if tentativa >= max_retries:
                    raise RuntimeError(
                        f"Falha após {max_retries} tentativas: {e}"
                    )
                delay = 2 ** (tentativa - 1)
                logger.info(f"⏳ Aguardando {delay}s antes de tentar novamente...")
                time.sleep(delay)

        raise RuntimeError("Falha inesperada no cliente DeepSeek")
