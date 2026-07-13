# FitNutri — protótipo funcional

## Entrega

O protótipo inclui dashboard premium, autenticação, cadastro de anamnese, upload privado de exames em PDF, extração de texto, execução dos seis agentes, acompanhamento por etapa, laudo em revisão e aprovação profissional.

## Supabase

- Projeto: `FitNutri`
- Referência: `awpuljvcikhehxvrxyvx`
- Região: `sa-east-1`
- Bucket privado: `fitnutri-exames`
- Limite do PDF: 4 MB

Migrations:

```text
supabase/migrations/001_fitnutri_jobs.sql
supabase/migrations/002_exam_pdf_storage.sql
```

## Modo do protótipo

```text
FITNUTRI_DISPATCH_MODE=manual
```

O painel executa uma etapa por requisição em `/api/atendimentos/{id}/advance`, até concluir os seis agentes. QStash permanece disponível como modo opcional de produção.

## Variáveis da Vercel

```text
ENVIRONMENT=production
PUBLIC_APP_URL=https://SEU-DOMINIO.vercel.app
ALLOWED_ORIGINS=https://SEU-DOMINIO.vercel.app
FITNUTRI_ADMIN_PASSWORD=<senha forte>
FITNUTRI_SESSION_SECRET=<segredo longo>
FITNUTRI_DISPATCH_MODE=manual
FITNUTRI_EXAM_BUCKET=fitnutri-exames
FITNUTRI_MAX_PDF_BYTES=4000000
FITNUTRI_MAX_EXAM_TEXT=60000
SUPABASE_URL=https://awpuljvcikhehxvrxyvx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<somente servidor>
DEEPSEEK_API_KEY=<chave>
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL_FLASH=deepseek-v4-flash
DEEPSEEK_MODEL_PRO=deepseek-v4-pro
DEEPSEEK_TIMEOUT_SECONDS=240
```

Não exponha chaves secretas no frontend.

## Limitações

- PDFs sem camada textual são armazenados, mas precisam de OCR ou transcrição posterior.
- No modo manual, o navegador deve permanecer aberto durante as seis etapas.
- O merge deve ocorrer somente após um atendimento fictício completo no Preview.

## Validações

- Compilação de todos os módulos Python.
- Validação sintática dos cinco arquivos JavaScript.
- Migration e bucket privado verificados no Supabase.
- Build Preview da Vercel concluído com sucesso.
