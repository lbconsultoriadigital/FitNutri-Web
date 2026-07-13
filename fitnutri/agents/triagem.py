"""
FitNutri Local - Agente 1: Triagem & Anamnese
Coleta dados completos do paciente através de perguntas estruturadas.
Modelo: DeepSeek V4 Flash
"""

import json
import logging
from ..models.schemas import (
    ContextoPipeline, Anamnese, DadosPessoais, HistoricoSaude,
    HabitosVida, ExamesLaboratoriais, TreinoAtual,
    ObjetivoEnum, SexoEnum, NivelTreinoEnum, LocalTreinoEnum,
)
from .base import AgenteBase
from ..validation.validator import ValidadorFitNutri, AlertaSeveridade

logger = logging.getLogger(__name__)
validador = ValidadorFitNutri()

SYSTEM_PROMPT = """Você é o Agente de Triagem da Clínica FitNutri.
Sua função é realizar uma anamnese completa e estruturada.

Com base nos dados fornecidos pelo paciente, organize TODAS as informações nos campos solicitados.

Dados a coletar/organizar:
- Dados pessoais (nome, idade, peso, altura, sexo, profissão)
- IMC (calcule automaticamente: peso / altura²)
- Objetivo principal (emagrecimento, hipertrofia, performance, recomposicao_corporal, saude_bem_estar, outro)
- Descrição detalhada do objetivo
- Histórico de saúde (doenças crônicas, cirurgias, medicamentos, alergias, condições específicas, histórico familiar)
- Hábitos de vida (sono horas, qualidade do sono, nível de estresse, cafeína diária, água L/dia, álcool, fumante)
- Exames disponíveis (texto livre com os exames que o paciente possui)
- Treino atual (frequência semanal, tipo, tempo de prática: iniciante/intermediario/avancado, lesões atuais, limitações, local: academia/casa/ambos)
- Preferências alimentares
- Restrições alimentares
- Suplementos em uso

IMPORTANTE: Responda APENAS com um JSON válido no seguinte formato, sem formatação markdown:
{
    "anamnese": {
        "dados_pessoais": {
            "nome": "...",
            "idade": 0,
            "peso_kg": 0.0,
            "altura_m": 0.0,
            "sexo": "masculino" ou "feminino",
            "profissao": "...",
            "imc": 0.0,
            "objetivo": "emagrecimento" | "hipertrofia" | "performance" | "recomposicao_corporal" | "saude_bem_estar" | "outro",
            "objetivo_descricao": "..."
        },
        "historico_saude": {
            "doencas_cronicas": [],
            "cirurgias": [],
            "medicamentos": [],
            "alergias": [],
            "condicoes_especificas": [],
            "historico_familiar": []
        },
        "habitos": {
            "sono_horas": 0,
            "sono_qualidade": "ruim" | "regular" | "boa" | "otima",
            "estresse_nivel": "baixo" | "moderado" | "alto",
            "cafeina_diaria": "...",
            "agua_litros": 0.0,
            "alcool": "...",
            "fumante": false
        },
        "exames": {
            "exames_texto": "...",
            "data_exames": "..."
        },
        "treino": {
            "frequencia_semanal": 0,
            "tipo_treino": "...",
            "tempo_pratica": "iniciante" | "intermediario" | "avancado",
            "lesoes_atuais": [],
            "limitacoes": [],
            "local_treino": "academia" | "casa" | "ambos"
        },
        "preferencias_alimentares": [],
        "restricoes_alimentares": [],
        "suplementos_atuais": []
    }
}

VALIDAÇÕES OBRIGATÓRIAS ANTES DE FINALIZAR:
1. Peso: {1-300} kg
2. Altura: {0.5-2.5} m
3. IMC coerente: peso / altura²
4. Idade: {14-120} anos
5. Se detectar sintomas graves (dor no peito, falta de ar, etc):
   - MARQUE COMO RED FLAG 🔴
   - NÃO continuar para próxima etapa

Se algum campo não foi informado, use valor padrão (null para optional, 0 para números, [] para listas, false para booleanos).
NUNCA invente informações. Use null se não tiver o dado."""


