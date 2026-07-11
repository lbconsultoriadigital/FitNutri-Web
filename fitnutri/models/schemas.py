"""
FitNutri Local - Modelos de Dados (Pydantic)
Schemas tipados para todo o pipeline de atendimento.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────

class ObjetivoEnum(str, Enum):
    EMAGRECER = "emagrecimento"
    HIPERTROFIA = "hipertrofia"
    PERFORMANCE = "performance"
    RECOMPOSICAO = "recomposicao_corporal"
    SAUDE = "saude_bem_estar"
    OUTRO = "outro"


class SexoEnum(str, Enum):
    MASCULINO = "masculino"
    FEMININO = "feminino"


class NivelTreinoEnum(str, Enum):
    INICIANTE = "iniciante"
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"


class LocalTreinoEnum(str, Enum):
    ACADEMIA = "academia"
    CASA = "casa"
    AMBOS = "ambos"


# ─── Input / Anamnese ─────────────────────────────────────────────────────

class DadosPessoais(BaseModel):
    nome: str = ""
    idade: int = Field(default=0, ge=0, le=150)
    peso_kg: float = Field(default=0.0, gt=0, le=500)
    altura_m: float = Field(default=0.0, gt=0, le=3)
    sexo: SexoEnum = SexoEnum.MASCULINO
    profissao: str = ""
    imc: Optional[float] = None
    objetivo: ObjetivoEnum = ObjetivoEnum.SAUDE
    objetivo_descricao: str = ""


class HistoricoSaude(BaseModel):
    doencas_cronicas: list[str] = []
    cirurgias: list[str] = []
    medicamentos: list[str] = []
    alergias: list[str] = []
    condicoes_especificas: list[str] = []
    historico_familiar: list[str] = []


class HabitosVida(BaseModel):
    sono_horas: float = Field(default=0, ge=0, le=24)
    sono_qualidade: str = "regular"
    estresse_nivel: str = "moderado"
    cafeina_diaria: str = ""
    agua_litros: float = Field(default=0, ge=0)
    alcool: str = "nao"
    fumante: bool = False


class ExamesLaboratoriais(BaseModel):
    exames_texto: Optional[str] = None
    exames_estruturados: Optional[dict] = None
    data_exames: Optional[str] = None


class TreinoAtual(BaseModel):
    frequencia_semanal: int = Field(default=0, ge=0, le=14)
    tipo_treino: str = ""
    tempo_pratica: NivelTreinoEnum = NivelTreinoEnum.INICIANTE
    lesoes_atuais: list[str] = []
    limitacoes: list[str] = []
    local_treino: LocalTreinoEnum = LocalTreinoEnum.ACADEMIA


class Anamnese(BaseModel):
    dados_pessoais: DadosPessoais
    historico_saude: HistoricoSaude
    habitos: HabitosVida
    exames: Optional[ExamesLaboratoriais] = None
    treino: TreinoAtual
    preferencias_alimentares: list[str] = []
    restricoes_alimentares: list[str] = []
    suplementos_atuais: list[str] = []


# ─── Outputs Intermediários ───────────────────────────────────────────────

class MarcadorExame(BaseModel):
    nome: str
    valor: str
    referencia: str
    status: str = "normal"  # critico | atencao | normal
    conduta: str = ""


class AnaliseExames(BaseModel):
    marcadores: list[MarcadorExame] = []
    alertas_criticos: list[str] = []
    parecer_medico: str = ""


class ItemSuplemento(BaseModel):
    nome: str
    dosagem: str
    posologia: str
    duracao: str
    justificativa: str
    evidencias: str = ""


class ProtocoloSuplementacao(BaseModel):
    suplementos: list[ItemSuplemento] = []
    interacoes: list[str] = []
    contraindicacoes: list[str] = []
    observacoes_gerais: str = ""


class Refeicao(BaseModel):
    nome: str
    horario: str
    alimentos: list[str] = []
    observacoes: str = ""


class PlanoAlimentar(BaseModel):
    tmb_kcal: float = 0
    get_kcal: float = 0
    ajuste_kcal: float = 0
    proteinas_g: float = 0
    carboidratos_g: float = 0
    gorduras_g: float = 0
    fibras_g: float = 0
    meta_hidrica_l: float = 0
    refeicoes: list[Refeicao] = []
    observacoes_gerais: str = ""


class DiaTreino(BaseModel):
    dia: str  # segunda, terca, etc
    foco: str
    exercicios: list[str] = []


class PlanoTreino(BaseModel):
    frequencia_semanal: int = 0
    estrutura: str = ""  # PPL | ABCD | UpperLower | Fullbody
    dias_treino: list[DiaTreino] = []
    aquecimento: str = ""
    observacoes: list[str] = []


# ─── Laudo Final ──────────────────────────────────────────────────────────

class LaudoFinal(BaseModel):
    paciente: str
    data_geracao: datetime = Field(default_factory=datetime.now)
    versao: str = "1.0"
    sumario_executivo: str = ""
    anamnese: Optional[Anamnese] = None
    analise_exames: Optional[AnaliseExames] = None
    protocolo_suplementacao: Optional[ProtocoloSuplementacao] = None
    plano_alimentar: Optional[PlanoAlimentar] = None
    plano_treino: Optional[PlanoTreino] = None
    recomendacoes_gerais: list[str] = []
    proximos_passos: list[str] = []


# ─── Contexto Compartilhado do Pipeline ───────────────────────────────────

class ContextoPipeline(BaseModel):
    """Contexto compartilhado entre todos os agentes do pipeline.
    Cada agente le, processa e enriquece este contexto."""
    paciente: Optional[Anamnese] = None
    analise_exames: Optional[AnaliseExames] = None
    protocolo_suplementacao: Optional[ProtocoloSuplementacao] = None
    plano_alimentar: Optional[PlanoAlimentar] = None
    plano_treino: Optional[PlanoTreino] = None
    laudo_final: Optional[LaudoFinal] = None
    etapa_atual: str = "inicio"
    erros: list[str] = []
    inicio_atendimento: datetime = Field(default_factory=datetime.now)
