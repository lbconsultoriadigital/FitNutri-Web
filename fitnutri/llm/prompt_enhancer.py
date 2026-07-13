"""
FitNutri - Melhorador de Prompts com Integração de PubMed
Enriquece os system prompts dos agentes com evidências científicas recentes e disclaimers.
"""

import logging
from typing import Dict, Optional
from .pubmed_integration import get_pubmed_client

logger = logging.getLogger(__name__)


DISCLAIMER_UNIVERSAL = """
⚠️ DISCLAIMER IMPORTANTE:
- As recomendações abaixo são SUGESTÕES baseadas em dados fornecidos e literatura científica.
- NÃO SUBSTITUEM diagnóstico médico profissional.
- O paciente DEVE ser atendido por profissional habilitado antes de qualquer ação clínica.
- A FitNutri funciona como plataforma de APOIO, não de substituição de atendimento médico presencial.
- Qualquer sintoma grave deve ser reportado imediatamente a um médico.
"""


class MelhoradorPrompts:
    """Enriquece prompts com contexto científico e disclaimers."""

    def __init__(self):
        try:
            self.pubmed = get_pubmed_client()
        except Exception as e:
            logger.warning(f"⚠️ Falha ao inicializar cliente PubMed: {e}")
            logger.warning("📋 PubMed desativado - prompts funcionarão sem enriquecimento de artigos")
            self.pubmed = None

    def melhorar_prompt_exames(self, prompt_original: str) -> str:
        """Adiciona contexto de PubMed ao prompt de análise de exames."""
        
        pubmed_refs = []
        if self.pubmed:
            try:
                pubmed_refs = self.pubmed.buscar_por_topico(
                    "laboratory markers inflammation metabolic health 2024 2025",
                    max_results=3
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar artigos PubMed: {e}")
                pubmed_refs = []

        refs_texto = ""
        if pubmed_refs:
            refs_texto = "\n## EVIDÊNCIA CIENTÍFICA RECENTE (PubMed)\n"
            for art in pubmed_refs:
                refs_texto += art.format_for_prompt()

        return f"""{prompt_original}

{refs_texto}

DIRETRIZES DE SEGURANÇA CRÍTICAS:
1. Se qualquer marcador estiver em intervalo CRÍTICO (ex: glicemia >250, hemoglobina <7):
   - Marque como RED FLAG 🔴
   - Oriente o paciente a buscar atendimento médico IMEDIATO
   - NÃO espere pela revisão, escale para o profissional responsável

2. Cite a fonte dos intervalos de referência (ex: "Segundo SBPC/ML 2024...")

3. Sempre termine com: "{DISCLAIMER_UNIVERSAL}"
"""

    def melhorar_prompt_suplementacao(self, prompt_original: str) -> str:
        """Adiciona contexto de PubMed ao prompt de suplementação."""
        
        pubmed_refs = []
        if self.pubmed:
            try:
                pubmed_refs = self.pubmed.buscar_por_topico(
                    "supplement efficacy safety evidence 2024 2025",
                    max_results=3
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar artigos PubMed: {e}")
                pubmed_refs = []

        refs_texto = ""
        if pubmed_refs:
            refs_texto = "\n## EVIDÊNCIA CIENTÍFICA RECENTE (PubMed)\n"
            for art in pubmed_refs:
                refs_texto += art.format_for_prompt()

        return f"""{prompt_original}

{refs_texto}

POSICIONAMENTO CRÍTICO SOBRE SUPLEMENTOS:
- CONTRAINDIQUE ATIVAMENTE qualquer termogênico, queimador de gordura ou estimulante em excesso
- Cite estudos científicos quando recomendar (ex: "Meta-análise de 2025 mostra que creatina...")
- NUNCA recomende suplementos sem justificativa baseada em marcadores bioquímicos ou deficiência
- Sempre termine com: "{DISCLAIMER_UNIVERSAL}"
"""

    def melhorar_prompt_nutricionista(self, prompt_original: str) -> str:
        """Adiciona contexto de PubMed ao prompt de nutrição."""
        
        pubmed_refs = []
        if self.pubmed:
            try:
                pubmed_refs = self.pubmed.buscar_por_topico(
                    "personalized nutrition macronutrients gut health 2024 2025",
                    max_results=3
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar artigos PubMed: {e}")
                pubmed_refs = []

        refs_texto = ""
        if pubmed_refs:
            refs_texto = "\n## EVIDÊNCIA CIENTÍFICA RECENTE (PubMed)\n"
            for art in pubmed_refs:
                refs_texto += art.format_for_prompt()

        return f"""{prompt_original}

{refs_texto}

PRINCÍPIOS CLÍNICOS CRÍTICOS:
1. Nunca prescrever dietas com <1200kcal (mulheres) ou <1500kcal (homens)
2. Sempre calcular TMB com fórmula Mifflin-St Jeor usando dados REAIS:
   - TMB = (10 × peso_kg) + (6.25 × altura_cm) - (5 × idade) + (5 se homem, -161 se mulher)
3. Priorizar saúde intestinal em TODOS os planos (fibras, prebióticos, probióticos)
4. Validar alergias/restrições ANTES de montar cardápio
5. Sempre termine com: "{DISCLAIMER_UNIVERSAL}"
"""

    def melhorar_prompt_treino(self, prompt_original: str) -> str:
        """Adiciona contexto de PubMed ao prompt de treino."""
        
        pubmed_refs = []
        if self.pubmed:
            try:
                pubmed_refs = self.pubmed.buscar_por_topico(
                    "resistance training periodization recovery HRV 2024 2025",
                    max_results=3
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar artigos PubMed: {e}")
                pubmed_refs = []

        refs_texto = ""
        if pubmed_refs:
            refs_texto = "\n## EVIDÊNCIA CIENTÍFICA RECENTE (PubMed)\n"
            for art in pubmed_refs:
                refs_texto += art.format_for_prompt()

        return f"""{prompt_original}

{refs_texto}

PRINCÍPIOS DE SEGURANÇA CRÍTICOS:
1. Se paciente reportar dor aguda, lesão recente ou cirurgia:
   - NÃO prescrever exercício sem avaliação médica
   - Marcar como RED FLAG e escalar

2. Para idosos (60+): Sempre começar com 2-3 semanas de adaptação com cargas leves
3. Verificar função cardiovascular ANTES de treinos de alta intensidade
4. Sempre terminus com: "{DISCLAIMER_UNIVERSAL}"
"""

    def melhorar_prompt_triagem(self, prompt_original: str) -> str:
        """Adiciona validações ao prompt de triagem."""
        
        return f"""{prompt_original}

VALIDAÇÕES OBRIGATÓRIAS ANTES DE FINALIZAR:
1. Peso: {1-300} kg
2. Altura: {0.5-2.5} m
3. IMC coerente: peso / altura² 
4. Idade: {14-120} anos
5. Se detectar sintomas graves (dor no peito, falta de ar, etc):
   - ESCALAR IMEDIATAMENTE
   - NÃO continuar para próxima etapa
   - Anexar flag RED FLAG 🔴

SEMPRE FINALIZAR COM: "{DISCLAIMER_UNIVERSAL}"
"""

    def melhorar_prompt_orquestrador(self, prompt_original: str) -> str:
        """Adiciona logica de escalação ao orquestrador."""
        
        return f"""{prompt_original}

LÓGICA DE ESCALAÇÃO DO ORQUESTRADOR:
1. Se qualquer etapa (1-5) retornar RED FLAG 🔴:
   - PAUSAR pipeline imediatamente
   - Enviar alerta para Felipe Leone (revisor)
   - NÃO gerar laudo até validação profissional

2. Se múltiplas etapas com RED FLAG 🟡:
   - Gerar laudo mas marcar como "REQUER VALIDAÇÃO URGENTE"
   - Destacar todos os alertas no laudo final

3. Sempre VALIDAR coerência entre etapas:
   - Triagem: paciente sedentário mas prescrito treino intenso? RED FLAG
   - Nutrição: calorias muito baixas para nível treino? RED FLAG
   - Suplementação: contraindicação com medicamento em uso? RED FLAG

4. Laudo final SEMPRE inclui:
   - Data de geração
   - Revisor profissional (Felipe Leone ou Daniel Rocha)
   - Data sugerida para reavaliação (30-90 dias)
   - Disclaimer completo

SEMPRE FINALIZAR COM: "{DISCLAIMER_UNIVERSAL}"
"""


class PromptEnhancerService:
    """Serviço que gerencia melhoramento de prompts para todos os agentes."""

    def __init__(self):
        self.melhorador = MelhoradorPrompts()

    def melhorar_todos_prompts(self, prompts_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Recebe dicionário de prompts e retorna versão melhorada.
        
        Args:
            prompts_dict: {
                "triagem": "prompt original...",
                "exames": "prompt original...",
                ...
            }
        
        Returns:
            Dicionário com prompts melhorados
        """
        prompts_melhorados = {}

        for agent_name, prompt in prompts_dict.items():
            if agent_name == "triagem":
                prompts_melhorados[agent_name] = self.melhorador.melhorar_prompt_triagem(prompt)
            elif agent_name == "exames":
                prompts_melhorados[agent_name] = self.melhorador.melhorar_prompt_exames(prompt)
            elif agent_name == "suplementacao":
                prompts_melhorados[agent_name] = self.melhorador.melhorar_prompt_suplementacao(prompt)
            elif agent_name == "nutricionista":
                prompts_melhorados[agent_name] = self.melhorador.melhorar_prompt_nutricionista(prompt)
            elif agent_name == "educador_fisico":
                prompts_melhorados[agent_name] = self.melhorador.melhorar_prompt_treino(prompt)
            elif agent_name == "orquestrador":
                prompts_melhorados[agent_name] = self.melhorador.melhorar_prompt_orquestrador(prompt)
            else:
                prompts_melhorados[agent_name] = prompt

            logger.info(f"✓ Prompt melhorado: {agent_name}")

        return prompts_melhorados


# Instância global
_service = None


def get_prompt_enhancer() -> PromptEnhancerService:
    """Retorna instância única do serviço."""
    global _service
    if _service is None:
        _service = PromptEnhancerService()
    return _service
