-- Persistência do pipeline FitNutri.

create extension if not exists pgcrypto;

create table if not exists public.fitnutri_jobs (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  patient_name text not null,
  input_data jsonb not null default '{}'::jsonb,
  context_data jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (
    status in ('queued','running','review_required','approved','failed','cancelled')
  ),
  current_stage integer not null default 0 check (current_stage between 0 and 6),
  stage_attempts integer not null default 0,
  error_message text,
  laudo_json jsonb,
  laudo_markdown text,
  laudo_html text,
  reviewer_name text,
  registration_type text,
  registration_number text,
  review_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  approved_at timestamptz
);

create index if not exists fitnutri_jobs_created_at_idx
  on public.fitnutri_jobs (created_at desc);
create index if not exists fitnutri_jobs_status_idx
  on public.fitnutri_jobs (status, current_stage);

alter table public.fitnutri_jobs enable row level security;
revoke all on table public.fitnutri_jobs from anon, authenticated;
grant select, insert, update, delete on table public.fitnutri_jobs to service_role;

create or replace function public.claim_fitnutri_job(p_job_id uuid, p_stage integer)
returns setof public.fitnutri_jobs
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  update public.fitnutri_jobs
     set status = 'running',
         stage_attempts = stage_attempts + 1,
         updated_at = now()
   where id = p_job_id
     and current_stage = p_stage - 1
     and status in ('queued', 'running')
  returning *;
end;
$$;

revoke all on function public.claim_fitnutri_job(uuid, integer) from public, anon, authenticated;
grant execute on function public.claim_fitnutri_job(uuid, integer) to service_role;
