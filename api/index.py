"""
FitNutri Web API - Servidor Serverless FastAPI para a Vercel.
Lida com a execução do pipeline de agentes de forma HTTP.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Adiciona o diretório raiz ao path para poder importar o módulo 'fitnutri'
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importa o core do FitNutri
from fitnutri.pipeline import PipelineFitNutri
from fitnutri.models.schemas import Anamnese

# Inicializa o app FastAPI
app = FastAPI(
    title="🏥 FitNutri Web API",
    description="Endpoint de Agentes de Saúde Multidisciplinar",
    version="1.0.0"
)

# Adiciona suporte a CORS (para que o frontend possa consultar o backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StatusAPI(BaseModel):
    status: str
    versao: str
    deepseek_key_configurada: bool

@app.get("/api")
def root_route() -> StatusAPI:
    """Verifica o status operacional do servidor."""
    key = os.getenv("DEEPSEEK_API_KEY")
    return StatusAPI(
        status="operacional",
        versao="1.0.0",
        deepseek_key_configurada=bool(key and key != "sua-api-key-aqui")
    )

@app.post("/api/executar")
async def executar_atendimento(dados: Dict[str, Any]):
    """
    Inicia a execução síncrona dos agentes para o paciente fornecido.
    
    Nota: Para deploys na Vercel Hobby, essa rota pode dar timeout se o DeepSeek demorar.
    Em produção, deve-se adotar um modelo de Background Jobs (ex: Upstash QStash, Celery, etc).
    """
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="Erro de infraestrutura: 'DEEPSEEK_API_KEY' não configurada nas variáveis de ambiente da Vercel."
        )

    try:
        # Inicializa o orquestrador
        pipeline = PipelineFitNutri(api_key=key)
        
        # Executa o pipeline de agentes com os dados brutos de entrada
        laudo, conteudo_md, conteudo_html, paciente_dir = pipeline.executar(dados)
        
        return {
            "status": "sucesso",
            "paciente": laudo.paciente,
            "diretorio_gerado": str(paciente_dir.name),
            "laudo": {
                "json": laudo.model_dump(),
                "markdown": conteudo_md,
                "html": conteudo_html
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro de processamento nos agentes de IA: {str(e)}"
        )
