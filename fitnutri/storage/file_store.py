"""
FitNutri Local - Sistema de Armazenamento
Gerencia diretórios e arquivos dos pacientes.
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from ..models.schemas import (
    ContextoPipeline, Anamnese, AnaliseExames,
    ProtocoloSuplementacao, PlanoAlimentar, PlanoTreino, LaudoFinal,
)

logger = logging.getLogger(__name__)


class FileStore:
    """Gerencia o armazenamento de dados dos pacientes no sistema de arquivos.

    Estrutura:
    pacientes/{slug}/
        input.json
        01-ficha_anamnese.md
        01-ficha_anamnese.json
        02-relatorio_exames.md
        02-relatorio_exames.json
        03-protocolo_suplementacao.md
        03-protocolo_suplementacao.json
        04-plano_alimentar.md
        04-plano_alimentar.json
        05-planilha_treino.md
        05-planilha_treino.json
        laudo-final.md
        laudo-final.json
        laudo-final.html
    """

    def __init__(self, diretorio_base: str = "./pacientes"):
        self.diretorio_base = Path(diretorio_base)
        self.diretorio_base.mkdir(parents=True, exist_ok=True)

    def criar_slug(self, nome: str) -> str:
        """Cria um slug único para o paciente baseado no nome e data."""
        nome_limpo = nome.lower().strip().replace(" ", "-")
        data = datetime.now().strftime("%Y-%m-%d")
        # Remove caracteres especiais
        nome_limpo = "".join(c for c in nome_limpo if c.isalnum() or c == "-")
        return f"{nome_limpo}-{data}"

    def criar_diretorio_paciente(self, paciente_slug: str) -> Path:
        """Cria o diretório do paciente e retorna o caminho."""
        caminho = self.diretorio_base / paciente_slug
        caminho.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Diretório criado: {caminho}")
        return caminho

    def salvar_input(self, paciente_dir: Path, dados: dict):
        """Salva o input original do paciente."""
        caminho = paciente_dir / "input.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 input.json salvo")

    def salvar_etapa(
        self,
        paciente_dir: Path,
        etapa_num: int,
        nome_agente: str,
        contexto: ContextoPipeline,
    ):
        """Salva o output de uma etapa do pipeline."""
        # Mapeia etapa → atributo do contexto
        etapa_map = {
            1: ("01-ficha_anamnese", "paciente"),
            2: ("02-relatorio_exames", "analise_exames"),
            3: ("03-protocolo_suplementacao", "protocolo_suplementacao"),
            4: ("04-plano_alimentar", "plano_alimentar"),
            5: ("05-planilha_treino", "plano_treino"),
            6: ("06-laudo_consolidado", "etapa_atual"),
        }

        prefixo, attr = etapa_map.get(etapa_num, (f"{etapa_num:02d}-etapa", None))
        if not attr:
            return

        dados = getattr(contexto, attr, None)
        if dados is None:
            return

        # Salva como JSON
        caminho_json = paciente_dir / f"{prefixo}.json"
        if hasattr(dados, "model_dump"):
            dados_dict = dados.model_dump()
        elif isinstance(dados, dict):
            dados_dict = dados
        else:
            dados_dict = {"valor": str(dados)}

        # Remove campos None para não poluir
        dados_dict = {k: v for k, v in dados_dict.items() if v is not None}

        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(dados_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 {prefixo}.json salvo")

    def salvar_relatorio_md(self, paciente_dir: Path, prefixo: str, titulo: str, conteudo: str):
        """Salva um relatório em formato Markdown."""
        caminho = paciente_dir / f"{prefixo}.md"
        cabecalho = f"# {titulo}\n\n"
        cabecalho += f"_Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n---\n\n"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(cabecalho + conteudo)
        logger.info(f"  💾 {prefixo}.md salvo")

    def salvar_laudo(self, paciente_dir: Path, laudo: LaudoFinal, conteudo_md: str, conteudo_html: str = ""):
        """Salva o laudo final em múltiplos formatos."""
        # JSON
        caminho_json = paciente_dir / "laudo-final.json"
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(laudo.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        # Markdown
        caminho_md = paciente_dir / "laudo-final.md"
        with open(caminho_md, "w", encoding="utf-8") as f:
            f.write(conteudo_md)

        # HTML
        if conteudo_html:
            caminho_html = paciente_dir / "laudo-final.html"
            with open(caminho_html, "w", encoding="utf-8") as f:
                f.write(conteudo_html)

        logger.info(f"  💾 Laudo salvo em {paciente_dir}/")
        logger.info(f"     ├── laudo-final.json")
        logger.info(f"     ├── laudo-final.md")
        if conteudo_html:
            logger.info(f"     └── laudo-final.html")

    def listar_pacientes(self) -> list[dict]:
        """Lista todos os pacientes atendidos."""
        pacientes = []
        if not self.diretorio_base.exists():
            return pacientes

        for item in self.diretorio_base.iterdir():
            if item.is_dir():
                laudo_path = item / "laudo-final.json"
                if laudo_path.exists():
                    try:
                        with open(laudo_path, "r", encoding="utf-8") as f:
                            laudo = json.load(f)
                        pacientes.append({
                            "slug": item.name,
                            "nome": laudo.get("paciente", item.name),
                            "data": laudo.get("data_geracao", ""),
                            "caminho": str(item),
                        })
                    except Exception:
                        pacientes.append({
                            "slug": item.name,
                            "nome": item.name,
                            "data": "",
                            "caminho": str(item),
                        })

        # Ordena por data (mais recente primeiro)
        pacientes.sort(key=lambda x: x.get("data", ""), reverse=True)
        return pacientes

    def carregar_input(self, caminho: str) -> dict:
        """Carrega dados de input de um arquivo JSON."""
        caminho_path = Path(caminho)
        if not caminho_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def limpar_paciente(self, paciente_slug: str):
        """Remove o diretório de um paciente."""
        caminho = self.diretorio_base / paciente_slug
        if caminho.exists():
            shutil.rmtree(caminho)
            logger.info(f"🗑️ Paciente removido: {paciente_slug}")
