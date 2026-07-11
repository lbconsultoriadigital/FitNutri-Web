"""
FitNutri Local - Pipeline Engine
Orquestrador principal do fluxo de agentes.
"""

import logging
from typing import Optional
from pathlib import Path

from .models.schemas import ContextoPipeline, LaudoFinal
from .llm.client import DeepSeekClient
from .agents import (
    AgenteTriagem,
    AgenteExames,
    AgenteSuplementacao,
    AgenteNutricionista,
    AgenteEducadorFisico,
    AgenteOrquestrador,
)
from .storage.file_store import FileStore
from .output.generator import LaudoGenerator

logger = logging.getLogger(__name__)


class PipelineFitNutri:
    """Orquestrador principal do pipeline de agentes.

    Gerencia o fluxo sequencial dos 6 agentes, mantendo o contexto
    compartilhado e salvando outputs intermediários.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        storage_dir: str = "./pacientes",
        parar_em_erro: bool = True,
    ):
        self.llm = DeepSeekClient(api_key=api_key)
        self.store = FileStore(storage_dir)
        self.generator = LaudoGenerator()
        self.parar_em_erro = parar_em_erro

        # Pipeline de agentes (a ordem IMPORTA!)
        self.agentes = [
            AgenteTriagem(self.llm),             # 📋 Etapa 1
            AgenteExames(self.llm),              # 🔬 Etapa 2
            AgenteSuplementacao(self.llm),       # 💊 Etapa 3
            AgenteNutricionista(self.llm),       # 🥗 Etapa 4
            AgenteEducadorFisico(self.llm),      # 🏋️ Etapa 5
            AgenteOrquestrador(self.llm),        # 👑 Etapa 6
        ]

    def executar(
        self,
        dados_paciente: dict,
        paciente_slug: Optional[str] = None,
    ) -> tuple[LaudoFinal, str, str, Path]:
        """Executa o pipeline completo para um paciente.

        Args:
            dados_paciente: Dados do paciente (input.json ou dict manual)
            paciente_slug: Slug opcional (gerado automaticamente se não informado)

        Returns:
            tuple: (LaudoFinal, conteudo_markdown, conteudo_html, diretorio_paciente)
        """
        # Inicializa contexto com dados do paciente
        contexto = ContextoPipeline()
        contexto._dados_entrada = dados_paciente  # type: ignore
        nome_paciente = dados_paciente.get("nome", "paciente")
        slug = paciente_slug or self.store.criar_slug(nome_paciente)
        paciente_dir = self.store.criar_diretorio_paciente(slug)

        # Salva input original
        self.store.salvar_input(paciente_dir, dados_paciente)

        logger.info(f"\n{'='*60}")
        logger.info(f"🏥 INICIANDO ATENDIMENTO — {nome_paciente}")
        logger.info(f"📁 Diretório: {paciente_dir}")
        logger.info(f"{'='*60}")

        # --- Pipeline principal ---
        for i, agente in enumerate(self.agentes):
            etapa = i + 1
            logger.info(f"\n{'─'*50}")
            logger.info(f"[{etapa}/6] ▶️ {agente.nome}")
            logger.info(f"   Modelo: {agente.modelo.upper()}")
            logger.info(f"{'─'*50}")

            try:
                contexto = agente.executar(contexto)

                # Salva etapa
                self.store.salvar_etapa(paciente_dir, etapa, agente.nome, contexto)

                logger.info(f"   ✅ {agente.nome} concluído")

            except Exception as e:
                erro_msg = f"❌ ERRO na etapa {etapa} ({agente.nome}): {e}"
                logger.error(erro_msg)
                contexto.erros.append(erro_msg)
                if self.parar_em_erro:
                    logger.error("⛔ Pipeline interrompido — parar_em_erro=true")
                    raise RuntimeError(erro_msg) from e
                else:
                    logger.warning("⚠️ Continuando pipeline apesar do erro...")

        # --- Geração do laudo final ---
        logger.info(f"\n{'─'*50}")
        logger.info(f"[✓] 📄 Gerando laudo final...")
        logger.info(f"{'─'*50}")

        laudo, conteudo_md, conteudo_html = self.generator.gerar_laudo(contexto)
        self.store.salvar_laudo(paciente_dir, laudo, conteudo_md, conteudo_html)

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ ATENDIMENTO FINALIZADO — {nome_paciente}")
        logger.info(f"📁 Arquivos em: {paciente_dir}/")
        logger.info(f"   ├── laudo-final.md")
        logger.info(f"   └── laudo-final.html")
        logger.info(f"{'='*60}")

        return laudo, conteudo_md, conteudo_html, paciente_dir
