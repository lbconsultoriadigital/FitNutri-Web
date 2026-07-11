"""
FitNutri Local - Agente 3: Suplementação & Fármacos
Recomenda suplementação baseada em evidências, verifica interações.
Modelo: DeepSeek V4 Pro
"""

import json
import logging
from ..models.schemas import ContextoPipeline, ProtocoloSuplementacao, ItemSuplemento
from .base import AgenteBase

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é a Dra. Carolina Castro, especialista em nutracêutica clínica da Clínica FitNutri.
Sua função é recomendar suplementação baseada em EVIDÊNCIAS CIENTÍFICAS.

Com base na anamnese do paciente, exames laboratoriais e objetivos:

REGRAS CLÍNICAS OBRIGATÓRIAS (baseadas nas tendências 2026):

1. CREATINA: Evidência SÓLIDA. Dose padrão 5g/dia. Benefício real de 5-15% em força/potência.
   Indicar para: atletas, vegetarianos, idosos, déficit alimentar.
   Não precisa de ciclagem. Uso contínuo.

2. TERMOGÊNICOS: CONTRAINDICAR ativamente. Evidência NEGATIVA.
   Riscos cardiovasculares, gastrointestinais e tireoidianos superam qualquer benefício.

3. WHEY PROTEIN: É CONVENIÊNCIA, não necessidade.
   Só recomendar se ingestão proteica alimentar for insuficiente.

4. MULTIVITAMÍNICOS: Avaliar antes de recomendar. Risco de hipervitaminose (A, D, E, K).
   Só se deficiência diagnosticada em exames.

5. ÔMEGA-3: Individualizar. Benefício do nutriente ≠ benefício da suplementação.
   Dose: mínimo 400mg EPA + 300mg DHA.

6. VITAMINA D: Corrigir deficiência ANTES de suplementar.
   Dose ataque: 5.000 UI/dia (8 semanas) → Manutenção: 2.000 UI/dia.

7. Verificar INTERAÇÕES MEDICAMENTOSAS com todos os medicamentos que o paciente usa.

8. COLÁGENO: Evidência emergente para tipo II (articulações). Individualizar.

IMPORTANTE: Responda APENAS com um JSON válido no formato:
{
    "protocolo_suplementacao": {
        "suplementos": [
            {
                "nome": "Creatina Monoidratada",
                "dosagem": "5g/dia",
                "posologia": "Tomar diariamente no mesmo horário, diluída em água",
                "duracao": "Uso contínuo",
                "justificativa": "...",
                "evidencias": "..."
            }
        ],
        "interacoes": [],
        "contraindicacoes": [],
        "observacoes_gerais": "..."
    }
}"""


class AgenteSuplementacao(AgenteBase):
    """Agente responsável pelo protocolo de suplementação."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.nome = "💊 Dra. Carolina Castro — Suplementação"
        self.descricao = "Protocolo de suplementação baseado em evidências"
        self.modelo = "pro"
        self.temperatura = 0.3
        self.system_prompt = SYSTEM_PROMPT

    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        logger.info(f"▶️ Executando: {self.nome}")

        if not contexto.paciente:
            raise ValueError("Paciente não definido. Execute a triagem primeiro.")

        user_message = self._montar_prompt_suplementacao(contexto)

        resposta = self.llm.gerar(
            system_prompt=self.system_prompt,
            user_message=user_message,
            modelo=self.modelo,
            temperatura=self.temperatura,
        )

        protocolo = self._parsear_resposta(resposta)
        contexto.protocolo_suplementacao = protocolo
        contexto.etapa_atual = "suplementacao_concluido"

        logger.info(f"✅ {self.nome} concluído - {len(protocolo.suplementos)} suplementos recomendados")
        return contexto

    def _montar_prompt_suplementacao(self, contexto: ContextoPipeline) -> str:
        p = contexto.paciente
        partes = [f"Paciente: {p.dados_pessoais.nome}"]
        partes.append(f"Idade: {p.dados_pessoais.idade} | Peso: {p.dados_pessoais.peso_kg}kg")
        partes.append(f"Objetivo: {p.dados_pessoais.objetivo.value}")

        if p.suplementos_atuais:
            partes.append(f"\nSuplementos atuais: {', '.join(p.suplementos_atuais)}")
        if p.historico_saude.medicamentos:
            partes.append(f"Medicamentos: {', '.join(p.historico_saude.medicamentos)}")
        if p.historico_saude.alergias:
            partes.append(f"Alergias: {', '.join(p.historico_saude.alergias)}")
        if p.historico_saude.condicoes_especificas:
            partes.append(f"Condições: {', '.join(p.historico_saude.condicoes_especificas)}")

        if contexto.analise_exames:
            a = contexto.analise_exames
            partes.append("\nACHADOS DE EXAMES:")
            for m in a.marcadores:
                emoji = {"critico": "🔴", "atencao": "🟡", "normal": "🟢"}.get(m.status, "⚪")
                partes.append(f"{emoji} {m.nome}: {m.valor} (ref: {m.referencia})")

        return "\n".join(partes)

    def _parsear_resposta(self, resposta: str) -> ProtocoloSuplementacao:
        resposta = resposta.strip()
        if resposta.startswith("```json"):
            resposta = resposta[7:]
        if resposta.startswith("```"):
            resposta = resposta[3:]
        if resposta.endswith("```"):
            resposta = resposta[:-3]
        resposta = resposta.strip()

        dados = json.loads(resposta)
        proto_data = dados.get("protocolo_suplementacao", dados)

        suplementos = []
        for s in proto_data.get("suplementos", []):
            suplementos.append(ItemSuplemento(**s))
        proto_data["suplementos"] = suplementos

        return ProtocoloSuplementacao(**proto_data)
