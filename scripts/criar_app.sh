#!/bin/bash
# ────────────────────────────────────────────────────────────────────────────
# FitNutri App Builder
# Cria um aplicativo nativo do macOS para o FitNutri Local
# ────────────────────────────────────────────────────────────────────────────

set -e

APP_NAME="FitNutri"
PROJECT_DIR="/Users/felipeleone/Documents/FitNutri"
APP_DIR="$PROJECT_DIR/${APP_NAME}.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
ICON="$RESOURCES/AppIcon.icns"

echo "🏗️  Criando $APP_NAME.app..."

# ─── Remove app anterior se existir ──────────────────────────────────────
if [ -d "$APP_DIR" ]; then
    echo "   ♻️  Removendo versão anterior..."
    rm -rf "$APP_DIR"
fi

# ─── Cria estrutura de diretórios ────────────────────────────────────────
mkdir -p "$MACOS" "$RESOURCES"

# ─── Cria o executável principal ────────────────────────────────────────
cat > "$MACOS/$APP_NAME" << 'SCRIPT'
#!/bin/bash

# ─── FitNutri - App Nativo macOS ─────────────────────────────────────────
# Este script inicia o servidor web do FitNutri em background
# e abre o navegador no dashboard.

PROJECT_DIR="/Users/felipeleone/Documents/FitNutri"
SERVER_SCRIPT="$PROJECT_DIR/fitnutri_web/server.py"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
PID_FILE="/tmp/fitnutri-server.pid"
LOG_FILE="$PROJECT_DIR/logs/server.log"

# Garante que a pasta de logs existe
mkdir -p "$PROJECT_DIR/logs"

# ─── Função para mostrar notificação ────────────────────────────────────
notify() {
    osascript -e "display notification \"$1\" with title \"🏥 FitNutri\" subtitle \"$2\" sound name \"default\""
}

# ─── Verifica se já está rodando ────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        notify "Já está rodando" "Servidor ativo (PID: $OLD_PID)"
        # Abre o navegador mesmo se já estiver rodando
        open "http://localhost:8080"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# ─── Inicia o servidor em background ─────────────────────────────────────
cd "$PROJECT_DIR"
nohup "$VENV_PYTHON" "$SERVER_SCRIPT" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

# Aguarda o servidor iniciar
sleep 2

# Verifica se está rodando
if kill -0 "$SERVER_PID" 2>/dev/null; then
    notify "Servidor iniciado" "🌐 http://localhost:8080"
    echo "✅ FitNutri Server rodando (PID: $SERVER_PID)"
    echo "   Dashboard: http://localhost:8080"
    echo "   Logs: $LOG_FILE"

    # Abre o navegador
    open "http://localhost:8080"
else
    notify "Erro ao iniciar" "Verifique os logs em $LOG_FILE"
    echo "❌ Erro ao iniciar o servidor"
    cat "$LOG_FILE"
    exit 1
fi

# ─── Mantém o app aberto mas sem janela ─────────────────────────────────
# Fica monitorando o processo
while kill -0 "$SERVER_PID" 2>/dev/null; do
    sleep 5
done

# Se o processo morrer, remove o PID file
rm -f "$PID_FILE"
SCRIPT

chmod +x "$MACOS/$APP_NAME"

# ─── Info.plist ─────────────────────────────────────────────────────────
cat > "$CONTENTS/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.fitnutri.local</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>FitNutri</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSBackgroundOnly</key>
    <false/>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

# ─── Cria um ícone simples (placeholder) ────────────────────────────────
# Como não temos um arquivo .icns, criamos um placeholder
# O macOS usará o ícone padrão, o que já funciona
touch "$ICON"

# ─── Cria script para parar o servidor ──────────────────────────────────
mkdir -p "$PROJECT_DIR/Parar FitNutri.app/Contents/MacOS"
cat > "$PROJECT_DIR/Parar FitNutri.app/Contents/MacOS/Parar FitNutri" << 'STOP_SCRIPT'
#!/bin/bash
PID_FILE="/tmp/fitnutri-server.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PID_FILE"
        osascript -e "display notification \"Servidor parado\" with title \"🏥 FitNutri\""
        echo "✅ Servidor parado (PID: $PID)"
    else
        rm -f "$PID_FILE"
        echo "⚠️  Servidor não estava rodando"
    fi
