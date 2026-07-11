#!/usr/bin/env python3
"""
FitNutri Local - CLI Principal
Sistema de Atendimento Multidisciplinar da Clínica FitNutri.

Uso:
    python main.py                          # Modo interativo
    python main.py --paciente input.json    # Modo batch
    python main.py --list                   # Listar pacientes
    python main.py --view thiago-rocha      # Ver laudo de paciente
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

from fitnutri.pipeline import PipelineFitNutri
from fitnutri.storage.file_store import FileStore

# ─── Configuração de Logging ──────────────────────────────────────────────
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / f"fitnutri-{datetime.now().strftime('%Y-%m-%d')}.log"),
    ],
)
logger = logging.getLogger("fitnutri")


# ─── Cores para terminal ──────────────────────────────────────────────────
class Cores:
    AZUL = "\033[94m"
    VERDE = "\033[92m"
    AMARELO = "\033[93m"
    VERMELHO = "\033[91m"
    MAGENTA = "\033[95m"
    CIANO = "\033[96m"
    NEGRITO = "\033[1m"
    RESET = "\033[0m"
    # Aliases
    cyan = lambda self, t: f"{self.CIANO}{t}{self.RESET}"
    green = lambda self, t: f"{self.VERDE}{t}{self.RESET}"
    yellow = lambda self, t: f"{self.AMARELO}{t}{self.RESET}"
    red = lambda self, t: f"{self.VERMELHO}{t}{self.RESET}"
    blue = lambda self, t: f"{self.AZUL}{t}{self.RESET}"
    bold = lambda self, t: f"{self.NEGRITO}{t}{self.RESET}"

c = Cores()


# ─── Modo Interativo ─────────────────────────────────────────────────────

def modo_interativo() -> dict:
    """Coleta dados do paciente via terminal interativo."""
    print()
    print(c.blue("=" * 60))
    print(c.bold(c.blue("🏥 CLÍNICA FITNUTRI — SISTEMA LOCAL DE ATENDIMENTO")))
    print(c.blue("=" * 60))
    print()
    print(c.cyan("📋 INICIANDO NOVO ATENDIMENTO"))
    print(c.cyan("─" * 40))
    print(c.yellow("(Pressione Enter para pular campos opcionais)"))
    print()

    dados = {}

    # Dados pessoais
    dados["nome"] = input(c.bold("Nome completo: ")).strip()
    if not dados["nome"]:
        dados["nome"] = "Paciente"

    dados["idade"] = _input_int("Idade")
    dados["peso_kg"] = _input_float("Peso (kg)")
    dados["altura_m"] = _input_float("Altura (m)")

    sexo = input(c.bold("Sexo (masculino/feminino): ")).strip().lower()
    dados["sexo"] = sexo if sexo in ("masculino", "feminino") else "masculino"

    dados["profissao"] = input(c.bold("Profissão: ")).strip()

    print()
    print(c.cyan("🎯 OBJETIVO"))
    print(c.cyan("─" * 40))
    print("1. Emagrecimento")
    print("2. Hipertrofia")
    print("3. Performance")
    print("4. Recomposição Corporal")
    print("5. Saúde e Bem-Estar")
    print("6. Outro")
    obj_opcao = _input_int("Objetivo (1-6)", default=1)
    objetivos = {
        1: "emagrecimento", 2: "hipertrofia", 3: "performance",
        4: "recomposicao_corporal", 5: "saude_bem_estar", 6: "outro",
    }
    dados["objetivo"] = objetivos.get(obj_opcao, "saude_bem_estar")
    dados["objetivo_descricao"] = input(c.bold("Descreva seu objetivo: ")).strip()

    # Histórico de saúde
    print()
    print(c.cyan("🩺 HISTÓRICO DE SAÚDE"))
    print(c.cyan("─" * 40))
    dados["doencas"] = _input_list("Doenças crônicas (separadas por vírgula)")
    dados["medicamentos"] = _input_list("Medicamentos em uso")
    dados["alergias"] = _input_list("Alergias")
    dados["cirurgias"] = _input_list("Cirurgias anteriores")
    dados["condicoes"] = _input_list("Condições específicas (DRGE, etc)")

    # Hábitos
    print()
    print(c.cyan("🌙 HÁBITOS DE VIDA"))
    print(c.cyan("─" * 40))
    dados["sono_horas"] = _input_float("Horas de sono por dia", default=7)
    dados["sono_qualidade"] = _input_opcao(
        "Qualidade do sono", ["ruim", "regular", "boa", "otima"], default="regular"
    )
    dados["estresse"] = _input_opcao(
        "Nível de estresse", ["baixo", "moderado", "alto"], default="moderado"
    )
    dados["cafeina"] = input(c.bold("Consumo de cafeína/dia: ")).strip() or "Não informado"
    dados["agua_litros"] = _input_float("Água (litros/dia)", default=2.0)

    alcool = input(c.bold("Consome álcool? (sim/nao): ")).strip().lower()
    dados["alcool"] = alcool if alcool in ("sim", "nao") else "nao"

    fumante = input(c.bold("Fumante? (s/n): ")).strip().lower()
    dados["fumante"] = fumante.startswith("s")

    # Exames
    print()
    print(c.cyan("🔬 EXAMES LABORATORIAIS"))
    print(c.cyan("─" * 40))
    print(c.yellow("Cole os resultados dos exames ou pressione Enter para pular"))
    exames_texto = []
    print(c.bold("Exames (digite 'fim' para encerrar):"))
    while True:
        linha = input("  > ")
        if linha.strip().lower() == "fim" or linha.strip() == "":
            break
        exames_texto.append(linha)
    dados["exames_texto"] = "\n".join(exames_texto) if exames_texto else ""
    dados["data_exames"] = input(c.bold("Data dos exames (DD/MM/AAAA): ")).strip()

    # Treino
    print()
    print(c.cyan("🏋️ TREINO ATUAL"))
    print(c.cyan("─" * 40))
    dados["treino_freq"] = _input_int("Frequência semanal (dias)", default=3)
    dados["tipo_treino"] = input(c.bold("Tipo de treino: ")).strip() or "Musculação"
    dados["nivel"] = _input_opcao(
        "Nível", ["iniciante", "intermediario", "avancado"], default="intermediario"
    )
    dados["local_treino"] = _input_opcao(
        "Local", ["academia", "casa", "ambos"], default="academia"
    )
    dados["lesoes"] = _input_list("Lesões atuais")
    dados["limitacoes"] = _input_list("Limitações")

    # Alimentação
    print()
    print(c.cyan("🥗 PREFERÊNCIAS ALIMENTARES"))
    print(c.cyan("─" * 40))
    dados["preferencias"] = _input_list("Preferências alimentares")
    dados["restricoes"] = _input_list("Restrições alimentares")
    dados["suplementos"] = _input_list("Suplementos em uso")

    return dados


def _input_int(label: str, default: int = 0) -> int:
    while True:
        try:
            valor = input(c.bold(f"{label}: ")).strip()
            if not valor:
                return default
            return int(valor)
        except ValueError:
            print(c.red("  ❌ Digite um número válido"))


def _input_float(label: str, default: float = 0.0) -> float:
    while True:
        try:
            valor = input(c.bold(f"{label}: ")).strip()
            if not valor:
                return default
            # Suporta vírgula como separador decimal
            return float(valor.replace(",", "."))
        except ValueError:
            print(c.red("  ❌ Digite um número válido"))


def _input_opcao(label: str, opcoes: list[str], default: str = "") -> str:
    print(c.bold(f"{label} ({'/'.join(opcoes)}): "))
    valor = input("  > ").strip().lower()
    if valor in opcoes:
        return valor
    if default:
        return default
    return opcoes[0]


def _input_list(label: str) -> list[str]:
    valores = input(c.bold(f"{label} (separados por vírgula): ")).strip()
    if not valores:
        return []
    return [v.strip() for v in valores.split(",") if v.strip()]


# ─── Funções de Visualização ─────────────────────────────────────────────

def listar_pacientes():
    """Lista todos os pacientes atendidos."""
    store = FileStore()
    pacientes = store.listar_pacientes()

    if not pacientes:
        print(c.yellow("\n📭 Nenhum paciente encontrado."))
        print(c.yellow("   Execute 'python main.py' para iniciar um atendimento."))
        return

    print(c.blue("\n" + "=" * 60))
    print(c.bold(c.blue("📋 PACIENTES ATENDIDOS")))
    print(c.blue("=" * 60))

    for i, p in enumerate(pacientes, 1):
        nome = c.bold(p["nome"])
        data = p.get("data", "")[:10] if p.get("data") else ""
        print(f"  {i}. {nome} ({data})")
        print(f"     📁 {p['caminho']}")

    print()


def ver_laudo(slug: str):
    """Exibe o laudo de um paciente."""
    store = FileStore()
    caminho = Path("pacientes") / slug / "laudo-final.md"

    if not caminho.exists():
        print(c.red(f"\n❌ Laudo não encontrado para '{slug}'"))
        print(c.yellow("   Use 'python main.py --list' para ver pacientes disponíveis."))
        return

    print(c.blue("\n" + "=" * 60))
    print(c.bold(c.blue(f"📄 LAUDO - {slug}")))
    print(c.blue("=" * 60 + "\n"))

    with open(caminho, "r", encoding="utf-8") as f:
        print(f.read())


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🏥 FitNutri Local - Sistema de Atendimento Multidisciplinar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py                        Modo interativo
  python main.py --paciente dados.json  Modo batch
  python main.py --list                 Listar pacientes
  python main.py --view thiago-rocha    Ver laudo
        """,
    )
    parser.add_argument(
        "--paciente", "-p",
        type=str,
        help="Caminho para arquivo JSON com dados do paciente",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Listar pacientes atendidos",
    )
    parser.add_argument(
        "--view", "-v",
        type=str,
        metavar="SLUG",
        help="Visualizar laudo de um paciente (slug)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API Key do DeepSeek (opcional, usa .env por padrão)",
    )

    args = parser.parse_args()

    # ─── Listar pacientes ──────────────────────────────────────────────
    if args.list:
        listar_pacientes()
        return

    # ─── Visualizar laudo ──────────────────────────────────────────────
    if args.view:
        ver_laudo(args.view)
        return

    # ─── Coletar dados do paciente ────────────────────────────────────
    if args.paciente:
        # Modo batch: carrega de arquivo JSON
        caminho = args.paciente
        if not os.path.exists(caminho):
            print(c.red(f"\n❌ Arquivo não encontrado: {caminho}"))
            sys.exit(1)
        with open(caminho, "r", encoding="utf-8") as f:
            dados_paciente = json.load(f)
        print(c.blue(f"\n📂 Carregando dados de: {caminho}"))
    else:
        # Modo interativo
        dados_paciente = modo_interativo()

    # ─── Confirmar antes de executar ──────────────────────────────────
    nome_paciente = dados_paciente.get("nome", "Paciente")
    objetivo = dados_paciente.get("objetivo", "não informado")
    print()
    print(c.cyan("📋 RESUMO DO PACIENTE"))
    print(c.cyan("─" * 40))
    print(f"  Nome:     {c.bold(nome_paciente)}")
    print(f"  Idade:    {dados_paciente.get('idade', '?')} anos")
    print(f"  Objetivo: {objetivo}")
    print()

    confirmar = input(c.yellow("Iniciar atendimento? (s/N): ")).strip().lower()
    if confirmar != "s":
        print(c.yellow("\n⏹️  Atendimento cancelado."))
        return

    # ─── Executar pipeline ────────────────────────────────────────────
    print()
    print(c.blue("=" * 60))
    print(c.bold(c.blue("🚀 INICIANDO PIPELINE DE AGENTES")))
    print(c.blue("=" * 60))

    api_key = args.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "sua-api-key-aqui":
        print()
        print(c.red("❌ API Key do DeepSeek não configurada!"))
        print(c.yellow("   Configure no arquivo .env:"))
        print(c.yellow("   DEEPSEEK_API_KEY=sua-chave-aqui"))
        print(c.yellow("   Ou passe via --api-key"))
        print()
        print(c.cyan("   Para obter uma chave: https://platform.deepseek.com/"))
        sys.exit(1)

    pipeline = PipelineFitNutri(api_key=api_key)

    try:
        laudo, conteudo_md, conteudo_html, paciente_dir = pipeline.executar(
            dados_paciente
        )

        print()
        print(c.green("=" * 60))
        print(c.bold(c.green("✅ ATENDIMENTO FINALIZADO COM SUCESSO!")))
        print(c.green("=" * 60))
        print()
        print(c.cyan(f"📁 Laudo salvo em: {c.bold(str(paciente_dir))}/"))
        print(c.cyan(f"   ├── laudo-final.md"))
        print(c.cyan(f"   ├── laudo-final.html"))
        print(c.cyan(f"   └── laudo-final.json"))
        print()
        print(c.yellow("📄 Para visualizar o laudo:"))
        print(c.yellow(f"   cat {paciente_dir}/laudo-final.md"))
        print(c.yellow(f"   python main.py --view {paciente_dir.name}"))
        print()

    except Exception as e:
        logger.error(f"❌ Erro durante o pipeline: {e}", exc_info=True)
        print()
        print(c.red(f"❌ ERRO: {e}"))
        print(c.yellow("   Verifique os logs para mais detalhes."))
        sys.exit(1)


if __name__ == "__main__":
    main()
