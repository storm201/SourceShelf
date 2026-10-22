# ▶️ How to run SourceShelf — numbered steps

Follow top to bottom. One command per step. Each step tells you what you should see.

**Python command:** use `python3` on macOS/Linux, `python` on Windows.
Below it's written as `python3` — swap it if needed.

> **On Windows this matters.** If `python3 --version` says *"is not recognized"* or opens
> the Microsoft Store, that's expected — `python3` is the Mac/Linux name.
> Run `python --version` instead, and use `python` for every command here.
> Still nothing? Try `py --version`.

---

# PHASE 1 — See it running (2 minutes, no setup)

### Step 1. Open a terminal in the project folder

- **Windows:** open the `sourceshelf` folder in File Explorer → click the address bar → type `powershell` → Enter
- **macOS:** open Terminal → type `cd ` (with a space) → drag the `sourceshelf` folder in → Enter
- **Linux:** right-click the folder → *Open in Terminal*

### Step 2. Confirm you're in the right folder

```
dir
```
(Windows — on Mac/Linux use `ls`)

✅ You see: `index.html`, `scripts`, `data`, `sourceshelf.html`
❌ If not, go back to Step 1.

### Step 3. Confirm Python is installed

```
python3 --version
```

✅ `Python 3.13.5` (or higher)

❌ **`python3` not recognized** → that's normal on Windows. `python3` is the Mac/Linux
name. On Windows the command is `python`. Try:

```
python --version
```

✅ That works? **Use `python` instead of `python3` for every command in this guide.**

