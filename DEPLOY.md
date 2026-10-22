# Deploying SourceShelf (100% free)

Follow this once, top to bottom. Takes about 15 minutes. Nothing here costs money.

```
   your PC                        GitHub                          Supabase
┌──────────┐              ┌────────────────────┐            ┌──────────────┐
│ edit +   │   git push   │ Actions (nightly)  │   writes   │ apps table   │
│ test     │ ───────────► │  crawl → build     │ ─────────► │ first_seen   │
│ locally  │              │  → commit → deploy │            │ crawl log    │
└──────────┘              └─────────┬──────────┘            └──────┬───────┘
                                    │ GitHub Pages                  │ read
                                    ▼                               ▼
                            https://you.github.io/sourceshelf  →  visitors
```

---

## Step 0 — what you need

| thing | cost | why |
|---|---|---|
| GitHub account | free | hosts the code, runs the cron, serves Pages |
| Supabase account | free tier | stores app history so "new today" is real |
| nothing else | — | no server, no domain, no credit card |

> **Supabase is optional.** With no database the site still builds and deploys —
> history just lives in the committed `data/apps.json` instead. You get the same
> "new arrivals" section; you lose the queryable history across machines.

---

## Step 1 — Supabase (5 min)

1. Go to **https://supabase.com** → *Start your project* → sign in with GitHub.
2. **New project.** Name it `sourceshelf`, pick the region closest to you
   (`ap-south-1 / Mumbai` for India), set a database password, choose the **Free** plan.
   Wait ~2 minutes for provisioning.
3. Open **SQL Editor** → *New query* → paste the **entire** contents of
   [`supabase/schema.sql`](supabase/schema.sql) → **Run**.
   You should see a result row with `apps: 0`, `runs: 0`, `added_today: 0`.
4. Go to **Project Settings → Data API** and copy:
   - **Project URL** → looks like `https://abcdefgh.supabase.co`
   - **anon / public** key → safe to publish
5. Go to **Project Settings → API Keys** and copy the **service_role / secret** key.
   ⚠️ This one bypasses Row Level Security. It goes in GitHub Secrets and your
   local `.env` **only** — never in the repo, never in the browser.

**Free tier limits, for reference:** 500 MB database, 5 GB bandwidth, 50k monthly
active users. Our table is ~1,600 rows × ~1 KB ≈ 2 MB, so you're at ~0.4% of the
free database. It will not be the thing that breaks.

---

## Step 2 — test it on your PC first

```bash
cd sourceshelf
cp .env.example .env          # then paste your URL + keys into .env
```

Run the pre-flight check — it probes every endpoint before you deploy:

```bash
python3 scripts/selftest.py
```

You want `0 failed`. Supabase lines should read:

```
PASS  .env loaded
PASS  SUPABASE_URL — https://xxxx.supabase.co
PASS  REST endpoint reachable
PASS  apps table readable
PASS  write access (service key)
```

If it says *table public.apps does not exist*, Step 1.3 didn't run — paste
`schema.sql` again.

Then do a real crawl:

```bash
python3 scripts/update.py           # full update
# or, much faster (keeps download links, still finds new apps):
python3 scripts/update.py --quick
```

Open `sourceshelf.html`. First run **seeds** the database: it records a discovery
date for every app but marks nothing as new — otherwise day one would claim
"1,619 new apps today", which is meaningless. From the *next* run onward, only
genuinely new repos appear in **New arrivals**.

Check the rows landed:

```bash
python3 scripts/supabase_store.py --stats
python3 scripts/supabase_store.py --new 7
```

---

## Step 3 — push to GitHub

```bash
git init
git add .
git commit -m "SourceShelf: open-source app radar"
git branch -M main
git remote add origin https://github.com/YOURNAME/sourceshelf.git
git push -u origin main
```

`.env` is git-ignored, so your service key can't leak. Verify with
`git ls-files | grep env` — it should print nothing.

---

## Step 4 — add your secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| name | value | required |
|---|---|---|
| `SUPABASE_URL` | `https://xxxx.supabase.co` | for history |
| `SUPABASE_SERVICE_KEY` | the service_role key | for history (writes) |
| `SUPABASE_ANON_KEY` | the anon key | for live refresh on the site |

No `GITHUB_TOKEN` needed — Actions provides one automatically with 5,000 requests/hour.

Also add an optional **variable** (same page, *Variables* tab):

