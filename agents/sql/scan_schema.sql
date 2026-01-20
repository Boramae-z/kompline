create table if not exists public.scans (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  repo_url text not null,
  status text not null check (status in ('QUEUED', 'PROCESSING', 'REPORT_GENERATING', 'COMPLETED', 'FAILED')),
  report_url text
);

create table if not exists public.scan_documents (
  scan_id uuid not null references public.scans(id) on delete cascade,
  document_id integer not null references public.documents(id) on delete cascade,
  primary key (scan_id, document_id)
);

create table if not exists public.scan_results (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid not null references public.scans(id) on delete cascade,
  compliance_item_id integer not null references public.compliance_items(id) on delete cascade,
  status text not null check (status in ('PENDING', 'PASS', 'FAIL', 'ERROR')),
  reasoning text,
  evidence text,
  updated_at timestamptz not null default now()
);

create index if not exists idx_scan_results_scan_id on public.scan_results (scan_id);
create index if not exists idx_scan_results_status on public.scan_results (status);