else
    echo "⚠️  Servidor não estava rodando"
fi
STOP_SCRIPT

chmod +x "$PROJECT_DIR/Parar FitNutri.app/Contents/MacOS/Parar FitNutri"

cat > "$PROJECT_DIR/Parar FitNutri.app/Contents/Info.plist" << 'STOP_PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Parar FitNutri</string>
    <key>CFBundleIdentifier</key>
    <string>com.fitnutri.stop</string>
    <key>CFBundleName</key>
    <string>Parar FitNutri</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
STOP_PLIST

# ─── Cria o atalho de desinstalação ────────────────────────────────────
mkdir -p "$PROJECT_DIR/Remover FitNutri.app/Contents/MacOS"
cat > "$PROJECT_DIR/Remover FitNutri.app/Contents/MacOS/Remover FitNutri" << 'REMOVE_SCRIPT'
#!/bin/bash
echo "⚠️  Deseja realmente remover o FitNutri Local?"
echo "   Isso NÃO apaga seus pacientes, apenas os apps."
read -p "   Continuar? (s/N): " confirm
if [ "$confirm" = "s" ]; then
    # Para o servidor se estiver rodando
    PID_FILE="/tmp/fitnutri-server.pid"
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
    # Remove os apps
    rm -rf "/Users/felipeleone/Documents/FitNutri/FitNutri.app"
    rm -rf "/Users/felipeleone/Documents/FitNutri/Parar FitNutri.app"
    echo "✅ Apps removidos!"
    echo "   Seus pacientes em pacientes/ foram preservados."
fi
REMOVE_SCRIPT

chmod +x "$PROJECT_DIR/Remover FitNutri.app/Contents/MacOS/Remover FitNutri"

cat > "$PROJECT_DIR/Remover FitNutri.app/Contents/Info.plist" << 'REMOVE_PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Remover FitNutri</string>
    <key>CFBundleIdentifier</key>
    <string>com.fitnutri.remove</string>
    <key>CFBundleName</key>
    <string>Remover FitNutri</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
REMOVE_PLIST

# ─── Cria script para criar atalho de Login (opcional) ──────────────────
cat > "$PROJECT_DIR/scripts/autostart.sh" << 'AUTOSTART'
#!/bin/bash
# Adiciona o FitNutri aos itens de login do macOS

APP_PATH="$HOME/Documents/FitNutri/FitNutri.app"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ FitNutri.app não encontrado em $APP_PATH"
    exit 1
fi

# Usa AppleScript para adicionar aos itens de login
osascript << EOF
tell application "System Events"
    set loginItems to get the name of every login item
    if "FitNutri" is not in loginItems then
        make login item at end with properties {path:"$APP_PATH", hidden:true}
        display notification "FitNutri adicionado à inicialização automática" with title "🏥 FitNutri"
    else
        display notification "FitNutri já está nos itens de inicialização" with title "🏥 FitNutri"
    end if
end tell
EOF
echo "✅ FitNutri adicionado à inicialização automática!"
echo "   O servidor iniciará sempre que você fizer login."
AUTOSTART
chmod +x "$PROJECT_DIR/scripts/autostart.sh"

echo ""
echo "✅ App criado: ${APP_NAME}.app"
echo "   📁 $APP_DIR"
echo ""
echo "🎯 USO:"
echo "   1. Abra o ${APP_NAME}.app (dê dois cliques)"
echo "   → O servidor inicia em background"
echo "   → O navegador abre no dashboard"
echo ""
echo "   2. Para parar: abra 'Parar FitNutri.app'"
echo ""
echo "   3. Para iniciar automático no login:"
echo "      bash scripts/autostart.sh"
echo ""
echo "📂 Os pacientes ficam em: pacientes/"
echo ""
