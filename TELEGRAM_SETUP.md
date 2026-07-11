# Setup Telegram Bot para FitNutri

## Passo 1 — Criar o Bot (2 minutos)
1. Abra o Telegram e procure por **@BotFather**
2. Envie o comando: `/newbot`
3. Nome: `FitNutri Clínica`
4. Username: `fitnutri_clinica_bot` (ou similar)
5. Copie o **HTTP API Token** gerado (algo como `123456:ABCdef...`)

## Passo 2 — Configurar no Hermes
Após obter o token, execute:

```bash
# Adicionar ao config.yaml do perfil fitnutri
hermes config set --profile fitnutri telegram.bot_token "SEU_TOKEN_AQUI"
hermes config set --profile fitnutri telegram.allowed_user_ids "[SEU_TELEGRAM_ID]"
hermes config set --profile fitnutri telegram.reactions true

# Reiniciar o gateway com o novo perfil
hermes gateway restart --profile fitnutri
```

## Passo 3 — Testar
1. No Telegram, procure por `@fitnutri_clinica_bot`
2. Envie: `/start`
3. Teste: "Liste os pacientes da FitNutri"
