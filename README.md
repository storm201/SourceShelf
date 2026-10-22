# 📡 SourceShelf

> **Current catalog: 1,619 apps · 23 categories · 10 platforms · 276 with direct
> download links**, crawled live from the GitHub API.
>
> ▶️ **Just want the commands? → [RUN.md](RUN.md)** — 27 numbered steps, one action each.
>
> 👶 **Never done this before? → [START-HERE.md](START-HERE.md)** — click-by-click,
> every step with "how to know it worked".
>
> ⚡ **Already know your way around? → [DEPLOY.md](DEPLOY.md)** — the compact version.

A fast, filterable directory of **popular open-source apps** — desktop, mobile, web,
CLI and self-hosted — crawled from GitHub every night. Instead of hunting through
a dozen `awesome-*` lists, you search one place and click **Download**.

- **Static site** → plain HTML/CSS/JS, no framework, no build step needed to view it
- **In-memory filtering** → search across thousands of apps in a few milliseconds
- **Direct downloads** → real release assets (`.exe`, `.dmg`, `.AppImage`, `.apk`, …)
  resolved from each repo's latest GitHub Release
- **Fully automated** → a scheduled GitHub Action re-crawls, re-classifies,
  commits and deploys every night
- **New arrivals** → a dedicated section showing exactly what was discovered each
  day, backed by `first_seen` history in Supabase
- **Free forever** → GitHub Actions + Pages + Supabase free tier; no server

---

## What's in the box

```
sourceshelf/
├── index.html              # app shell (production, multi-file)
├── assets/
│   ├── app.css             # design system, dark UI
│   └── app.js              # search + filter + render engine (vanilla)
├── data/
│   ├── apps.json           # canonical dataset (machine readable)
│   └── apps.js             # same data as window.__SOURCESHELF__ for the site
├── scripts/
│   ├── taxonomy.py         # categories, platforms, discovery queries, overrides
│   ├── fetch_apps.py       # the crawler
│   ├── update.py           # crawl + rebuild in one command
│   ├── build_single.py     # bundles html + JSON + RSS + config
│   ├── supabase_store.py   # PostgREST client (stdlib only)
│   ├── envcfg.py           # tiny .env loader
│   ├── selftest.py         # pre-flight check of every endpoint
│   ├── serve.py            # local preview server
│   └── review.py           # spot-check classifier output
├── sourceshelf.html          # single-file build — double-click it, or host anywhere
├── update.sh / update.bat  # one-command local updaters (macOS+Linux / Windows)
├── supabase/schema.sql     # paste into the Supabase SQL editor once
├── tests/test_supabase.py  # 22 checks against a mock PostgREST server
├── DEPLOY.md               # step-by-step free deployment guide
├── dist/                   # Pages artifact (generated)
└── .github/workflows/refresh.yml   # nightly crawl → build → commit → deploy
```


---

## How "New arrivals" works

The GitHub search API tells you what exists **today**. It cannot tell you what
appeared since yesterday — so history has to be stored somewhere.

| layer | role |
|---|---|
| `apps.first_seen` in Supabase | the source of truth. Set once when a repo is first seen, never rewritten. |
| `data/apps.json` | local fallback so the site works with no database |
| `meta.newArrivals` | what the build step ships to the browser, grouped by day |
| **New arrivals** tab | renders those groups: *Today · Yesterday · 3 days ago* |

Two things are deliberate:

- **Seeding run claims nothing.** The first crawl records discovery dates for
  every app but marks none as new. Otherwise day one would announce
  "1,619 new apps today", which is noise, not news.
- **`first_seen` never moves.** A daily upsert overwrites stars and descriptions
  but preserves the original discovery date, so an app can't drift into
  "new" twice.

Public artefacts the build produces:

| file | contents |
|---|---|
| `dist/data/apps.json` | full catalog |
| `dist/data/new-arrivals.json` | new apps grouped by day (last 7 days) |
| `dist/feed.xml` | RSS 2.0 feed — subscribe to get new apps in your reader |

### Verify the storage layer

No Supabase account needed — the client is tested against a local mock of
PostgREST:

```bash
python3 tests/test_supabase.py     # 22 assertions, all offline
```

It proves endpoint paths, auth headers, upsert semantics, 250-row batching,
1,000-row pagination, `first_seen` preservation, and clean errors on a bad key
(401) or a missing table (404).

---

