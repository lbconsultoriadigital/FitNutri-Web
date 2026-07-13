"""
FitNutri Local - Agente 4: Nutricionista Clínico
Cria planos alimentares personalizados.
Modelo: DeepSeek V4 Flash
"""

import json
import logging
from ..models.schemas import ContextoPipeline, PlanoAlimentar, Refeicao
from .base import AgenteBase
from ..validation.validator import ValidadorFitNutri, AlertaSeveridade

logger = logging.getLogger(__name__)
validador = ValidadorFitNutri()

SYSTEM_PROMPT = """Você é Felipe Leone, nutricionista clínico e esportivo da Clínica FitNutri.
Crie planos alimentares PERSONALIZADOS, saborosos e baseados em evidências.

Com base nos dados do paciente, exames e protocolo de suplementação:

METODOLOGIA:
1. Calcular TMB (Mifflin-St Jeor):
   - Homens: 10 × peso(kg) + 6.25 × altura(cm) - 5 × idade + 5
   - Mulheres: 10 × peso(kg) + 6.25 × altura(cm) - 5 × idade - 161

2. Calcular GET = TMB × fator atividade:
   - Sedentário: 1.2 | Leve: 1.375 | Moderado: 1.55 | Intenso: 1.725

3. Ajuste calórico para objetivo:
   - Emagrecimento: GET - 400 a 500 kcal
   - Hipertrofia: GET + 300 a 500 kcal
   - Recomposição: GET - 200 a 400 kcal (déficit leve)
   - Performance: GET + 100 a 300 kcal

4. Distribuição de macronutrientes:
   - Proteínas: 1.6-2.2g/kg (hipertrofia: 2.0-2.4g/kg | emagrecimento: 2.0-2.4g/kg)
   - Gorduras: 0.8-1.2g/kg (mínimo 20-30% do VET)
   - Carboidratos: restante das calorias
   - Fibras: mínimo 25-30g/dia

ABORDAGEM ANTI-DIETA (tendência 2026):
- NUNCA proibir alimentos — focar em ADICIONAR densidade nutricional
- Food first: priorizar alimentação real sobre suplementos
- Saúde intestinal: incluir fibras solúveis, prebióticos, alimentos fermentados
- Mood Food: considerar relação alimentação-humor (cacau, magnésio, triptofano)
- Estabilidade glicêmica: combinar proteína + fibra + gordura boa
- GLP-1 natural: banana verde, aveia, leguminosas

DIRETRIZES DE SEGURANÇA CRÍTICAS:
1. NUNCA prescrever <1200 kcal (mulheres) ou <1500 kcal (homens)
   - Se objetivo de emagrecimento resultar em <1200/1500: MARQUE COMO RED FLAG
   - Sugerir aumento de déficit apenas com acompanhamento profissional

2. Verificar ALERGIAS E RESTRIÇÕES ANTES de montar cardápio
   - Se alergênico presente no plano: ERRO CRÍTICO 🔴

3. VALIDAR macronutrientes:
   - Proteína <1.6g/kg com objetivo hipertrofia: WARNING
   - Gordura <20% do VET: RED FLAG (saúde hormonal)

4. Se paciente com diabetes, síndrome metabólica ou pré-diabetes:
   - Priorizar índice glicêmico baixo
   - Combinar todos os carboidratos com proteína/fibra

5. Sempre finalizar com disclaimer e data de reavaliação (30 dias)

IMPORTANTE: Responda APENAS com um JSON válido no formato:
{
    "plano_alimentar": {
        "tmb_kcal": 0.0,
        "get_kcal": 0.0,
        "ajuste_kcal": 0.0,
        "proteinas_g": 0.0,
        "carboidratos_g": 0.0,
        "gorduras_g": 0.0,
        "fibras_g": 0.0,
        "meta_hidrica_l": 0.0,
        "refeicoes": [
            {
                "nome": "Café da Manhã",
                "horario": "07:30",
                "alimentos": ["3 ovos mexidos", "2 fatias pão integral", "150g mamão"],
                "observacoes": "Incluir chia"
            }
        ],
        "observacoes_gerais": "..."
    }
}"""


