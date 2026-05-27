-- SRNHS School Profile Analysis Dashboard
-- Online storage schema for Flask server + Supabase Postgres.
-- The Flask backend connects server-side using SUPABASE_SECRET_KEY or legacy SUPABASE_SERVICE_ROLE_KEY.
-- Do not expose that key in browser code or GitHub.

create table if not exists public.dashboard_settings (
  id integer primary key,
  dashboard_title text not null,
  school_name text not null,
  location text not null,
  subtitle text not null,
  logo_url text not null,
  login_background_url text not null,
  main_green text not null default '#168447',
  sidebar_color text not null default '#071B12',
  page_background text not null default '#F8FBF8',
  updated_at timestamptz,
  updated_by text
);

create table if not exists public.account_holders (
  id bigint generated always as identity primary key,
  full_name text not null,
  username text not null unique,
  password_hash text not null,
  avatar_url text default '',
  account_status text not null default 'Active',
  last_active timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.school_records (
  id bigint generated always as identity primary key,
  school_year text not null,
  level text not null check (level in ('JHS','SHS')),
  grade_level text not null,
  enrollment integer not null default 0 check (enrollment >= 0),
  dropouts integer not null default 0 check (dropouts >= 0),
  repeaters integer not null default 0 check (repeaters >= 0),
  teachers integer not null default 0 check (teachers >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by text,
  unique (school_year, grade_level)
);

create table if not exists public.resources (
  id bigint generated always as identity primary key,
  school_year text not null unique,
  jhs_classrooms integer not null default 0 check (jhs_classrooms >= 0),
  shs_classrooms integer not null default 0 check (shs_classrooms >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by text
);

create table if not exists public.room_sizes (
  id bigint generated always as identity primary key,
  grade_level text not null unique,
  room_length numeric not null check (room_length >= 0),
  room_width numeric not null check (room_width >= 0),
  updated_at timestamptz not null default now(),
  updated_by text
);

create table if not exists public.cohort_records (
  id bigint generated always as identity primary key,
  school_year text not null unique,
  baseline_year text not null,
  grade7_baseline integer not null check (grade7_baseline >= 0),
  grade12_current integer not null check (grade12_current >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by text
);

create table if not exists public.action_plans (
  id bigint generated always as identity primary key,
  school_year text not null,
  analysis_type text not null default 'Prescriptive',
  focus_area text not null,
  observed_pattern text not null,
  data_basis text,
  suggested_action text not null,
  responsible_group text not null,
  target_indicator text,
  baseline_value text,
  target_value text,
  monitoring_period text,
  current_result text,
  status text not null default 'Suggested',
  progress_notes text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by text
);

alter table public.action_plans add column if not exists analysis_type text not null default 'Prescriptive';
alter table public.action_plans add column if not exists data_basis text;
alter table public.action_plans add column if not exists target_indicator text;
alter table public.action_plans add column if not exists baseline_value text;
alter table public.action_plans add column if not exists target_value text;
alter table public.action_plans add column if not exists monitoring_period text;
alter table public.action_plans add column if not exists current_result text;
alter table public.action_plans add column if not exists progress_notes text;

create table if not exists public.change_history (
  id bigint generated always as identity primary key,
  occurred_at timestamptz not null default now(),
  display_name text not null,
  action_label text not null,
  snapshot_json text not null,
  undone boolean not null default false,
  undone_at timestamptz
);

create table if not exists public.activity_logs (
  id bigint generated always as identity primary key,
  occurred_at timestamptz not null default now(),
  account_holder_id bigint references public.account_holders(id) on delete set null,
  display_name text not null,
  action text not null,
  section text not null,
  affected_record text,
  details text
);

create table if not exists public.report_exports (
  id bigint generated always as identity primary key,
  report_name text not null,
  exported_by text not null,
  exported_at timestamptz not null default now(),
  selected_years text,
  format text not null
);

create table if not exists public.workbook_exports (
  id bigint generated always as identity primary key,
  exported_by text not null,
  exported_at timestamptz not null default now(),
  file_name text not null,
  included_school_years text
);

create index if not exists idx_school_records_year on public.school_records(school_year);
create index if not exists idx_activity_occurred on public.activity_logs(occurred_at desc);
create index if not exists idx_actions_year on public.action_plans(school_year);
create index if not exists idx_change_history_time on public.change_history(occurred_at desc);

-- Keep direct browser/API access closed. The Flask server accesses these tables
-- using a server-only service key. RLS is enabled with no public policies.
alter table public.dashboard_settings enable row level security;
alter table public.account_holders enable row level security;
alter table public.school_records enable row level security;
alter table public.resources enable row level security;
alter table public.room_sizes enable row level security;
alter table public.cohort_records enable row level security;
alter table public.action_plans enable row level security;
alter table public.change_history enable row level security;
alter table public.activity_logs enable row level security;
alter table public.report_exports enable row level security;
alter table public.workbook_exports enable row level security;

-- Server-side Flask access. Keep SUPABASE_SECRET_KEY or legacy SUPABASE_SERVICE_ROLE_KEY only in hosting secrets.
grant select, insert, update, delete on table public.dashboard_settings to service_role;
grant select, insert, update, delete on table public.account_holders to service_role;
grant select, insert, update, delete on table public.school_records to service_role;
grant select, insert, update, delete on table public.resources to service_role;
grant select, insert, update, delete on table public.room_sizes to service_role;
grant select, insert, update, delete on table public.cohort_records to service_role;
grant select, insert, update, delete on table public.action_plans to service_role;
grant select, insert, update, delete on table public.change_history to service_role;
grant select, insert, update, delete on table public.activity_logs to service_role;
grant select, insert, update, delete on table public.report_exports to service_role;
grant select, insert, update, delete on table public.workbook_exports to service_role;
grant usage, select on all sequences in schema public to service_role;