| name | value |
|---|---|
| `SITE_URL` | `https://YOURNAME.github.io/sourceshelf` (used in the RSS feed) |

---

## Step 5 — turn on Pages

1. Repo → **Settings → Pages**
2. **Source: GitHub Actions** (not "Deploy from a branch")
3. Go to the **Actions** tab → *Refresh catalog & deploy* → **Run workflow** → *Run*

First run takes ~5–10 minutes. When it finishes:

- **Overview** shows a summary: apps in catalog, new today, download links
- The **deploy** job prints your URL: `https://YOURNAME.github.io/sourceshelf/`
- Your data commit appears: `chore(data): refresh catalog 2026-10-22 [+9 new]`

After that it runs **by itself at 03:17 UTC every night** (08:47 IST). Your PC does
not need to be on.

---

## Step 6 — confirm the automation is alive

```bash
# run this after the first scheduled run
python3 scripts/supabase_store.py --stats
```

`runs` should have grown by one per night. The website header shows
`updated Oct 22`, and the **New arrivals** badge counts what was added in the
last 7 days.

---

## What ends up where

| path | what it is | who serves it |
|---|---|---|
| `/` | the site (single self-contained HTML) | GitHub Pages |
| `/data/apps.json` | full catalog, machine readable | GitHub Pages |
| `/data/new-arrivals.json` | **new apps, grouped by day** | GitHub Pages |
| `/feed.xml` | RSS feed of new arrivals | GitHub Pages |
| `/rest/v1/apps` | the table behind it all | Supabase |

All four web endpoints are static files on Pages — free, unlimited bandwidth,
no cold starts. Supabase is only read by the *optional* live refresh; if it's
down or slow the page still renders from the baked data.

```bash
# verify the endpoints once deployed
curl -s https://YOURNAME.github.io/sourceshelf/data/new-arrivals.json | head -20
curl -s https://YOURNAME.github.io/sourceshelf/feed.xml | head -12
```

---

## Troubleshooting

**`selftest.py` says "table public.apps does not exist"**
Re-run `supabase/schema.sql` in the SQL editor. The whole file, not one statement.

**Actions fails at "Crawl GitHub" with 403**
You hit the API rate limit. The built-in token gives 5,000/hr which a normal run
doesn't exhaust — check for a stray `GITHUB_TOKEN` secret overriding it with a
weak token. Delete any such secret.

**Actions fails at "Deploy to GitHub Pages"**
Settings → Pages → Source must be **GitHub Actions**. Also check
Settings → Actions → General → Workflow permissions allows read/write.

**The deploy step is skipped**
The `deploy` job needs the artifact from `refresh`. If crawl fails, deploy is
skipped by design — fix the crawl first.

**New arrivals stays empty**
Expected on seeding day. After the second run it fills. If it still won't:
`python3 scripts/supabase_store.py --new 7` — if that returns rows, the data is
there and the issue is the build; run `python3 scripts/build_single.py`.

**Everything shows as new one day**
The history read failed and fell back to local. Check `SUPABASE_URL`/`SERVICE_KEY`
secrets and re-run. The schema's RLS only allows SELECT for anon, so writes need
the service key.

**Site is stale after a green run**
Pages caches briefly. Hard-refresh once (Ctrl/Cmd+Shift+R).

**Rate limited locally / crawl takes forever**
Set `GITHUB_TOKEN` in `.env`. Free, no scopes, 80× the quota.

---

## Cost ledger

| item | usage | cost |
|---|---|---|
| GitHub Actions | ~10 min/night ≈ 300 min/month, limit 2,000 on free | **₹0** |
| GitHub Pages | static, 100 GB/month soft limit | **₹0** |
| Supabase | ~2 MB of 500 MB, ~5k rows/month of 50k MAU | **₹0** |
| Domain | `*.github.io` subdomain | **₹0** |

> GitHub disables scheduled workflows on repos with **60 days of no activity**.
> The nightly job commits every day, which itself counts as activity — so the
> automation keeps itself alive.

---

## Running it locally, without GitHub

```bash
python3 scripts/update.py      # crawl + rebuild
python3 scripts/serve.py       # preview at localhost:8080
python3 scripts/selftest.py    # verify everything
```

Schedule it (see README) if you'd rather not use Actions — but note your PC has to
be awake at the scheduled time, and history then depends on the local
`data/apps.json` unless Supabase is configured.
