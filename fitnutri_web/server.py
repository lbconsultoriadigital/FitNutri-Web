#!/usr/bin/env python3
"""
FitNutri Web Server - Interface Web para o Pipeline de Agentes
Usa apenas módulos nativos do Python (sem dependências extras).
"""

import os
import sys
import json
import logging
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ─── Configurações ───────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent.parent
PACIENTES_DIR = PROJECT_DIR / "pacientes"
VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python3"
MAIN_SCRIPT = PROJECT_DIR / "main.py"
STATIC_DIR = Path(__file__).resolve().parent / "static"
PORT = 8080

# ─── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | FitNutriServer | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fitnutri-server")


# ─── Handlers ─────────────────────────────────────────────────────────────

class FitNutriHandler(SimpleHTTPRequestHandler):
    """Handler HTTP que serve a dashboard e a API."""

    def __init__(self, *args, **kwargs):
        # Define diretório base para arquivos estáticos
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # ─── API Endpoints ─────────────────────────────────────────────
        if path == "/api/pacientes":
            self._handle_listar_pacientes()

        elif path == "/api/paciente":
            self._handle_ver_paciente(params)

        elif path == "/api/status":
            self._send_json({"status": "online", "projeto": "FitNutri Local"})

        elif path == "/api/laudo-html":
            self._handle_laudo_html(params)

        else:
            # Serve arquivos estáticos (index.html, css, js)
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/executar":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            self._handle_executar(json.loads(body))

        else:
            self._send_error(404, "Endpoint não encontrado")

    # ─── Handlers da API ───────────────────────────────────────────────

    def _handle_listar_pacientes(self):
        """Lista todos os pacientes com laudo gerado."""
        pacientes = []
        if PACIENTES_DIR.exists():
            for item in sorted(PACIENTES_DIR.iterdir(), reverse=True):
                if item.is_dir() and (item / "laudo-final.json").exists():
                    try:
                        with open(item / "laudo-final.json", "r", encoding="utf-8") as f:
                            laudo = json.load(f)
                        pacientes.append({
                            "slug": item.name,
                            "nome": laudo.get("paciente", item.name),
                            "data": laudo.get("data_geracao", "")[:10],
                            "objetivo": self._extrair_objetivo(item),
                            "tem_laudo": True,
                        })
                    except Exception:
                        pacientes.append({
                            "slug": item.name,
                            "nome": item.name,
                            "data": "",
                            "objetivo": "",
                            "tem_laudo": False,
                        })
        self._send_json(pacientes)

    def _handle_ver_paciente(self, params):
        """Retorna dados de um paciente específico."""
        slug = params.get("slug", [None])[0]
        if not slug:
            return self._send_error(400, "Parâmetro 'slug' é obrigatório")

        paciente_dir = PACIENTES_DIR / slug
        if not paciente_dir.exists():
            return self._send_error(404, f"Paciente '{slug}' não encontrado")

        laudo_path = paciente_dir / "laudo-final.md"
        laudo_html_path = paciente_dir / "laudo-final.html"
        laudo_json_path = paciente_dir / "laudo-final.json"

        dados = {
            "slug": slug,
            "existe_laudo": laudo_path.exists(),
        }

        if laudo_json_path.exists():
            with open(laudo_json_path, "r", encoding="utf-8") as f:
                dados["laudo_json"] = json.load(f)

        if laudo_path.exists():
            with open(laudo_path, "r", encoding="utf-8") as f:
                dados["laudo_md"] = f.read()

        if laudo_html_path.exists():
            with open(laudo_html_path, "r", encoding="utf-8") as f:
                dados["laudo_html"] = f.read()

        # Lista arquivos do paciente
        dados["arquivos"] = sorted(
            [f.name for f in paciente_dir.iterdir() if f.is_file()]
        )

        self._send_json(dados)

    def _handle_laudo_html(self, params):
        """Serve o laudo em HTML formatado."""
        slug = params.get("slug", [None])[0]
        if not slug:
            return self._send_error(400, "Parâmetro 'slug' é obrigatório")

        html_path = PACIENTES_DIR / slug / "laudo-final.html"
        if not html_path.exists():
            return self._send_error(404, "Laudo HTML não encontrado")

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def _handle_executar(self, dados):
        """Executa o pipeline com dados fornecidos."""
        try:
            # Salva input temporário
            temp_input = PACIENTES_DIR / "_temp_input.json"
            with open(temp_input, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)

            # Executa o pipeline
            cmd = [
                str(VENV_PYTHON),
                str(MAIN_SCRIPT),
                "-p", str(temp_input),
            ]

            logger.info(f"▶️ Executando pipeline via subprocess...")
            resultado = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout
                cwd=str(PROJECT_DIR),
                input="s\n",  # Auto-confirm
            )

            # Log do resultado
            logger.info(f"Pipeline exit code: {resultado.returncode}")
            if resultado.stdout:
                # Procura pelo slug do paciente no output
                for linha in resultado.stdout.split("\n"):
                    if "📁 Laudo salvo em:" in linha:
                        slug = linha.split("pacientes/")[-1].strip().rstrip("/")
                        self._send_json({
                            "success": True,
                            "slug": slug,
                            "message": "Pipeline executado com sucesso!",
                        })
                        # Remove o temp input
                        if temp_input.exists():
                            temp_input.unlink()
                        return

            # Se não achou o slug, retorna sucesso mesmo assim
            self._send_json({
                "success": resultado.returncode == 0,
                "message": "Pipeline executado" if resultado.returncode == 0 else "Erro na execução",
                "stdout": resultado.stdout[-1000:] if resultado.stdout else "",
                "stderr": resultado.stderr[-500:] if resultado.stderr else "",
            })

            if temp_input.exists():
                temp_input.unlink()

        except subprocess.TimeoutExpired:
            self._send_error(408, "Pipeline excedeu o tempo limite (5 min)")
        except Exception as e:
            logger.error(f"Erro ao executar pipeline: {e}")
            self._send_error(500, str(e))

    # ─── Utilitários ───────────────────────────────────────────────────

    def _extrair_objetivo(self, paciente_dir: Path) -> str:
        """Extrai o objetivo do paciente do input.json."""
        input_path = paciente_dir / "input.json"
        if input_path.exists():
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                return dados.get("objetivo", "").replace("_", " ").title()
            except Exception:
                pass
        return ""

    def _send_json(self, data: dict, status: int = 200):
        """Envia resposta JSON."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False, default=str).encode("utf-8"))

    def _send_error(self, status: int, message: str):
        """Envia resposta de erro."""
        self._send_json({"error": message}, status)

    def log_message(self, format, *args):
        """Custom logging."""
        logger.info(f"{self.client_address[0]} - {format % args}")


def abrir_navegador():
    """Abre o navegador no dashboard."""
    url = f"http://localhost:{PORT}"
    logger.info(f"🌐 Abrindo navegador em {url}")
    webbrowser.open(url)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = HTTPServer(("127.0.0.1", port), FitNutriHandler)

    print(f"""
╔══════════════════════════════════════════════╗
║        🏥 FitNutri Local Server              ║
║                                              ║
║   🌐 http://localhost:{port}                  ║
║                                              ║
║   📁 Pacientes: {PACIENTES_DIR}       ║
║                                              ║
║   ⏹️  Para parar: Ctrl+C                      ║
╚══════════════════════════════════════════════╝
    """)

    # Abre navegador após 1 segundo
    import threading
    threading.Timer(1.5, abrir_navegador).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Servidor encerrado.")
        server.server_close()


if __name__ == "__main__":
    main()