class AgenteNutricionista(AgenteBase):
    """Agente responsável pelo planejamento alimentar."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.nome = "🥗 Felipe Leone — Nutricionista Clínico"
        self.descricao = "Cria planos alimentares personalizados"
        self.modelo = "flash"
        self.temperatura = 0.4
        self.system_prompt = SYSTEM_PROMPT

    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        logger.info(f"▶️ Executando: {self.nome}")

        if not contexto.paciente:
            raise ValueError("Paciente não definido. Execute a triagem primeiro.")

        user_message = self._montar_prompt_nutricao(contexto)

        resposta = self.llm.gerar(
            system_prompt=self.system_prompt,
            user_message=user_message,
            modelo=self.modelo,
            temperatura=self.temperatura,
        )

        plano = self._parsear_resposta(resposta)
        contexto.plano_alimentar = plano
        
        # OPÇÃO A: Validação Minimal
        self._validar_plano_alimentar(plano, contexto)
        
        contexto.etapa_atual = "nutricao_concluido"

        logger.info(f"✅ {self.nome} concluído - GET: {plano.get_kcal:.0f} kcal")
        return contexto
    
    def _validar_plano_alimentar(self, plano: PlanoAlimentar, contexto: ContextoPipeline) -> None:
        """Valida plano alimentar contra regras de segurança."""
        logger.info("🔍 Validando plano alimentar...")
        
        paciente = contexto.paciente
        sexo = paciente.dados_pessoais.sexo.lower()
        
        # RED FLAGS: Calorias muito baixas
        min_kcal = 1200 if "feminino" in sexo else 1500
        if plano.ajuste_kcal < min_kcal:
            msg = f"RED FLAG: Ingestão calórica {plano.ajuste_kcal:.0f} kcal < mínimo recomendado ({min_kcal} kcal)"
            logger.error(f"🔴 {msg}")
            contexto.alertas_validacao.append(msg)
            contexto.escalacao_necessaria = True
            contexto.severidade_escalacao = AlertaSeveridade.VERMELHO.value
        
        # WARNING: Proteína baixa para hipertrofia
        proteina_por_kg = plano.proteinas_g / paciente.dados_pessoais.peso_kg
        objetivo = paciente.dados_pessoais.objetivo.value.lower()
        
        if "hipertrofia" in objetivo and proteina_por_kg < 1.6:
            msg = f"⚠️ Proteína baixa para hipertrofia: {proteina_por_kg:.2f}g/kg (recomendado 1.6-2.4g/kg)"
            logger.warning(msg)
            contexto.alertas_validacao.append(msg)
        
        # WARNING: Gordura muito baixa
        gordura_percent = (plano.gorduras_g * 9) / plano.ajuste_kcal * 100 if plano.ajuste_kcal > 0 else 0
        if gordura_percent < 20:
            msg = f"⚠️ Ingestão de gordura baixa: {gordura_percent:.1f}% (mínimo 20-30% para saúde hormonal)"
            logger.warning(msg)
            contexto.alertas_validacao.append(msg)
        
        # WARNING: Fibra baixa
        if plano.fibras_g < 25:
            msg = f"⚠️ Fibras abaixo do recomendado: {plano.fibras_g:.0f}g (mínimo 25-30g/dia)"
            logger.warning(msg)
            contexto.alertas_validacao.append(msg)
        
        # Validar restrições alimentares
        restricoes = paciente.restricoes_alimentares or []
        if restricoes:
            logger.info(f"📋 Verificando {len(restricoes)} restrições alimentares...")
            for refeicao in plano.refeicoes:
                for alimento in refeicao.alimentos:
                    for restricao in restricoes:
                        if restricao.lower() in alimento.lower():
                            msg = f"ERRO: Alimento contraindicado '{alimento}' na refeição '{refeicao.nome}' (paciente alérgico a '{restricao}')"
                            logger.error(f"🔴 {msg}")
                            contexto.alertas_validacao.append(msg)
                            contexto.escalacao_necessaria = True
                            contexto.severidade_escalacao = AlertaSeveridade.VERMELHO.value

    def _montar_prompt_nutricao(self, contexto: ContextoPipeline) -> str:
        p = contexto.paciente
        partes = [f"Paciente: {p.dados_pessoais.nome}"]
        partes.append(f"Idade: {p.dados_pessoais.idade} | Peso: {p.dados_pessoais.peso_kg}kg | Altura: {p.dados_pessoais.altura_m}m")
        partes.append(f"Sexo: {p.dados_pessoais.sexo} | Profissão: {p.dados_pessoais.profissao}")
        partes.append(f"Objetivo: {p.dados_pessoais.objetivo.value} - {p.dados_pessoais.objetivo_descricao}")

        partes.append(f"\nDados de treino: {p.treino.frequencia_semanal}x/semana - {p.treino.tipo_treino}")
        partes.append(f"Nível: {p.treino.tempo_pratica} | Local: {p.treino.local_treino}")

        if p.preferencias_alimentares:
            partes.append(f"\nPreferências: {', '.join(p.preferencias_alimentares)}")
        if p.restricoes_alimentares:
            partes.append(f"Restrições: {', '.join(p.restricoes_alimentares)}")

        partes.append(f"\nSono: {p.habitos.sono_horas}h/dia ({p.habitos.sono_qualidade})")
        partes.append(f"Estresse: {p.habitos.estresse_nivel}")

        if contexto.analise_exames:
            a = contexto.analise_exames
            partes.append("\nACHADOS IMPORTANTES DOS EXAMES:")
            for m in a.marcadores:
                if m.status in ("critico", "atencao"):
                    partes.append(f"⚠️ {m.nome}: {m.valor} - {m.conduta}")

        if contexto.protocolo_suplementacao:
            s = contexto.protocolo_suplementacao
            partes.append("\nSUPLEMENTAÇÃO PRESCRITA:")
            for sup in s.suplementos:
                partes.append(f"- {sup.nome}: {sup.dosagem}")

        return "\n".join(partes)

    def _parsear_resposta(self, resposta: str) -> PlanoAlimentar:
        resposta = resposta.strip()
        if resposta.startswith("```json"):
            resposta = resposta[7:]
        if resposta.startswith("```"):
            resposta = resposta[3:]
        if resposta.endswith("```"):
            resposta = resposta[:-3]
        resposta = resposta.strip()

        dados = json.loads(resposta)
        plano_data = dados.get("plano_alimentar", dados)

        refeicoes = []
        for r in plano_data.get("refeicoes", []):
            refeicoes.append(Refeicao(**r))
        plano_data["refeicoes"] = refeicoes

        return PlanoAlimentar(**plano_data)
