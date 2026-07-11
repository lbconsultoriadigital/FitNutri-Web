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
