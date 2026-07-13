"""
FitNutri - Agente 1: Triagem & Anamnese.

A triagem é determinística: os dados já chegam estruturados e validados pela
API. Não há motivo para depender de uma resposta de LLM para apenas copiar os
campos do formulário para o contexto clínico.
"""

from __future__ import annotations

import logging
from typing import Any

from ..models.schemas import (
    Anamnese,
    ContextoPipeline,
    DadosPessoais,
    ExamesLaboratoriais,
    HabitosVida,
    HistoricoSaude,
    LocalTreinoEnum,
    NivelTreinoEnum,
    ObjetivoEnum,
    SexoEnum,
    TreinoAtual,
)
from .base import AgenteBase

logger = logging.getLogger(__name__)


class AgenteTriagem(AgenteBase):
    """Transforma o payload validado da API em uma anamnese tipada."""

    def __init__(self, llm_client):
        # Mantemos a assinatura comum dos agentes, embora esta etapa não use LLM.
        super().__init__(llm_client)
        self.nome = "📋 Triagem & Anamnese"
        self.descricao = "Organiza os dados estruturados do paciente"
        self.modelo = "deterministico"
        self.temperatura = 0.0
        self.system_prompt = ""

    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        logger.info("▶️ Executando: %s", self.nome)

        entrada = getattr(contexto, "_dados_entrada", None)
        if not isinstance(entrada, dict):
            if contexto.paciente:
                contexto.etapa_atual = "triagem_concluida"
                return contexto
            raise ValueError("Dados de entrada da triagem não foram fornecidos")

        anamnese = self._montar_anamnese(entrada)
        contexto.paciente = anamnese
        contexto.etapa_atual = "triagem_concluida"

        logger.info(
            "✅ %s concluído - Paciente: %s",
            self.nome,
            anamnese.dados_pessoais.nome,
        )
        return contexto

    def _montar_anamnese(self, entrada: dict[str, Any]) -> Anamnese:
        peso = self._float(entrada.get("peso_kg"))
        altura = self._float(entrada.get("altura_m"))
        imc = round(peso / (altura ** 2), 2) if peso > 0 and altura > 0 else None

        condicoes = self._lista(entrada.get("condicoes"))
        doencas = self._lista(entrada.get("doencas_cronicas"))
        doencas = self._deduplicar(doencas or condicoes)

        condicoes_especificas = self._deduplicar(condicoes)
        observacoes = str(entrada.get("obs") or "").strip()
        if observacoes:
            condicoes_especificas.append(f"Observações adicionais: {observacoes}")

        exames_texto = str(entrada.get("exames_texto") or "").strip()
        exames = ExamesLaboratoriais(
            exames_texto=exames_texto or None,
            data_exames=self._texto_ou_none(entrada.get("data_exames")),
        )

        return Anamnese(
            dados_pessoais=DadosPessoais(
                nome=str(entrada.get("nome") or "").strip(),
                idade=self._int(entrada.get("idade")),
                peso_kg=peso,
                altura_m=altura,
                sexo=self._enum(
                    SexoEnum,
                    entrada.get("sexo"),
                    SexoEnum.MASCULINO,
                ),
                profissao=str(entrada.get("profissao") or "").strip(),
                imc=imc,
                objetivo=self._enum(
                    ObjetivoEnum,
                    entrada.get("objetivo"),
                    ObjetivoEnum.SAUDE,
                ),
                objetivo_descricao=str(
                    entrada.get("objetivo_descricao") or ""
                ).strip(),
            ),
            historico_saude=HistoricoSaude(
                doencas_cronicas=doencas,
                cirurgias=self._lista(entrada.get("cirurgias")),
                medicamentos=self._lista(entrada.get("medicamentos")),
                alergias=self._lista(entrada.get("alergias")),
                condicoes_especificas=condicoes_especificas,
                historico_familiar=self._lista(
                    entrada.get("historico_familiar")
                ),
            ),
            habitos=HabitosVida(
                sono_horas=self._float(entrada.get("sono_horas")),
                sono_qualidade=str(
                    entrada.get("sono_qualidade") or "regular"
                ).strip(),
                estresse_nivel=str(
                    entrada.get("estresse_nivel") or "moderado"
                ).strip(),
                cafeina_diaria=str(
                    entrada.get("cafeina_diaria") or ""
                ).strip(),
                agua_litros=self._float(entrada.get("agua_litros")),
                alcool=str(entrada.get("alcool") or "nao").strip(),
                fumante=bool(entrada.get("fumante", False)),
            ),
            exames=exames,
            treino=TreinoAtual(
                frequencia_semanal=self._int(
                    entrada.get("frequencia_treino")
                ),
                tipo_treino=str(
                    entrada.get("tipo_treino") or ""
                ).strip(),
                tempo_pratica=self._enum(
                    NivelTreinoEnum,
                    entrada.get("nivel_treino"),
                    NivelTreinoEnum.INICIANTE,
                ),
                lesoes_atuais=self._lista(entrada.get("lesoes")),
                limitacoes=self._lista(entrada.get("limitacoes")),
                local_treino=self._enum(
                    LocalTreinoEnum,
                    entrada.get("local_treino"),
                    LocalTreinoEnum.ACADEMIA,
                ),
            ),
            preferencias_alimentares=self._lista(
                entrada.get("preferencias_alimentares")
            ),
            restricoes_alimentares=self._lista(
                entrada.get("restricoes_alimentares")
            ),
            suplementos_atuais=self._lista(
                entrada.get("suplementos_atuais")
            ),
        )

    @staticmethod
    def _lista(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = value.split(",")
        elif isinstance(value, (list, tuple, set)):
            items = value
        else:
            items = [value]
        return [
            str(item).strip()
            for item in items
            if str(item).strip()
        ]

    @staticmethod
    def _deduplicar(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    @staticmethod
    def _float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _texto_ou_none(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _enum(enum_class, value: Any, default):
        try:
            return enum_class(value)
        except (TypeError, ValueError):
            return default
