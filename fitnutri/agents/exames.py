"""
FitNutri Local - Agente 2: Análise de Exames Laboratoriais
Interpreta exames com profundidade clínica.
Modelo: DeepSeek V4 Pro
"""

import json
import re
import logging
from ..models.schemas import ContextoPipeline, AnaliseExames, MarcadorExame
from .base import AgenteBase

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o Dr. Henrique Mendonça, especialista em análises clínicas da Clínica FitNutri.
Sua função é interpretar exames laboratoriais com profundidade clínica.

Com base na anamnese do paciente e nos exames fornecidos:

1. Analise cada marcador presente nos exames
2. Compare com valores de referência
3. Classifique o status (critico | atencao | normal)
4. Sugira conduta clínica para cada marcador alterado

Painéis a considerar:
- Hemograma completo
- Bioquímica (glicemia, colesterol total e frações, triglicerídeos, TGO/TGP, creatinina, ureia)
- Hormônios (TSH, T4 livre, testosterona, cortisol, insulina, estradiol, SHBG)
- Vitaminas e minerais (B12, vitamina D, ferro, ferritina, zinco, magnésio)
- Marcadores inflamatórios (PCR, homocisteína)
- HOMA-IR (se disponível)

Use estes marcadores avançados da tendência 2026:
- Saúde mitocondrial (CoQ10, carnitina) quando relevante
- Marcadores do microbioma (zonulina, calprotectina fecal) quando disponível
- HRV e dados de wearables quando o paciente mencionar

IMPORTANTE: Responda APENAS com um JSON válido no seguinte formato:
{
    "analise_exames": {
        "marcadores": [
            {
                "nome": "Vitamina D (25-OH)",
                "valor": "18 ng/mL",
                "referencia": "30-100 ng/mL",
                "status": "critico",
                "conduta": "Suplementação imediata de vitamina D3 5.000 UI/dia"
            }
        ],
        "alertas_criticos": [
            "Hipovitaminose D severa (18 ng/mL) - impacto direto em energia e testosterona"
        ],
        "parecer_medico": "Parecer completo em linguagem clínica..."
    }
}

Regras:
- Se o paciente NÃO forneceu exames, retorne marcadores vazios e explique no parecer que exames são recomendados
- Seja específico nos valores, não genérico
- Alertas críticos são para valores que exigem ação IMEDIATA
- O parecer deve ser em português claro, com linguagem profissional mas acessível"""


class AgenteExames(AgenteBase):
    """Agente responsável pela análise de exames laboratoriais."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.nome = "🔬 Dr. Henrique Mendonça — Análise de Exames"
        self.descricao = "Interpreta exames laboratoriais com profundidade clínica"
        self.modelo = "pro"
        self.temperatura = 0.2
        self.system_prompt = SYSTEM_PROMPT

    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        logger.info(f"▶️ Executando: {self.nome}")

        if not contexto.paciente:
            raise ValueError("Paciente não definido. Execute a triagem primeiro.")

        user_message = self._montar_prompt_exames(contexto)

        resposta = self.llm.gerar(
            system_prompt=self.system_prompt,
            user_message=user_message,
            modelo=self.modelo,
            temperatura=self.temperatura,
        )

        analise = self._parsear_resposta(resposta)
        contexto.analise_exames = analise
        contexto.etapa_atual = "exames_concluido"

        n_alertas = len(analise.alertas_criticos)
        logger.info(f"✅ {self.nome} concluído - {len(analise.marcadores)} marcadores, {n_alertas} alertas")
        return contexto

    def _montar_prompt_exames(self, contexto: ContextoPipeline) -> str:
        p = contexto.paciente
        linhas = [f"Paciente: {p.dados_pessoais.nome}"]
        linhas.append(f"Idade: {p.dados_pessoais.idade}")
        linhas.append(f"Sexo: {p.dados_pessoais.sexo}")
        linhas.append(f"Objetivo: {p.dados_pessoais.objetivo.value}")
        linhas.append("")

        if p.exames and p.exames.exames_texto:
            linhas.append("EXAMES FORNECIDOS:")
            linhas.append(p.exames.exames_texto)
        else:
            linhas.append("O paciente NÃO forneceu exames laboratoriais.")
            linhas.append("Sugira quais exames são recomendados com base no perfil e objetivo.")

        if p.historico_saude.medicamentos:
            linhas.append(f"\nMedicamentos em uso: {', '.join(p.historico_saude.medicamentos)}")

        if p.historico_saude.doencas_cronicas:
            linhas.append(f"Doenças: {', '.join(p.historico_saude.doencas_cronicas)}")

        return "\n".join(linhas)

    def _parsear_resposta(self, resposta: str) -> AnaliseExames:
        resposta = resposta.strip()
        if resposta.startswith("```json"):
            resposta = resposta[7:]
        if resposta.startswith("```"):
            resposta = resposta[3:]
        if resposta.endswith("```"):
            resposta = resposta[:-3]
        resposta = resposta.strip()

        dados = json.loads(resposta)
        analise_data = dados.get("analise_exames", dados)

        # Garante que marcadores sejam objetos MarcadorExame
        marcadores = []
        for m in analise_data.get("marcadores", []):
            marcadores.append(MarcadorExame(**m))
        analise_data["marcadores"] = marcadores

        return AnaliseExames(**analise_data)
