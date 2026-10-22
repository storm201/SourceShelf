-- ============================================================================
--  SourceShelf — Supabase schema
--
--  Paste this whole file into:  Supabase dashboard → SQL Editor → New query → Run
--  It is idempotent: safe to run again later (upgrades, no data loss).
--
--  Design notes
--    • `apps` is the source of truth for the catalog.
--    • `first_seen` is the important column: it never changes once a row exists,
--      which is what makes "newly added today" possible across days.
--    • `runs` is a crawl log, so you can prove the automation is alive.
--    • Row Level Security is ON: anonymous (browser) traffic can only SELECT.
--      Writes require the service_role key, which only lives in GitHub Actions.
-- ============================================================================

-- ------------------------------------------------------------------ tables
create table if not exists public.apps (
  id               text primary key,              -- "owner/repo"
  name             text        not null,
  owner            text        not null,
  url              text        not null,
  homepage         text,
  description      text        not null default '',
  stars            integer     not null default 0,
  forks            integer     not null default 0,
  language         text,
  license          text,
  category         text        not null default 'Other',
  platforms        text[]      not null default '{}',
  topics           text[]      not null default '{}',
  repo_created_at  date,
  repo_pushed_at   date,
  release          jsonb,                          -- latest release + assets
  first_seen       date        not null default current_date,
  last_seen        date        not null default current_date,
  updated_at       timestamptz not null default now()
);

create table if not exists public.runs (
  id              bigint generated always as identity primary key,
  ran_at          timestamptz not null default now(),
  app_count       integer     not null default 0,
  new_count       integer     not null default 0,
  with_downloads  integer     not null default 0,
  source          text        default 'github-actions'
);

-- -------------------------------------------------------------- fast reads
create index if not exists apps_stars_idx      on public.apps (stars desc);
create index if not exists apps_first_seen_idx on public.apps (first_seen desc);
create index if not exists apps_category_idx   on public.apps (category);
create index if not exists apps_platforms_idx  on public.apps using gin (platforms);
create index if not exists apps_newest_idx     on public.apps (first_seen desc, stars desc);

-- ------------------------------------------------------------ handy view
-- Everything discovered in the last 7 days, newest first.
create or replace view public.new_arrivals as
  select id, name, owner, url, description, stars, category, platforms,
         license, release, first_seen
  from public.apps
  where first_seen >= (current_date - interval '7 days')
  order by first_seen desc, stars desc;

-- Daily counts, for badges/charts. `security_invoker` keeps RLS in force.
create or replace view public.daily_additions
  with (security_invoker = true) as
  select first_seen as day, count(*)::int as added
  from public.apps
  where first_seen >= (current_date - interval '90 days')
  group by first_seen
  order by first_seen desc;

-- ------------------------------------------------------------ security
alter table public.apps enable row level security;
alter table public.runs enable row level security;

-- Public, read-only access for the website (anon key is safe to expose).
drop policy if exists "apps are publicly readable"  on public.apps;
create policy "apps are publicly readable"
  on public.apps for select to anon, authenticated using (true);

drop policy if exists "runs are publicly readable" on public.runs;
create policy "runs are publicly readable"
  on public.runs for select to anon, authenticated using (true);

-- Belt and braces: anon can read, never write. (service_role bypasses RLS,
-- so the crawler still works.)
revoke insert, update, delete on public.apps from anon, authenticated;
revoke insert, update, delete on public.runs from anon, authenticated;
grant  select on public.apps to anon, authenticated;
grant  select on public.runs to anon, authenticated;
grant  select on public.new_arrivals to anon, authenticated;
grant  select on public.daily_additions to anon, authenticated;

-- ------------------------------------------------------------------ realtime
-- Intentionally omitted. The site polls the REST API (see liveRefresh() in
-- assets/app.js) and never opens a websocket, so no publication is needed.
--
-- Do NOT add `alter publication supabase_realtime add table public.apps;` here.
-- Supabase already puts new tables in that publication automatically, so the
-- statement aborts the whole script with:
--     ERROR 42710: relation "apps" is already member of publication
-- That is also why this file is safe to re-run: every statement above is
-- idempotent (create ... if not exists / create or replace / drop policy if exists).

-- ------------------------------------------------------------ sanity check
-- After running, this should return one row with 0 apps on a fresh database.
select
  (select count(*) from public.apps)  as apps,
  (select count(*) from public.runs)  as runs,
  (select count(*) from public.apps where first_seen = current_date) as added_today;
