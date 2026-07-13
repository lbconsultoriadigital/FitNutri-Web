-- PDF privado de exames e metadados de extração.

alter table public.fitnutri_jobs
  add column if not exists exam_file_path text,
  add column if not exists exam_file_name text,
  add column if not exists exam_file_size bigint,
  add column if not exists exam_page_count integer,
  add column if not exists exam_text_length integer,
  add column if not exists exam_extract_warning text;

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'fitnutri-exames',
  'fitnutri-exames',
  false,
  4000000,
  array['application/pdf']::text[]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Nenhuma policy pública é criada. O backend acessa o bucket com service_role.
