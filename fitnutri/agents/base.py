"""
FitNutri Local - Classe Base para Agentes
Define o contrato que todos os agentes devem seguir.
"""

from abc import ABC, abstractmethod
from ..models.schemas import ContextoPipeline
from ..llm.client import DeepSeekClient


class AgenteBase(ABC):
    """Classe base abstrata para todos os agentes do pipeline.

    Cada agente:
    1. Recebe o ContextoPipeline atual
    2. Executa sua especialidade via LLM
    3. Enriquece o contexto com sua contribuição
    4. Retorna o contexto atualizado
    """

    def __init__(self, llm_client: DeepSeekClient):
        self.llm = llm_client
        self.nome: str = "Agente Base"
        self.descricao: str = ""
        self.modelo: str = "flash"
        self.temperatura: float = 0.3
        self.max_tokens: int = 4096
        self.system_prompt: str = ""

    @abstractmethod
    def executar(self, contexto: ContextoPipeline) -> ContextoPipeline:
        """Executa a etapa do agente e retorna contexto atualizado."""
        pass

    def _montar_contexto_entrada(self, contexto: ContextoPipeline) -> str:
        """Monta o resumo do contexto acumulado para o prompt."""
        partes = []

        if contexto.paciente:
            p = contexto.paciente
            partes.append("## DADOS DO PACIENTE")
            partes.append(f"Nome: {p.dados_pessoais.nome}")
            partes.append(f"Idade: {p.dados_pessoais.idade}")
            partes.append(f"Peso: {p.dados_pessoais.peso_kg}kg")
            partes.append(f"Altura: {p.dados_pessoais.altura_m}m")
            partes.append(f"Objetivo: {p.dados_pessoais.objetivo.value}")
            if p.dados_pessoais.objetivo_descricao:
                partes.append(f"Descrição: {p.dados_pessoais.objetivo_descricao}")
            partes.append("")

        if contexto.analise_exames:
            a = contexto.analise_exames
            partes.append("## ANÁLISE DE EXAMES")
            for m in a.marcadores:
                partes.append(f"- {m.nome}: {m.valor} ({m.status})")
            if a.alertas_criticos:
                partes.append("Alertas: " + "; ".join(a.alertas_criticos))
            partes.append("")

        if contexto.protocolo_suplementacao:
            s = contexto.protocolo_suplementacao
            partes.append("## PROTOCOLO DE SUPLEMENTAÇÃO")
            for sup in s.suplementos:
                partes.append(f"- {sup.nome}: {sup.dosagem} ({sup.posologia})")
            partes.append("")

        if contexto.plano_alimentar:
            pa = contexto.plano_alimentar
            partes.append("## PLANO ALIMENTAR")
            partes.append(f"GET: {pa.get_kcal:.0f} kcal | Ajuste: {pa.ajuste_kcal:.0f} kcal")
            partes.append(f"Proteínas: {pa.proteinas_g:.0f}g | Carboidratos: {pa.carboidratos_g:.0f}g | Gorduras: {pa.gorduras_g:.0f}g")
            partes.append("")

        return "\n".join(partes)
