# FitNutri — implantação da fundação assíncrona

## Arquitetura

- Vercel: interface estática e API FastAPI.
- Supabase: persistência dos atendimentos, contexto e laudos.
- Upstash QStash: uma execução por etapa do pipeline.
- DeepSeek: processamento dos seis agentes.
- Aprovação humana: o laudo termina em `review_required` e precisa ser aprovado por profissional habilitado.

## Supabase

Projeto criado:

- Nome: `FitNutri`
- Referência: `awpuljvcikhehxvrxyvx`
- Região: `sa-east-1`

A migration está em:

```text
supabase/migrations/001_fitnutri_jobs.sql
```

Ela já foi aplicada no projeto acima.

A tabela `public.fitnutri_jobs` está com RLS habilitado e sem acesso para `anon` e `authenticated`. A aplicação deve acessar o banco somente pelo backend usando a service role.

## Variáveis obrigatórias na Vercel

```text
ENVIRONMENT=production
PUBLIC_APP_URL=https://SEU-DOMINIO.vercel.app
ALLOWED_ORIGINS=https://SEU-DOMINIO.vercel.app

FITNUTRI_ADMIN_PASSWORD=<senha forte>
FITNUTRI_SESSION_SECRET=<segredo aleatório longo>
FITNUTRI_WORKER_TOKEN=<segredo aleatório longo>

SUPABASE_URL=https://awpuljvcikhehxvrxyvx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<chave secreta, somente no servidor>

QSTASH_TOKEN=<token do QStash>

DEEPSEEK_API_KEY=<chave DeepSeek>
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL_FLASH=<modelo rápido disponível na conta>
DEEPSEEK_MODEL_PRO=<modelo de raciocínio disponível na conta>
DEEPSEEK_TIMEOUT_SECONDS=180
```

Nunca exponha `SUPABASE_SERVICE_ROLE_KEY`, `QSTASH_TOKEN`, `FITNUTRI_WORKER_TOKEN` ou `DEEPSEEK_API_KEY` no frontend.

## Upstash QStash

1. Crie ou use uma conta Upstash.
2. Abra o QStash e copie o token.
3. Configure `QSTASH_TOKEN` na Vercel.
4. Configure `FITNUTRI_WORKER_TOKEN` com um valor aleatório forte.
5. O backend encaminhará esse token como `Authorization` ao endpoint `/api/jobs/process`.

## Fluxo

```text
POST /api/atendimentos
  → cria job no Supabase
  → publica etapa 1 no QStash
  → cada etapa salva o contexto
  → publica a próxima etapa
  → etapa 6 gera os artefatos
  → status review_required
  → profissional revisa e aprova
  → status approved
```

## Checklist antes do merge

- [ ] Variáveis da Vercel configuradas nos ambientes Preview e Production.
- [ ] QStash configurado.
- [ ] Deployment Preview concluído.
- [ ] `/api/health` retorna `operational`.
- [ ] Login testado.
- [ ] Atendimento fictício percorre as seis etapas.
- [ ] Laudo aparece em `review_required`.
- [ ] Aprovação registra nome e número profissional.
- [ ] Nenhum segredo aparece no bundle do navegador ou nos logs.

## Smoke test

```bash
curl https://SEU-DOMINIO.vercel.app/api/health
```

Resposta esperada depois da configuração:

```json
{
  "status": "operational",
  "version": "2.0.0"
}
```

Não faça merge apenas porque o build passou. Valide o fluxo assíncrono completo no deployment Preview com dados fictícios.
