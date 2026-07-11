"""
FitNutri Local - Agente 6: Orquestrador Final
Consolida todo o trabalho dos especialistas em um laudo final completo.
Modelo: DeepSeek V4 Pro
"""

import json
import logging
from datetime import datetime
from ..models.schemas import ContextoPipeline, LaudoFinal
from .base import AgenteBase

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o Orquestrador Clínico Master da Clínica FitNutri.
Sua função é CONSOLIDAR todo o trabalho dos especialistas em um laudo final completo, profissional e acolhedor.

Você receberá o contexto COMPLETO do paciente com:
1. ANAMNESE (dados pessoais, histórico, hábitos, exames, treino)
2. ANÁLISE DE EXAMES (marcadores, alertas, parecer do Dr. Henrique)
3. PROTOCOLO DE SUPLEMENTAÇÃO (doses, posologia, justificativas da Dra. Carolina)
4. PLANO ALIMENTAR (macros, cardápio, observações do nutricionista)
5. PLANO DE TREINO (periodização, exercícios do educador físico)

Com tudo isso, gere o laudo final com:

1. **SUMÁRIO EXECUTIVO** - Visão geral do caso em 3-5 linhas
2. **DADOS DO PACIENTE** - Tabela resumo dos dados pessoais e IMC
3. **ANÁLISE DE EXAMES** - Tabela de marcadores com status e conduta
4. **PROTOCOLO DE SUPLEMENTAÇÃO** - Cada suplemento com dose, posologia e justificativa
5. **PLANO ALIMENTAR** - Cálculos metabólicos, distribuição de macros, cardápio completo
6. **PLANO DE TREINO** - Estrutura semanal, cada dia com exercícios
7. **RECOMENDAÇÕES GERAIS** - Orientações finais
8. **PRÓXIMOS PASSOS** - Ações que o paciente deve tomar

TOM: Profissional, acolhedor, técnico mas acessível. Linguagem clara.

IMPORTANTE: Responda APENAS com um JSON válido no formato:
{
    "laudo_final": {
        "paciente": "Nome Completo",
        "data_geracao": "2026-07-03T12:00:00",
        "sumario_executivo": "Paciente... texto completo do sumário...",
        "recomendacoes_gerais": [],
        "proximos_passos": []
    }
}

OBS: Os campos anamnese, analise_exames, protocolo_suplementacao, plano_alimentar e plano_treino
já estão preenchidos no contexto. Seu foco é GERAR o sumário executivo, recomendações e próximos passos,
além de garantir que o laudo completo esteja coeso e bem formatado."""


class AgenteOrquestrador(AgenteBase):
    """Agente responsável por consolidar o laudo final."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.nome = "👑 Orquestrador Clínico — Consolidação Final"
        self.descricao = "Consolida o laudo multidisciplinar completo"
        self.modelo = "pro"
        self.temperatura = 0.3
        self.system_prompt = SYSTEM_PROMPT

    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        logger.info(f"▶️ Executando: {self.nome}")

        if not contexto.paciente:
            raise ValueError("Paciente não definido. Execute a triagem primeiro.")

        user_message = self._montar_prompt_consolidacao(contexto)

        resposta = self.llm.gerar(
            system_prompt=self.system_prompt,
            user_message=user_message,
            modelo=self.modelo,
            temperatura=self.temperatura,
        )

        laudo_data = self._parsear_resposta(resposta)

        # Cria o LaudoFinal completo com todos os dados consolidados
        laudo = LaudoFinal(
            paciente=laudo_data.get("paciente", contexto.paciente.dados_pessoais.nome),
            data_geracao=datetime.now(),
            sumario_executivo=laudo_data.get("sumario_executivo", ""),
            anamnese=contexto.paciente,
            analise_exames=contexto.analise_exames,
            protocolo_suplementacao=contexto.protocolo_suplementacao,
            plano_alimentar=contexto.plano_alimentar,
            plano_treino=contexto.plano_treino,
            recomendacoes_gerais=laudo_data.get("recomendacoes_gerais", []),
            proximos_passos=laudo_data.get("proximos_passos", []),
        )

        # Armazena o laudo no contexto para o generator usar
        contexto.etapa_atual = "laudo_consolidado"

        logger.info(f"✅ {self.nome} concluído - Laudo final gerado para {laudo.paciente}")

        # Retorna o contexto E o laudo como atributo extra
        contexto.laudo_final = laudo  # type: ignore
        return contexto

    def _montar_prompt_consolidacao(self, contexto: ContextoPipeline) -> str:
        partes = ["## CONTEXTO COMPLETO DO PACIENTE PARA CONSOLIDAÇÃO DO LAUDO FINAL\n"]

        # 1. Dados do paciente
        p = contexto.paciente
        partes.append("### 1. DADOS DO PACIENTE")
        partes.append(json.dumps(p.dados_pessoais.model_dump(), indent=2, ensure_ascii=False))
        partes.append(f"Histórico de saúde: {json.dumps(p.historico_saude.model_dump(), indent=2, ensure_ascii=False)}")
        partes.append(f"Hábitos: {json.dumps(p.habitos.model_dump(), indent=2, ensure_ascii=False)}")
        partes.append(f"Treino atual: {json.dumps(p.treino.model_dump(), indent=2, ensure_ascii=False)}")
        if p.preferencias_alimentares:
            partes.append(f"Preferências alimentares: {', '.join(p.preferencias_alimentares)}")
        if p.restricoes_alimentares:
            partes.append(f"Restrições: {', '.join(p.restricoes_alimentares)}")
        partes.append("")

        # 2. Exames
        if contexto.analise_exames:
            partes.append("### 2. ANÁLISE DE EXAMES")
            partes.append(json.dumps(contexto.analise_exames.model_dump(), indent=2, ensure_ascii=False))
            partes.append("")

        # 3. Suplementação
        if contexto.protocolo_suplementacao:
            partes.append("### 3. PROTOCOLO DE SUPLEMENTAÇÃO")
            partes.append(json.dumps(contexto.protocolo_suplementacao.model_dump(), indent=2, ensure_ascii=False))
            partes.append("")

        # 4. Plano alimentar
        if contexto.plano_alimentar:
            partes.append("### 4. PLANO ALIMENTAR")
            partes.append(json.dumps(contexto.plano_alimentar.model_dump(), indent=2, ensure_ascii=False))
            partes.append("")

        # 5. Plano de treino
        if contexto.plano_treino:
            partes.append("### 5. PLANO DE TREINO")
            partes.append(json.dumps(contexto.plano_treino.model_dump(), indent=2, ensure_ascii=False))
            partes.append("")

        partes.append("\nCom base em TODOS os dados acima, gere o sumário executivo, recomendações e próximos passos.")
        partes.append("O laudo será montado com todas as seções preenchidas pelos especialistas.")
        partes.append("Seu foco é dar coesão, tom profissional e garantir que nada importante foi perdido.")

        return "\n".join(partes)

    def _parsear_resposta(self, resposta: str) -> dict:
        resposta = resposta.strip()
        if resposta.startswith("```json"):
            resposta = resposta[7:]
        if resposta.startswith("```"):
            resposta = resposta[3:]
        if resposta.endswith("```"):
            resposta = resposta[:-3]
        resposta = resposta.strip()

        dados = json.loads(resposta)
        return dados.get("laudo_final", dados)
