#!/bin/bash
# ────────────────────────────────────────────────────────────────────
# FitNutri — Cron Jobs de Follow-up e Lembretes
# ────────────────────────────────────────────────────────────────────

# ═══ LEMBRETES PRÉ-CONSULTA ═══

# Lembrete 24h antes — todo dia às 8h
hermes cron create "every day at 8am America/Sao_Paulo" \
  "Check tomorrow's Google Calendar for FitNutri appointments.
   For each patient found, send a Telegram message to Felipe summarizing the day's schedule.
   If patient has phone/WhatsApp, draft a reminder message for Felipe to approve."

# Lembrete 1h antes — todo dia às 7h, 9h, 13h, 15h, 17h
hermes cron create "every day at 7am,9am,1pm,3pm,5pm America/Sao_Paulo" \
  "Check Google Calendar for FitNutri appointments starting in 1 hour.
   Send Felipe a quick Telegram reminder: 'Consulta com {nome} em 1h às {hora}'"

# ═══ FOLLOW-UP PÓS-CONSULTA ═══

# Follow-up 24h depois — todo dia às 18h
hermes cron create "every day at 6pm America/Sao_Paulo" \
  "Check yesterday's completed FitNutri appointments in Google Calendar.
   For each patient, draft a follow-up message: 'Olá {nome}! Como está se sentindo após a consulta de ontem? Tem alguma dúvida sobre o plano?'
   Send the drafts to Felipe on Telegram for approval."

# Follow-up 7 dias — todo dia às 10h
hermes cron create "every day at 10am America/Sao_Paulo" \
  "Check FitNutri appointments from 7 days ago.
   Draft: 'Já faz uma semana! Como está a adaptação ao plano alimentar e treino? Tem dúvidas?'
   Send drafts to Felipe for approval."

# Follow-up 30 dias — todo dia às 11h
hermes cron create "every day at 11am America/Sao_Paulo" \
  "Check FitNutri appointments from 30 days ago.
   Draft: 'Olá {nome}! Completamos um mês desde sua consulta. Que tal agendarmos uma reavaliação para ver seu progresso?'
   Send drafts to Felipe for approval."

# ═══ ALERTAS ═══

# Alerta de no-show — todo dia às 9h30
hermes cron create "every day at 9:30am America/Sao_Paulo" \
  "Check today's FitNutri appointments that started before 9:30am.
   If any patient hasn't been marked as 'attended', alert Felipe on Telegram."

# Resumo semanal — toda segunda às 7h
hermes cron create "every monday at 7am America/Sao_Paulo" \
  "Generate a weekly summary for Felipe:
   - Total appointments this week
   - Patients seen vs no-shows
   - Follow-ups pending
   - New patients registered
   Send as Telegram message."
