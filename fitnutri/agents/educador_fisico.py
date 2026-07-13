"""
FitNutri Local - Agente 5: Educador Físico
Cria treinos personalizados com periodização.
Modelo: DeepSeek V4 Flash
"""

import json
import logging
from ..models.schemas import ContextoPipeline, PlanoTreino, DiaTreino
from .base import AgenteBase
from ..validation.validator import ValidadorFitNutri, AlertaSeveridade
from ..llm.prompt_enhancer import get_prompt_enhancer

logger = logging.getLogger(__name__)
validador = ValidadorFitNutri()
prompt_enhancer = get_prompt_enhancer()

SYSTEM_PROMPT = """Você é Daniel Rocha, educador físico especialista em periodização de treinos da Clínica FitNutri.
Desenhe planilhas de treino PERSONALIZADAS baseadas no perfil do paciente.

Com base nos dados do paciente, exames e plano alimentar:

DIRETRIZES TÉCNICAS:
- Força como base para TODOS os perfis e objetivos
- Periodização de acordo com o nível (iniciante/intermediário/avançado)
- Estruturas disponíveis: PPL (Push/Pull/Legs), ABCD, Upper/Lower, Fullbody
- Incluir aquecimento clínico (mobilidade + ativação) em todo treino
- Adaptar para limitações e lesões do paciente
- Considerar dados de HRV e recuperação quando disponíveis
- Treino híbrido: prescrever para academia + casa quando relevante

REGRAS POR OBJETIVO:
- HIPERTROFIA: 8-12 reps, 3-4 séries, 60-90s descanso
- EMAGRECIMENTO: 10-15 reps, 3-4 séries, 30-60s descanso, exercícios compostos
- FORÇA: 4-6 reps, 4-5 séries, 120-180s descanso
- SAÚDE: 10-15 reps, 2-3 séries, 60s descanso, foco em mobilidade

TENDÊNCIAS 2026 PARA INCORPORAR:
- HRV (Heart Rate Variability) como métrica de recuperação
- Benefícios do treino para SAÚDE MENTAL (comunicar isso ao paciente)
- Se for idoso (60+): usar "envelhecimento ativo", nunca "terceira idade"
- Comunidade: sugerir grupos de treino ou desafios
- Treino funcional 2.0: baseado em estilo de vida

DIRETRIZES DE SEGURANÇA CRÍTICAS:
1. LESÕES E LIMITAÇÕES CONHECIDAS:
   - Se paciente reporta lesão aguda ou cirurgia recente (<3 meses):
     MARQUE COMO RED FLAG e NÃO prescrever exercício sem avaliação médica
   - Se limitação existente: ADAPTAR exercício, NÃO evitar completamente

2. IDOSOS (60+):
   - SEMPRE começar com 2-3 semanas de adaptação com cargas LEVES
   - Priorizar equilíbrio, propriocepção e força funcional
   - Evitar movimentos rápidos ou explosivos inicialmente

3. VERIFICAR FUNÇÃO CARDIOVASCULAR:
   - Se exame mostra problemas cardíacos: NÃO prescrever HIIT ou treino de alta intensidade
   - Marcar como RED FLAG se pressão arterial sistólica >180 mmHg

4. Se paciente não aceitou suplementação recomendada (por alergia/restrição):
   - Ajustar expectativa de ganho muscular no treino

5. Sempre finalizar com disclaimer: "Este plano requer avaliação profissional antes da execução"

IMPORTANTE: Responda APENAS com um JSON válido no formato:
{
    "plano_treino": {
        "frequencia_semanal": 4,
        "estrutura": "PPL",
        "dias_treino": [
            {
                "dia": "Segunda-feira",
                "foco": "Peito, Ombros e Tríceps",
                "exercicios": [
                    "Supino reto: 4×8-10",
                    "Desenvolvimento halteres: 3×10-12",
                    "Elevação lateral: 4×12-15",
                    "Tríceps testa: 3×10-12"
                ]
            }
        ],
        "aquecimento": "5 min mobilidade de ombro + ativação de core",
        "observacoes": []
    }
}"""