❌ **`Python was not found; run without arguments to install from the Microsoft Store`** →
that's the Windows Store stub interrupting, not a real Python. Try `py --version` first
(it's installed alongside Python and always works). If `py` works, use `py` everywhere.

❌ **Neither works** → install from https://python.org/downloads and **tick
"Add python.exe to PATH"** on the first screen. Then close the terminal and open a new one —
the PATH change doesn't reach terminals that were already open.

### Step 4. Start the local server

```
python3 scripts/serve.py
```

✅ You see:
```
SourceShelf → http://localhost:8080/
Ctrl+C to stop.
```
Your browser opens automatically. If it doesn't, open `http://localhost:8080` yourself.

### Step 5. Look at the site

The page shows **1,619 apps**. Try typing `music` in the search box.

Top-right corner will say ⚪ **JSON snapshot** — that's correct, you haven't connected
Supabase yet. It means "using the built-in data file".

### Step 6. Stop the server

Press `Ctrl+C` in the terminal.

> ✅ **Phase 1 done. The site runs.** Everything below connects it to real storage
> and makes it update by itself.

---

# PHASE 2 — Connect Supabase (15 minutes)

### Step 7. Create a Supabase account

Go to **https://supabase.com** → *Start your project* → **Sign in with GitHub**.
(No GitHub account? Create one free at https://github.com/signup — you need it for Phase 3 anyway.)

### Step 8. Create the project

Click **New project** and fill in:

| field | value |
|---|---|
| Name | `sourceshelf` |
| Database password | click **Generate a password** → save it somewhere |
| Region | **Mumbai (ap-south-1)** if you're in India, else the closest |
| Plan | **Free** |

Click **Create new project**. Wait ~2 minutes (it shows a loading bar). Don't close the tab.

### Step 9. Create the tables

1. Left sidebar → **SQL Editor**
2. Click **New query**
3. Open the file `sourceshelf/supabase/schema.sql` in Notepad
4. Select **everything** (`Ctrl+A`), copy (`Ctrl+C`)
5. Paste into the SQL editor
6. Click **Run** (`Ctrl+Enter`)

✅ Bottom panel shows one row: `apps | runs | added_today` → `0 | 0 | 0`

#### ❌ If you get `ERROR: 42710: relation "apps" is already member of publication "supabase_realtime"`

You're running an **older copy** of `schema.sql`. That file contained a
`alter publication supabase_realtime ...` line that Supabase rejects because it
already publishes new tables automatically. The line was dead weight — the site
never uses websockets — and has been removed.

Fix: you have two options.

- **Simplest** — your tables were probably already created by the failed run.
  Skip this step and run `python scripts\selftest.py`. If it says
  `PASS apps table readable`, you're done.
- **Clean** — get the current `schema.sql` and run it again. It is idempotent
  (verified: three consecutive runs on PostgreSQL 17, all OK), so running it
  twice is harmless.

❌ Any other red error = you didn't paste the whole file. Select all again and re-run.

### Step 10. Copy your Project URL

Left sidebar → **Project Settings** (gear icon) → **API** → copy **Project URL**.
It looks like `https://abcdefghijk.supabase.co`. Paste it into Notepad.

### Step 11. Copy your anon key

Same page → under **Project API keys** → the row marked **anon / public** → copy it.
This one is safe to publish.

### Step 12. Copy your service key

Same page → scroll to **service_role / secret** → click **Reveal** → copy it.

> ⚠️ This key bypasses security. Only ever put it in `.env` and GitHub Secrets.
> Never post it in chat or commit it.

### Step 13. Create your `.env` file

**Windows:**
```
copy .env.example .env
notepad .env
```

**macOS / Linux:**
```
cp .env.example .env
nano .env
```

### Step 14. Fill in the three values

Replace the placeholder lines so the file looks like this (your values, no quotes, no spaces around `=`):

```
SUPABASE_URL=https://abcdefghijk.supabase.co
SUPABASE_ANON_KEY=paste_your_anon_key_here
SUPABASE_SERVICE_KEY=paste_your_service_key_here
```

Save it:
- Notepad → `Ctrl+S` → close
- nano → `Ctrl+O`, Enter, then `Ctrl+X`

### Step 15. Test the connection

```
python3 scripts/selftest.py
```

✅ You want, in the **Supabase** section:
```
PASS  .env loaded
PASS  SUPABASE_URL — https://...
PASS  REST endpoint reachable
PASS  apps table readable
PASS  write access (service key)
```
and at the bottom: **`0 failed`**

<details>
<summary>❌ If it fails</summary>

| message | fix |
|---|---|
| `SUPABASE_URL is not set` | wrong folder, or the file is `.env.txt`. On Windows: Notepad → *Save as* → *All files* → name it `.env` |
| `table public.apps does not exist` | Step 9 didn't run — redo it |
| `key rejected` | key copied partially — copy it again, all of it |
| `write test failed` | `SUPABASE_SERVICE_KEY` missing |
| `cannot reach https://...` | URL typo, or project still starting — wait a minute |

</details>

**Do not continue until this says `0 failed`.**

### Step 16. Fill the database

```
python3 scripts/update.py
```

Takes 3–15 minutes. It prints 67 lines like `[1/67] topic:self-hosted → 100 (+100)`.

✅ Ends with something like:
```
supabase: 1619 rows synced, 1619 first seen today
note: first run — discovery dates recorded, but nothing is marked new.
  New arrivals start appearing from the next run.
```

**Both of those are correct.** All 1,619 rows get today's date recorded — that's
your baseline. Nothing is *flagged* as new, because there's nothing to compare
against yet. The New arrivals section starts filling from the next run.

The summary at the bottom should say **`new today: 0`**. If it says
`new today: 1619`, you're on an old copy of the code — grab the current one.

### Step 17. Check the database

```
python3 scripts/supabase_store.py --stats
```

✅ `apps: 1619 rows` and `runs: 1 rows`

You can also look in Supabase → **Table Editor** → `apps` — you'll see 1,619 rows
with a filled `first_seen` column. **That's your storage working.**

### Step 18. Bake the keys into the page

This is the step that makes the header say **Live · Supabase** instead of
**JSON snapshot**.

`update.py` writes your apps into the database. It does **not** write the
connection details into the page — only this command does:

```
python3 scripts/build_single.py
```

✅ You want this exact line:
```
supabase config: injected
```

❌ If it says `supabase config: none`, your `.env` isn't in this folder or is
missing `SUPABASE_URL` / `SUPABASE_ANON_KEY`. Redo Step 13–14, then run this again.
The page will work either way — it just falls back to the bundled JSON snapshot.

### Step 19. Confirm the site reads from it

```
python3 scripts/serve.py
```

✅ Top-right now says 🟢 **Live · Supabase**

Press `Ctrl+C` when done.

> ✅ **Phase 2 done. Storage is real, not the JSON fallback.**

---

# PHASE 3 — Put it online with a daily cron (10 minutes)

### Step 20. Check your secrets won't be uploaded

```
git init
git status
```

✅ `.env` is **NOT** in the list (`.gitignore` excludes it)
❌ If `.env` appears — stop, tell me, don't commit.

### Step 21. Commit the code

```
git add .
git commit -m "SourceShelf"
git branch -M main
```

### Step 22. Create the GitHub repo

Go to **https://github.com/new**

| field | value |
|---|---|
| Repository name | `sourceshelf` |
| Visibility | **Public** (Pages is free for public repos) |
| Add a README | **leave unticked** |

Click **Create repository**.

### Step 23. Connect and push

GitHub shows a "quick setup" page. Use the **"…or push an existing repository"** block:

```
git remote add origin https://github.com/YOURNAME/sourceshelf.git
git push -u origin main
```

✅ Reload the GitHub page — your files are there, and `.env` is **not** among them.

### Step 24. Add the database secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
Add these three, one at a time (Name on top, Value below, click *Add secret*):

| Name | Value |
|---|---|
| `SUPABASE_URL` | your project URL |
| `SUPABASE_SERVICE_KEY` | service_role key |
| `SUPABASE_ANON_KEY` | anon key |

### Step 25. Add the site URL variable

Same page → **Variables** tab → **New repository variable**:

| Name | Value |
|---|---|
| `SITE_URL` | `https://YOURNAME.github.io/sourceshelf` |

### Step 26. Turn on Pages

**Settings** → **Pages** → *Build and deployment* → **Source: `GitHub Actions`**

⚠️ This dropdown, not "Deploy from a branch".

### Step 27. Run the automation once, manually

**Actions** tab → left sidebar **Refresh catalog & deploy** → right side **Run workflow**
→ leave defaults → **Run workflow**.

Watch it for 5–10 minutes.

✅ `refresh` job goes green, then `deploy` goes green
✅ Summary shows apps in catalog / new today
✅ A new commit appears: `chore(data): refresh catalog …`
✅ Your site is live at `https://YOURNAME.github.io/sourceshelf/`

Open it. Top-right should be 🟢 **Live · Supabase**.

### Step 28. Done — verify tomorrow

Nothing more to do. It runs **every night at 03:17 UTC (08:47 IST)**.

Tomorrow, check:

```
python3 scripts/supabase_store.py --stats
```

`runs` has grown by one. And the site will show a **New arrivals** badge with
what it found that day.

> ✅ **Phase 3 done. Fully automated and online.**

---

# Daily commands (after setup)

| I want to… | command |
|---|---|
| see the site locally | `python3 scripts/serve.py` |
| update apps now (fast) | `python3 scripts/update.py --quick` |
| update apps + download links | `python3 scripts/update.py` |
| check everything works | `python3 scripts/selftest.py` |
| build the single-file page + inject keys | `python3 scripts/build_single.py` |
| which copy am I looking at? | `python3 scripts/doctor.py` |
| reset "new arrivals" to a clean baseline | `python3 scripts/reset_seed.py` |
| see database row counts | `python3 scripts/supabase_store.py --stats` |
| see recent arrivals | `python3 scripts/supabase_store.py --new 7` |
| push changes to GitHub | `git add . && git commit -m "msg" && git push` |

---

# Things that trip people up

1. **Double-clicking works, but tells you nothing about which copy it is.**
   The page is plain files, and Supabase allows reads from anywhere, so a
   double-clicked `sourceshelf.html` shows live data just fine.
   Use `python3 scripts/serve.py` when you want it to *print* the folder and
   the page timestamp it is serving — that's how you catch a stale copy.

2. **Double-clicking shows old data after an update.**
   `update.py` rewrites the file — reload or reopen it.

3. **`python3 scripts/update.py` says "can't open file".**
   You're in the wrong folder. `cd` into `sourceshelf` first.

3b. **The page shows an old design, or the wrong data source.**
   You almost certainly have two copies of the project on disk: one you are
   *serving*, one you are *opening*. Extract the zip into an empty folder.
   Then run this inside the folder you actually care about:

   ```
   python scripts/doctor.py
   ```

   It prints the folder it is in, whether that copy is current, whether it is
   built for Supabase, and lists any other copies sitting next to it.

4. **Windows `python3` opens the Microsoft Store.**
   That's the fake stub. Use `python` instead.

5. **First run marks nothing as new.** Correct — it's recording the baseline.
   Arrivals appear from run #2.

6. **Notepad saves `.env` as `.env.txt`.** In *Save as*, choose *All files*.

7. **The live site shows fewer apps than your local copy (e.g. 977 instead of 1,619).**
   GitHub's search API only allows ~30 requests a minute. The crawl runs 67
   searches, so on a slow night some of them come back empty and that run
   simply sees fewer repos. Two things now protect you:

   - the crawl **retries** every failed search once, slower;
   - anything already in the database that search missed is **carried over**,
     so the catalog never shrinks.

   The crawl log says it plainly:
   ```
   unique repos from search: 1402  (64/67 queries ok, 3 failed)
   history: 217 apps kept from the database (not returned by search this run)
   ```

   If you see that line and the number is still low, your database is smaller
   than you think — run `python scripts/build_single.py` locally (your PC has a
   full search cache) and let the next nightly run take it from there.

---

# Where things live

```
sourceshelf/
├── index.html            ← multi-file version
├── sourceshelf.html      ← single-file version (double-click this)
├── .env                  ← YOUR SECRETS (never commit)
├── .env.example          ← template
├── START-HERE.md         ← beginner walkthrough (this file is RUN.md)
├── data/apps.json        ← the JSON fallback dataset
├── scripts/
│   ├── update.py         ← crawl + rebuild
│   ├── build_single.py   ← rebuild sourceshelf.html + inject Supabase keys
│   ├── serve.py          ← local preview (prints the folder it serves)
│   ├── doctor.py         ← which copy am I actually looking at?
│   ├── selftest.py       ← verify everything
│   └── supabase_store.py ← database client
├── supabase/schema.sql   ← paste into Supabase SQL editor
└── .github/workflows/refresh.yml  ← the nightly automation
```
