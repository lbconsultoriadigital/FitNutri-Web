# FitNutri — protótipo funcional

## O que está incluído

- Interface premium responsiva com a identidade FitNutri.
- Login administrativo por sessão HTTP-only.
- Cadastro completo de atendimento e anamnese.
- Upload privado de PDF de exames de até 4 MB.
- Extração de texto com `pypdf` para alimentar os agentes.
- Aviso quando o PDF parece escaneado e não possui camada de texto suficiente.
- Execução dos seis agentes em etapas independentes:
  1. Triagem
  2. Exames
  3. Suplementação
  4. Nutrição
  5. Treino
  6. Consolidação
- Visualização da saída estruturada de cada agente.
- Laudo final em `review_required`.
- Aprovação com nome, conselho e número de registro profissional.
- Persistência no Supabase e PDF em bucket privado.

## Supabase

Projeto:

- Nome: `FitNutri`
- Referência: `awpuljvcikhehxvrxyvx`
- Região: `sa-east-1`

Migrations:

```text
supabase/migrations/001_fitnutri_jobs.sql
supabase/migrations/002_exam_pdf_storage.sql
```

A segunda migration cria as colunas de metadados do exame e o bucket privado `fitnutri-exames`.

## Modos de processamento

### Protótipo — recomendado agora

```text
FITNUTRI_DISPATCH_MODE=manual
```

O painel chama `/api/atendimentos/{id}/advance` seis vezes, uma etapa por requisição. Isso torna o protótipo funcional sem depender de QStash e evita uma única requisição muito longa.

### Produção com fila

```text
FITNUTRI_DISPATCH_MODE=qstash
QSTASH_TOKEN=<token>
FITNUTRI_WORKER_TOKEN=<segredo>
```

Cada etapa é publicada no QStash e processada por `/api/jobs/process`.

## Variáveis obrigatórias na Vercel

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

Nunca exponha a service role do Supabase, a chave DeepSeek ou o token do worker no frontend.

## Fluxo funcional

```text
Login
  → novo atendimento
  → anamnese + PDF opcional
  → PDF armazenado no bucket privado
  → texto extraído e incorporado ao contexto
  → seis agentes executados em sequência
  → saídas intermediárias disponíveis no painel
  → laudo gerado como rascunho
  → revisão e aprovação profissional
```

## Limitações conhecidas do protótipo

- A Vercel limita o corpo da requisição de Functions a 4,5 MB; por segurança o upload foi limitado a 4 MB.
- `pypdf` extrai texto de PDFs com camada textual. PDFs totalmente escaneados exigirão OCR em uma etapa futura.
- O modo manual depende de o navegador permanecer aberto durante a execução dos seis agentes.
- O PR não deve ser mesclado antes de configurar os secrets e validar um atendimento fictício completo no Preview.

## Validação executada

```text
python -m py_compile api/index.py fitnutri/webapp/*.py
node --check public/app-core.js
node --check public/app-form.js
node --check public/app-list.js
node --check public/app-render.js
node --check public/app-run.js
Supabase: migration, bucket privado e permissões confirmados
Vercel Preview: build concluído com sucesso
```