class AgenteTriagem(AgenteBase):
    """Agente responsável pela triagem e coleta de anamnese."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.nome = "📋 Triagem & Anamnese"
        self.descricao = "Coleta dados completos do paciente"
        self.modelo = "flash"
        self.temperatura = 0.3
        self.system_prompt = SYSTEM_PROMPT

    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        logger.info(f"▶️ Executando: {self.nome}")

        # Monta o prompt com os dados disponíveis
        dados_brutos = self._extrair_dados_brutos(contexto)
        user_message = (
            "Extraia e mapeie os seguintes dados do paciente para o JSON de anamnese.\n\n"
            f"DADOS BRUTOS DO PACIENTE:\n{dados_brutos}\n\n"
            "REGRAS DE MAPEAMENTO:\n"
            "- objetivo: 'emagrecimento', 'hipertrofia', 'performance', 'recomposicao_corporal', 'saude_bem_estar', 'outro'\n"
            "- sexo: 'masculino' ou 'feminino'\n"
            "- nivel: 'iniciante', 'intermediario', 'avancado'\n"
            "- local_treino: 'academia', 'casa', 'ambos'\n"
            "- sono_qualidade: 'ruim', 'regular', 'boa', 'otima'\n"
            "- estresse_nivel: 'baixo', 'moderado', 'alto'\n"
            "IMPORTANTE: USE OS VALORES REAIS DOS DADOS ACIMA. NÃO USE null. Se um campo não está nos dados, use o default vazio '' ou 0.")

        # Chama o LLM
        resposta = self.llm.gerar(
            system_prompt=self.system_prompt,
            user_message=user_message,
            modelo=self.modelo,
            temperatura=self.temperatura,
        )

        # Parseia o JSON
        anamnese = self._parsear_resposta(resposta)
        contexto.paciente = anamnese
        
        # OPÇÃO A: Validação Minimal
        self._validar_anamnese(anamnese, contexto)
        
        contexto.etapa_atual = "triagem_concluida"

        logger.info(f"✅ {self.nome} concluído - Paciente: {anamnese.dados_pessoais.nome}")
        return contexto
    
    def _validar_anamnese(self, anamnese: Anamnese, contexto: ContextoPipeline) -> None:
        """Valida dados da anamnese e detecta red flags."""
        dados_pessoais = anamnese.dados_pessoais
        habitos = anamnese.habitos
        
        logger.info("🔍 Validando dados da triagem...")
        
        # Validar dados pessoais
        valido_pessoais, erros_pessoais = validador.validar_dados_pessoais({
            "peso_kg": dados_pessoais.peso_kg,
            "altura_m": dados_pessoais.altura_m,
            "imc": dados_pessoais.imc,
            "idade": dados_pessoais.idade
        })
        
        if not valido_pessoais:
            for erro in erros_pessoais:
                logger.warning(f"⚠️ Erro em dados pessoais: {erro}")
                contexto.alertas_validacao = contexto.alertas_validacao or []
                contexto.alertas_validacao.append(erro)
        
        # Validar hábitos de vida
        valido_habitos, erros_habitos, avisos_habitos = validador.validar_habitos_vida({
            "sono_horas": habitos.sono_horas,
            "agua_litros": habitos.agua_litros,
            "cafeina_diaria": habitos.cafeina_diaria,
            "fumante": habitos.fumante
        })
        
        if avisos_habitos:
            for aviso in avisos_habitos:
                logger.warning(f"⚠️ Aviso em hábitos: {aviso}")
                contexto.alertas_validacao = contexto.alertas_validacao or []
                contexto.alertas_validacao.append(aviso)
        
        # Detecção de red flags em texto (lesões, sintomas graves)
        lesoes_texto = " ".join(anamnese.treino.lesoes_atuais or [])
        sintomas_flags = validador.validar_relatos_sintomas(lesoes_texto)
        
        if sintomas_flags:
            logger.error(f"🚨 RED FLAG detectada na triagem!")
            for flag in sintomas_flags:
                logger.error(f"   - {flag['palavra_chave']}: {flag['recomendacao']}")
                contexto.alertas_validacao = contexto.alertas_validacao or []
                contexto.alertas_validacao.append(flag['recomendacao'])
                contexto.escalacao_necessaria = True
                contexto.severidade_escalacao = AlertaSeveridade.PRETO

    def _extrair_dados_brutos(self, contexto: ContextoPipeline) -> str:
        """Extrai dados disponíveis no contexto ou input inicial."""
        entrada = getattr(contexto, "_dados_entrada", None)

        if entrada:
            import json as json_mod
            return json_mod.dumps(entrada, indent=2, ensure_ascii=False)

        if contexto.paciente:
            return json.dumps(contexto.paciente.model_dump(), indent=2, ensure_ascii=False)

        # Se não tem paciente ainda, são dados vindos do input inicial
        return "Paciente novo - organizar dados a partir do input fornecido."

    def _parsear_resposta(self, resposta: str) -> Anamnese:
        """Parseia a resposta JSON do LLM para o modelo Anamnese."""
        # Remove possíveis marcadores markdown
        resposta = resposta.strip()
        if resposta.startswith("```json"):
            resposta = resposta[7:]
        if resposta.startswith("```"):
            resposta = resposta[3:]
        if resposta.endswith("```"):
            resposta = resposta[:-3]

        resposta = resposta.strip()
        dados = json.loads(resposta)

        anamnese_data = dados.get("anamnese", dados)
        return Anamnese(**anamnese_data)
