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
from ..validation.validator import ValidadorFitNutri, AlertaSeveridade, SistemaEscalacao
from ..llm.prompt_enhancer import get_prompt_enhancer

logger = logging.getLogger(__name__)
validador = ValidadorFitNutri()
escalacao = SistemaEscalacao()

try:
    prompt_enhancer = get_prompt_enhancer()
except Exception as e:
    logger.warning(f"⚠️ Falha ao inicializar PromptEnhancer: {e}")
    prompt_enhancer = None

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

DIRETRIZES DE SEGURANÇA CRÍTICAS:
1. RED FLAGS CLÍNICAS OBRIGATÓRIAS - se detectar, MARQUE IMEDIATAMENTE:
   - Glicemia >250 mg/dL ou <50 mg/dL → EMERGÊNCIA 🔴
   - Hemoglobina <7 g/dL → EMERGÊNCIA 🔴
   - Hemoglobina <6 g/dL → EMERGÊNCIA CRÍTICA 🚨
   - Creatinina >3.0 mg/dL → FALÊNCIA RENAL 🔴
   - TSH >10 mIU/L → HIPOTIREOIDISMO SEVERO
   - Pressão Arterial >180/120 mmHg → RISCO DE AVC 🔴

2. Sempre cite as FONTES e DIRETRIZES:
   - "Segundo as recomendações SBPC/ML 2024..."
   - "Meta-análise de 2025 mostra que..."

3. NUNCA recomende mudanças de medicação. Quando houver contraindicação:
   - Marque como RED FLAG
   - Escalação obrigatória para médico prescritivo

4. Se paciente SEM exames:
   - Recomende painel específico para o objetivo/idade
   - Não adivinhe valores

5. Sempre finalizar com disclaimer de responsabilidade profissional

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
        
        if prompt_enhancer:
            try:
                self.system_prompt = prompt_enhancer.melhorador.melhorar_prompt_exames(SYSTEM_PROMPT)
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível enriquecer prompt com PubMed: {e}")
                logger.warning("📋 Usando prompt padrão sem enriquecimento")
                self.system_prompt = SYSTEM_PROMPT
        else:
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
        
        # OPÇÃO A: Validação Minimal + RED FLAGS
        self._validar_exames(analise, contexto)
        
        contexto.etapa_atual = "exames_concluido"

        n_alertas = len(analise.alertas_criticos)
        logger.info(f"✅ {self.nome} concluído - {len(analise.marcadores)} marcadores, {n_alertas} alertas")
        return contexto
    
    def _validar_exames(self, analise: AnaliseExames, contexto: ContextoPipeline) -> None:
        """Valida exames e detecta red flags críticas."""
        logger.info("🔍 Validando resultados de exames...")
        
        # Extrair valores dos marcadores para validação
        exames_dict = {}
        for marcador in analise.marcadores:
            nome_lower = marcador.nome.lower()
            valor_str = str(marcador.valor).replace(" mg/dL", "").replace(" ng/mL", "").replace(" g/dL", "")
            try:
                exames_dict[nome_lower] = float(valor_str)
            except ValueError:
                pass
        
        # Validar exames contra red flags
        valido_exames, erros_exames, red_flags = validador.validar_exames(exames_dict)
        
        if red_flags:
            logger.error(f"🚨 RED FLAGS DETECTADAS! Total: {len(red_flags)}")
            for flag in red_flags:
                logger.error(f"   🔴 {flag['marcador']}: {flag['recomendacao']}")
                contexto.alertas_validacao.append(flag['recomendacao'])
            
            # Determinar necessidade de escalação
            necessita_escalacao, severidade, msg = escalacao.avaliar_necessidade_escalacao(
                {"paciente_nome": contexto.paciente.dados_pessoais.nome},
                red_flags_exames=red_flags
            )
            
            if necessita_escalacao:
                logger.error(f"⚠️ ESCALAÇÃO NECESSÁRIA - Severidade: {severidade.value}")
                contexto.escalacao_necessaria = True
                contexto.severidade_escalacao = severidade.value
                contexto.alertas_validacao.append(msg)
        
        # Validar alertas já identificados pelo LLM
        if analise.alertas_criticos:
            for alerta in analise.alertas_criticos:
                logger.warning(f"⚠️ Alerta do LLM: {alerta}")
                if not any(alerta in a for a in contexto.alertas_validacao):
                    contexto.alertas_validacao.append(alerta)

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
