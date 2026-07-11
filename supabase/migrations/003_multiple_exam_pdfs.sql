-- Suporte a múltiplos PDFs de exames por atendimento.

alter table public.fitnutri_jobs
  add column if not exists exam_files jsonb not null default '[]'::jsonb;

update public.fitnutri_jobs
set exam_files = jsonb_build_array(
  jsonb_strip_nulls(
    jsonb_build_object(
      'id', 'legacy',
      'path', exam_file_path,
      'name', exam_file_name,
      'size', exam_file_size,
      'page_count', exam_page_count,
      'text_length', exam_text_length,
      'warning', exam_extract_warning
    )
  )
)
where exam_file_path is not null
  and exam_files = '[]'::jsonb;

update storage.buckets
set file_size_limit = 6000000,
    allowed_mime_types = array['application/pdf']::text[]
where id = 'fitnutri-exames';
