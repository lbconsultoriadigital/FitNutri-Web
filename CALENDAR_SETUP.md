# Google Calendar Setup para FitNutri

## Passo 1 — Criar Projeto no Google Cloud (10 minutos)
1. Acesse https://console.cloud.google.com
2. Crie um novo projeto: "FitNutri"
3. Habilite as APIs:
   - Google Calendar API
   - Google Sheets API
4. Vá em "APIs & Services" → "Credentials"
5. Crie um "OAuth 2.0 Client ID"
   - Application type: "Desktop app"
   - Name: "FitNutri Hermes"
6. Baixe o JSON como `client_secret.json`

## Passo 2 — Configurar no Hermes
```bash
# Copiar o client secret para o Hermes
cp ~/Downloads/client_secret.json ~/.hermes/

# Rodar o setup OAuth
python ~/.hermes/skills/productivity/google-workspace/scripts/setup.py \
  --client-secret ~/.hermes/client_secret.json \
  --services calendar,sheets

# Seguir o link de autorização no browser
# Colar o código de autorização de volta
```

## Passo 3 — Testar
```bash
# Listar eventos da semana
python ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py calendar list

# Criar evento de teste
python ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py calendar create \
  --summary "TESTE: Consulta FitNutri" \
  --start "$(date -v+1d +%Y-%m-%d)T14:00:00-03:00" \
  --end "$(date -v+1d +%Y-%m-%d)T14:50:00-03:00"
```

## Calendários Recomendados
- **Consultas FitNutri** (calendário principal)
- **Retornos** (calendário separado para follow-ups)
- **Felipe Pessoal** (bloqueios de indisponibilidade)

## Horários de Atendimento
```
Segunda-Sexta: 08:00-18:00
Sábado: 08:00-12:00 (opcional)
Domingo: Fechado

Duração padrão: 50 minutos (primeira consulta)
Retorno: 30 minutos
Intervalo: 10 minutos entre consultas
```