## "Will I see new apps every day?" — the honest answer

**Only if something runs the crawler.** Downloading this folder gives you a
*snapshot*: `sourceshelf.html` has the catalog baked in, so opening it tomorrow shows
the same apps until you refresh the data. There are three ways to get daily freshness,
in order of how much I recommend them:

### Option 1 — GitHub Actions (recommended, zero maintenance)

Push this folder to a GitHub repo and forget about it. The included workflow runs at
03:17 UTC every night on GitHub's servers — your PC doesn't even need to be on.

1. Create a repo and push: `git init && git add . && git commit -m init`
   then `git remote add origin <your repo>` and `git push -u origin main`
2. Go to the **Actions** tab → *Refresh app catalog* → **Enable workflow**
3. (Optional, to publish a public URL) Settings → Pages → Source: **GitHub Actions**,
   and add a repository **variable** `DEPLOY_PAGES = true`

Fresh data is committed back to the repo daily, and the site is republished if you
enabled Pages. Cost: free.

### Option 2 — your own PC, on a schedule

If you'd rather keep it local, run `update.sh` (macOS/Linux) or `update.bat` (Windows)
on a timer. Each run re-crawls GitHub and rewrites `sourceshelf.html` — reload the page
and the new apps are there.

**Windows** (Task Scheduler):

1. Task Scheduler → **Create Basic Task** → Daily → pick a time
2. Action: **Start a program**
   - Program: `C:\Windows\System32\cmd.exe`
   - Arguments: `/c "C:\path\to\sourceshelf\update.bat --quick"`
   - Start in: `C:\path\to\sourceshelf`
3. Tick *Run whether user is logged on or not* if you want it to fire unattended

**macOS / Linux** (cron) — run `crontab -e` and add:

```cron
17 3 * * * /path/to/sourceshelf/update.sh >> /tmp/sourceshelf.log 2>&1
```

> `--quick` refreshes the catalog (new apps, star counts, descriptions) and keeps
> the previously resolved download links. A full `./update.sh` also re-resolves the
> links against each project's latest release — slower, since it visits one page per
> project, but it catches new versions.

### Option 3 — just run it manually

`./update.sh` whenever you feel like it, then refresh the browser. Perfectly fine if
you only care about new apps every week or two.

### Speeding up either local option

Create a free GitHub token (no scopes needed) and set it before running:

```bash
export GITHUB_TOKEN=ghp_xxx        # macOS/Linux
set GITHUB_TOKEN=ghp_xxx           # Windows cmd
$env:GITHUB_TOKEN="ghp_xxx"        # Windows PowerShell
```

That raises the API budget from 60 to 5,000 requests/hour, so a full crawl with
download links takes a couple of minutes instead of being throttled.

### Day-to-day commands

| I want to… | command |
|---|---|
| Update everything and rebuild | `./update.sh` |
| Fast refresh (star counts, new apps; keeps last known download links) | `./update.sh --quick` |
| Force a re-query (ignore the 20h cache) | `./update.sh --force` |
| Just look at the site | `python3 scripts/serve.py` then open `localhost:8080` |
| Only rebuild the HTML from current data | `python3 scripts/build_single.py` |

Nightly runs print their result, and both `data/apps.json` and the page carry a
`generatedAt` timestamp — the header of the site shows it as *"updated Oct 22"*.

---

## Run it locally

```bash
cd sourceshelf
python3 scripts/serve.py        # serves + opens http://localhost:8080
```

The site reads whatever is in `data/apps.js`, so no build step is required.
(Use a server, not `file://`, if you want search params to behave.)

### Refresh the catalog

```bash
# unauthenticated: 60 core + 10 search requests/hour — slow but works
python3 scripts/fetch_apps.py --min-stars 400 --releases 0

# with a token: 5000 core + 30 search requests/min — the real way
export GITHUB_TOKEN=ghp_yourtoken      # no scopes needed, just a classic/fine-grained PAT
python3 scripts/fetch_apps.py --min-stars 400 --releases 800
```

Useful flags:

| flag | meaning |
|---|---|
| `--min-stars N` | quality floor (default 400) |
| `--max-apps N` | hard cap on catalog size (default 4000) |
| `--releases N` | how many top repos get their download links resolved |
| `--queries N` | only run the first N discovery queries (debugging) |
| `--force` | ignore the 20-hour search cache in `cache/` |
| `--web` | resolve download links from the public release **web pages** instead of the REST API — no token, no quota |
| `--offline` | rebuild the dataset using only cached release data (no network) |

