-- Mantém cada PDF abaixo do limite seguro de corpo das Vercel Functions.

update storage.buckets
set file_size_limit = 4000000,
    allowed_mime_types = array['application/pdf']::text[]
where id = 'fitnutri-exames';