class AgenteEducadorFisico(AgenteBase):
    """Agente responsável pelo planejamento de treinos."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.nome = "🏋️ Daniel Rocha — Educador Físico"
        self.descricao = "Cria planilhas de treino personalizadas"
        self.modelo = "flash"
        self.temperatura = 0.4
        try:
            self.system_prompt = prompt_enhancer.melhorador.melhorar_prompt_treino(SYSTEM_PROMPT)
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível enriquecer prompt com PubMed: {e}")
            logger.warning("📋 Usando prompt padrão sem enriquecimento")
            self.system_prompt = SYSTEM_PROMPT

    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        logger.info(f"▶️ Executando: {self.nome}")

        if not contexto.paciente:
            raise ValueError("Paciente não definido. Execute a triagem primeiro.")

        user_message = self._montar_prompt_treino(contexto)

        resposta = self.llm.gerar(
            system_prompt=self.system_prompt,
            user_message=user_message,
            modelo=self.modelo,
            temperatura=self.temperatura,
        )

        plano_treino = self._parsear_resposta(resposta)
        contexto.plano_treino = plano_treino
        
        # OPÇÃO A: Validação Minimal
        self._validar_plano_treino(plano_treino, contexto)
        
        contexto.etapa_atual = "treino_concluido"

        logger.info(f"✅ {self.nome} concluído - {plano_treino.frequencia_semanal}x/semana ({plano_treino.estrutura})")
        return contexto
    
    def _validar_plano_treino(self, plano_treino: PlanoTreino, contexto: ContextoPipeline) -> None:
        """Valida plano de treino contra limitações e contraindições."""
        logger.info("🔍 Validando plano de treino...")
        
        paciente = contexto.paciente
        idade = paciente.dados_pessoais.idade
        lesoes = paciente.treino.lesoes_atuais or []
        limitacoes = paciente.treino.limitacoes or []
        
        # RED FLAG: Lesão aguda sem avaliação médica
        if lesoes:
            logger.error(f"🔴 LESÕES DETECTADAS: {', '.join(lesoes)}")
            msg = f"RED FLAG: Paciente com lesão(ões). Treino requer avaliação médica presencial."
            contexto.alertas_validacao.append(msg)
            contexto.escalacao_necessaria = True
            contexto.severidade_escalacao = AlertaSeveridade.VERMELHO.value
        
        # WARNING: Idosos precisam de introdução gradual
        if idade >= 60:
            logger.warning(f"⚠️ Paciente idoso ({idade} anos). Recomenda-se período de adaptação de 2-3 semanas.")
            contexto.alertas_validacao.append(f"Paciente idoso ({idade}). Começar com cargas leves e progressão gradual.")
        
        # Check exames para contraindições cardiovasculares
        if contexto.analise_exames:
            for marcador in contexto.analise_exames.marcadores:
                if "pressão" in marcador.nome.lower() and "sistólica" in marcador.nome.lower():
                    try:
                        valor = float(str(marcador.valor).split("/")[0])
                        if valor > 180:
                            msg = "RED FLAG: Pressão arterial elevada (>180). NÃO prescrever HIIT ou alta intensidade."
                            logger.error(f"🔴 {msg}")
                            contexto.alertas_validacao.append(msg)
                            contexto.escalacao_necessaria = True
                            contexto.severidade_escalacao = AlertaSeveridade.VERMELHO.value
                    except (ValueError, IndexError):
                        pass
        
        # WARNING: Limitações reportadas
        if limitacoes:
            logger.warning(f"⚠️ LIMITAÇÕES: {', '.join(limitacoes)}")
            contexto.alertas_validacao.append(f"Limitações presentes - treino adaptado: {', '.join(limitacoes)}")

    def _montar_prompt_treino(self, contexto: ContextoPipeline) -> str:
        p = contexto.paciente
        partes = [f"Paciente: {p.dados_pessoais.nome}"]
        partes.append(f"Idade: {p.dados_pessoais.idade} | Peso: {p.dados_pessoais.peso_kg}kg | Altura: {p.dados_pessoais.altura_m}m")
        partes.append(f"Objetivo: {p.dados_pessoais.objetivo.value} - {p.dados_pessoais.objetivo_descricao}")
        partes.append(f"Profissão: {p.dados_pessoais.profissao}")

        partes.append(f"\nTreino atual: {p.treino.frequencia_semanal}x/semana")
        partes.append(f"Tipo: {p.treino.tipo_treino}")
        partes.append(f"Nível: {p.treino.tempo_pratica}")
        partes.append(f"Local: {p.treino.local_treino}")

        if p.treino.lesoes_atuais:
            partes.append(f"Lesões: {', '.join(p.treino.lesoes_atuais)}")
        if p.treino.limitacoes:
            partes.append(f"Limitações: {', '.join(p.treino.limitacoes)}")

        partes.append(f"\nSono: {p.habitos.sono_horas}h/dia ({p.habitos.sono_qualidade})")
        partes.append(f"Estresse: {p.habitos.estresse_nivel}")

        if contexto.analise_exames:
            a = contexto.analise_exames
            for m in a.marcadores:
                if m.status in ("critico", "atencao"):
                    partes.append(f"\n⚠️ Exame: {m.nome}: {m.valor}")

        if contexto.plano_alimentar:
            pa = contexto.plano_alimentar
            partes.append(f"\nPlano alimentar: {pa.get_kcal:.0f} kcal/dia")
            partes.append(f"Proteínas: {pa.proteinas_g:.0f}g | Carboidratos: {pa.carboidratos_g:.0f}g | Gorduras: {pa.gorduras_g:.0f}g")

        return "\n".join(partes)

    def _parsear_resposta(self, resposta: str) -> PlanoTreino:
        resposta = resposta.strip()
        if resposta.startswith("```json"):
            resposta = resposta[7:]
        if resposta.startswith("```"):
            resposta = resposta[3:]
        if resposta.endswith("```"):
            resposta = resposta[:-3]
        resposta = resposta.strip()

        dados = json.loads(resposta)
        treino_data = dados.get("plano_treino", dados)

        dias = []
        for d in treino_data.get("dias_treino", []):
            dias.append(DiaTreino(**d))
        treino_data["dias_treino"] = dias

        return PlanoTreino(**treino_data)