> **No token? No problem.** When the REST quota is spent, the crawler automatically
> falls back to reading `github.com/<repo>/releases` HTML (which isn't API rate
> limited) to find asset names, sizes and download URLs. `--web` forces that mode.

Then rebuild the portable single file:

```bash
python3 scripts/build_single.py     # → dist/index.html
```

---

## How the automation works

`.github/workflows/refresh.yml` runs **daily at 03:17 UTC**, and on demand from the
Actions tab (**Run workflow**).

```
schedule ─┬─> fetch_apps.py  ──> data/apps.json + data/apps.js
          ├─> build_single.py ──> dist/index.html
          └─> git commit + push  (or deploy to Pages)
```

1. Commit this folder to a GitHub repo.
2. Nothing else is required for data freshness — the workflow uses the built-in
   `GITHUB_TOKEN`, which is enough for a full crawl.
3. To also **publish the site**, set a repository variable
   `DEPLOY_PAGES = true` (Settings → Secrets and variables → Actions → Variables) and
   enable Pages → Source: *GitHub Actions*. The workflow then deploys `dist/`.

### Other free hosts

`dist/index.html` is a single self-contained file — drag it into Netlify Drop,
Cloudflare Pages, Vercel, or Surge and you're live. For a multi-file deploy, upload
`index.html`, `assets/` and `data/` (browser caching then works per-asset, which is
slightly faster on repeat visits).

---

## How apps are picked and sorted into categories

`scripts/taxonomy.py` holds three things you'll actually want to edit:

1. **`QUERIES`** — GitHub search strings like `topic:self-hosted stars:>1500`.
   Add a topic here and you widen the net. Each query pulls up to 100 repos.
2. **`CATEGORY_RULES` / `PLATFORM_RULES`** — keyword lists per category/platform.
   GitHub *topics* are the strongest signal, then the repo name, then the
   description. Short keywords (`ai`, `os`) are deliberately down-weighted so that
   "email" doesn't get filed under AI.
3. **`OVERRIDES`** — hand-pinned `repo → (category, platforms)` for the famous
   projects where guessing is silly (Jellyfin is Video & Streaming, Joplin is Notes).

`is_app()` throws out libraries, frameworks, curated lists, `awesome-*` repos,
cheatsheets, roadmaps and anything archived, so the catalog stays a list of things
you can actually *install*.

Check the classifier's work at any time:

```bash
python3 scripts/review.py            # per-category dump + suspicious entries
python3 scripts/review.py --cat "Media & Audio"
```

---

## Performance notes

- One JSON payload, parsed once; all filtering happens in a pre-indexed in-memory
  array (a lowercase search blob per app).
- Cards render in pages of 48 via `IntersectionObserver` — the DOM never holds
  4,000 nodes at once.
- Typing is debounced at 70 ms; every keystroke is a single `indexOf` pass per app.
- No web fonts, no CSS framework, no analytics, no external JS. Icons are inline SVG.
- Avatars degrade to letter tiles if GitHub is unreachable, so the layout never jumps.

Typical: ~150 KB HTML for the whole site plus ~1–3 MB of data, first paint well
under a second on a normal connection.

---

## Adding an app that the crawler missed

Two ways, in order of preference:

1. **Add a discovery query** — if the project has a topic the crawler doesn't search
   yet, add e.g. `"topic:my-niche stars:>500"` to `QUERIES` in `taxonomy.py`.
2. **Pin it** — add `"owner/repo": ("Category", ["Windows", "Linux"])` to `OVERRIDES`.
   Overrides always win and bypass the app-vs-library filter.

Pin the famous ones. Keyword scoring handles the long tail, but a curated
`OVERRIDES` entry is free accuracy.

## Notes & limits

- GitHub allows 5,000 authenticated API calls/hour. A full crawl uses ~70 search
  calls + one release call per repo you resolve — `--releases 800` fits comfortably.
- Repos whose developers publish installers elsewhere (e.g. their own website) will
  show **Get app**, which opens the Releases page. If there's no release at all,
  the detail panel explains the project is source/self-hosted only.
- Star counts are a popularity proxy, not a quality guarantee. Licenses are shown on
  every card; always check before redistributing.
- Data is refreshed daily, not live. Star counts are as of the last crawl.
