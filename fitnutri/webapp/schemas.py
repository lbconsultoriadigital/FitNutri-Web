from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import MAX_EXTRACTED_TEXT


class AtendimentoCreate(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    nome: str = Field(min_length=2, max_length=160)
    idade: int = Field(ge=0, le=150)
    peso_kg: float = Field(gt=0, le=500)
    altura_m: float = Field(gt=0, le=3)
    sexo: Literal["masculino", "feminino"]
    profissao: str = Field(default="", max_length=160)
    objetivo: Literal[
        "emagrecimento", "hipertrofia", "performance",
        "recomposicao_corporal", "saude_bem_estar", "outro",
    ] = "saude_bem_estar"
    objetivo_descricao: str = Field(default="", max_length=3000)
    condicoes: list[str] = Field(default_factory=list, max_length=50)
    doencas_cronicas: list[str] = Field(default_factory=list, max_length=50)
    cirurgias: list[str] = Field(default_factory=list, max_length=50)
    medicamentos: list[str] = Field(default_factory=list, max_length=100)
    alergias: list[str] = Field(default_factory=list, max_length=100)
    historico_familiar: list[str] = Field(default_factory=list, max_length=100)
    sono_horas: float = Field(default=0, ge=0, le=24)
    sono_qualidade: str = Field(default="regular", max_length=80)
    estresse_nivel: str = Field(default="moderado", max_length=80)
    agua_litros: float = Field(default=0, ge=0, le=20)
    alcool: str = Field(default="nao", max_length=80)
    fumante: bool = False
    frequencia_treino: int = Field(default=0, ge=0, le=14)
    tipo_treino: str = Field(default="", max_length=300)
    nivel_treino: Literal["iniciante", "intermediario", "avancado"] = "iniciante"
    lesoes: list[str] = Field(default_factory=list, max_length=50)
    limitacoes: list[str] = Field(default_factory=list, max_length=50)
    local_treino: Literal["academia", "casa", "ambos"] = "academia"
    preferencias_alimentares: list[str] = Field(default_factory=list, max_length=100)
    restricoes_alimentares: list[str] = Field(default_factory=list, max_length=100)
    suplementos_atuais: list[str] = Field(default_factory=list, max_length=100)
    exames_texto: str = Field(default="", max_length=MAX_EXTRACTED_TEXT)
    obs: str = Field(default="", max_length=15_000)


class WorkerPayload(BaseModel):
    job_id: str
    stage: int = Field(ge=1, le=6)


class ApprovalPayload(BaseModel):
    reviewer_name: str = Field(min_length=3, max_length=160)
    registration_type: Literal["CRM", "CRN", "CREF", "outro"]
    registration_number: str = Field(min_length=2, max_length=80)
    notes: str = Field(default="", max_length=4000)


class LoginPayload(BaseModel):
    password: str = Field(min_length=1, max_length=500)
