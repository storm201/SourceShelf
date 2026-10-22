# 🚀 Do this, in this order

A beginner's walkthrough. Each step says exactly what to type and **how to know it
worked**. Don't skip ahead — later steps depend on earlier ones.

Total time: about 30 minutes, most of it waiting for downloads.

> **Where to type commands.** You need a terminal:
> - **Windows** → press `Win`, type `powershell`, press Enter
> - **macOS** → press `Cmd+Space`, type `terminal`, press Enter
> - **Linux** → `Ctrl+Alt+T`
>
> Anything in a grey box is a command. Copy it, paste it, press Enter.

---

## Step 1 — Check you have Python

You ran `index.html` and it worked. That's the site **with data already baked in** —
it can't update itself. Python is what fetches new apps.

```bash
python3 --version
```

If that errors, also try:

```bash
python --version
```

**You want to see `Python 3.10` or higher.**

<details open>
<summary>❌ On Windows: "python3 is not recognized" or the Microsoft Store opens</summary>

That is **normal and not an error with your PC.** `python3` is the Mac/Linux command name;
Windows uses `python`. The Store message is Windows hijacking the command, not real Python.

Try these in order and use the first one that prints a version number:

```
python --version
py --version
```

Whatever works, use that name for **every** command in this guide.
(If `py` works, `py scripts/serve.py` etc. works too.)

</details>

<details>
<summary>❌ Nothing works at all</summary>

Install Python:

- **Windows:** go to https://www.python.org/downloads/ → download → run the installer →
  ⚠️ **on the first screen, tick "Add python.exe to PATH"** → Install.
  Then **close and reopen PowerShell** and try again.
- **macOS:** `brew install python` (or download from python.org)
- **Linux:** `sudo apt install python3` (Debian/Ubuntu) or `sudo dnf install python3` (Fedora)

From now on, use whichever worked: `python3` or `python`. These docs say `python3`.

</details>

---

## Step 2 — Open a terminal *inside* the project folder

The commands below only work if you are in the `sourceshelf` folder. This is the step
most people get wrong.

**Windows** — in File Explorer, open the `sourceshelf` folder, then click the address
bar, type `powershell`, press Enter.

**macOS** — open Terminal, type `cd ` (with a space), then drag the `sourceshelf`
folder from Finder into the Terminal window and press Enter.

**Linux** — right-click the folder → *Open in Terminal*.

Now check you're in the right place:

```bash
dir
```

(Windows; or `ls` on Mac/Linux). **You should see `index.html`, `scripts`, `data`,
`README.md`.** If you see something else, you're in the wrong folder — go back.

---

## Step 3 — Create your Supabase project

This is the actual database storage. Free tier, no card.

1. Go to **https://supabase.com** → *Start your project* → sign in with GitHub
   (create a GitHub account first if you don't have one — you'll need it anyway).
2. **New project**
   - Name: `sourceshelf`
   - Database password: click *Generate a password* and **save it somewhere**
   - Region: **Mumbai (ap-south-1)** if you're in India, otherwise the closest one
   - Plan: **Free**
3. Click **Create new project** and wait ~2 minutes. Don't close the tab.
4. In the left sidebar, click **SQL Editor** → **New query**.
5. Open the file `supabase/schema.sql` from your downloaded folder in Notepad
   (or any text editor), select **all** of it, copy, paste into the SQL editor.
6. Click **Run** (or press `Ctrl+Enter`).

**How you know it worked:** the bottom panel shows a result with one row:
`apps | runs | added_today` → `0 | 0 | 0`.

<details>
<summary>❌ <code>ERROR: 42710: relation "apps" is already member of publication "supabase_realtime"</code></summary>

You're using an older copy of `schema.sql`. It had a `alter publication
supabase_realtime ...` line that Supabase rejects, because Supabase already
publishes new tables on its own. The line was unnecessary — the site polls the
REST API and never opens a websocket — so it's gone.

Your tables were most likely created anyway by the failed run. Check by running:

```
python scripts\selftest.py
```

`PASS  apps table readable` means you're fine and can move on. Otherwise get the
current `schema.sql` and run it again — it's idempotent, so a second run is safe.

</details>

Any other red error means the whole file didn't get pasted — select all of it
again and re-run.

---

## Step 4 — Get your keys

In Supabase, left sidebar → **Project Settings** (gear icon) → **API**.

Copy these two things into Notepad for now:

| what it's called | where | what it's for |
|---|---|---|
| **Project URL** | near the top, `https://xxxxx.supabase.co` | where your database lives |
| **anon / public** key | under *Project API keys* | safe to publish; the website uses it to read |

Then scroll down to **service_role / secret** key — click *Reveal* and copy it too.

> ⚠️ **The service_role key is powerful.** It bypasses all security rules. It goes
> in your local `.env` file and in GitHub Secrets — **never** in a chat, never in a
> screenshot, never in your repo. If you ever leak it, click *Rotate* in Supabase.
>
> The **anon** key is the opposite: it's designed to be public, and can only *read*.

---

## Step 5 — Put the keys in `.env`

In the project folder there's a file called `.env.example`. You need a copy called
`.env` (no `.example`).

**Windows (PowerShell, in the project folder):**

```powershell
copy .env.example .env
notepad .env
```

**macOS / Linux:**

```bash
cp .env.example .env
nano .env      # or: open -e .env
```

Notepad/nano now shows the file. Fill in three lines (paste your values):

```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=PASTE_YOUR_ANON_KEY_HERE
SUPABASE_SERVICE_KEY=PASTE_YOUR_SERVICE_KEY_HERE
```

Save and close:
- **Notepad:** `Ctrl+S`, then close the window
- **nano:** `Ctrl+O`, Enter, then `Ctrl+X`

> No spaces around the `=`. No quotes needed. `.env` is git-ignored, so this file
> will never be uploaded.

---

## Step 6 — Test the connection *before* doing anything else

```bash
python3 scripts/selftest.py
```

Read the **Supabase** section. You want:

```
PASS  .env loaded
PASS  SUPABASE_URL — https://xxxx.supabase.co
PASS  REST endpoint reachable
PASS  apps table readable
PASS  write access (service key)
```

And at the bottom: **`0 failed`**.

<details>
<summary>❌ What if it fails?</summary>

| message | fix |
|---|---|
| `SUPABASE_URL is not set` | you're in the wrong folder, or the file is named `.env.txt`. Windows hides extensions — in Notepad use *Save as* → *All files* → name it `.env` |
| `table public.apps does not exist` | Step 3.5 didn't run. Paste the whole `schema.sql` again |
| `key rejected — check SUPABASE_ANON_KEY` | wrong key copied (truncated). Copy it again, fully |
| `cannot reach https://...` | URL typo, or the project is still provisioning. Wait a minute |
| `write test failed` | you didn't fill in `SUPABASE_SERVICE_KEY` |

</details>

Don't continue until this is clean. Everything downstream depends on it.

---

## Step 7 — Do your first crawl

This is the run that fills the database. It takes 3–15 minutes depending on
your connection.

```bash
python3 scripts/update.py
```

You'll see it working through 67 searches, then:

```
supabase: 0 apps in history
supabase: syncing catalog…
supabase: 1619 rows synced, 0 first seen today
note: first run — discovery dates recorded, but nothing is marked new.
```

**That last line is correct, not a bug.** This run records *when* each app was
first seen. Claiming 1,619 apps were "added today" on your very first run would be
a lie. Real arrivals start appearing from the next run.

**How you know it worked:**

```bash
python3 scripts/supabase_store.py --stats
```

You want something like `apps: 1619 rows`, `runs: 1 rows`.

Also check it in Supabase itself: **Table Editor → apps** — you should see 1,619 rows
with a `first_seen` column filled in. **That's your storage working.**

---

## Step 8 — Look at your site, now database-backed

```bash
python3 scripts/serve.py
```

It opens `http://localhost:8080` in your browser. Look at the top-right corner:

| what you see | meaning |
|---|---|
| 🟢 **Live · Supabase** | connected — reading from your database |
| 🟡 **Fallback · JSON** | database unreachable — using the built-in snapshot |
| ⚪ **JSON snapshot** | na Supabase configured in this build |

> **Why serve instead of double-clicking?** A page opened as a `file://` URL is
> blocked by the browser from calling Supabase. Over `http://localhost` it works.
> Your deployed site on GitHub Pages uses `https://`, so it's fine there too.
> Double-clicking still works — you just get the JSON fallback.

Press `Ctrl+C` in the terminal when you're done looking.

---

## Step 9 — Push the code to GitHub

First check your secrets won't be uploaded:

```bash
git init
git status
```

Make sure **`.env` is not in the list**. `.gitignore` should already exclude it.
If it *is* listed, stop and tell me — don't commit.

Then:

```bash
git add .
git commit -m "SourceShelf with Supabase storage"
git branch -M main
```

Now create the repo: go to **https://github.com/new**, name it `sourceshelf`,
keep it **Public** (Pages is free for public repos), **don't** tick "Add a README".
Click *Create repository*. GitHub shows you a page with commands — use the ones
under **"…or push an existing repository from the command line"**, which will be:

```bash
git remote add origin https://github.com/YOURNAME/sourceshelf.git
git push -u origin main
```

Reload the GitHub page — your files should be there. **Check `.env` is not among them.**

---

## Step 10 — Give GitHub the same keys

In your repo: **Settings → Secrets and variables → Actions → New repository secret**.

Add these three, one at a time (Name on top, Value below, then *Add secret*):

| Name | Value |
|---|---|
| `SUPABASE_URL` | your project URL |
| `SUPABASE_SERVICE_KEY` | the service_role key |
| `SUPABASE_ANON_KEY` | the anon key |

Then click the **Variables** tab (same page) → *New repository variable*:

| Name | Value |
|---|---|
| `SITE_URL` | `https://YOURNAME.github.io/sourceshelf` |

---

## Step 11 — Turn on the website

**Settings → Pages** → under *Build and deployment*:

- **Source: `GitHub Actions`** ← this dropdown, not the branch option

Then go to the **Actions** tab → left sidebar *Refresh catalog & deploy* →
right side **Run workflow** button → leave defaults → **Run workflow**.

Watch it: the run takes 5–10 minutes. Click into it to follow along.

**How you know it worked:**
- The `refresh` job goes green, then `deploy` goes green
- The **Summary** shows apps in catalog / new today
- A new commit appears: `chore(data): refresh catalog …`
- Your site is live at **`https://YOURNAME.github.io/sourceshelf/`**

Open it. Top-right should read 🟢 **Live · Supabase**.

---

## Step 12 — Confirm the automation is real

Nothing more to do — it now runs **every night at 03:17 UTC (08:47 IST)** by itself.
Your PC can be off.

To verify it's actually running, in a day or two:

```bash
python3 scripts/supabase_store.py --stats
```

`runs` should have grown by one per night. In Supabase → Table Editor → `runs`,
you'll see a row per crawl with a timestamp and how many new apps it found.

And the site will start showing a **New arrivals** badge with what it found
that day. Click it to see apps grouped *Today / Yesterday / N days ago*.

---

## Daily use from now on

| I want to… | command |
|---|---|
| update the catalog on my PC now | `python3 scripts/update.py` |
| …but fast (keeps download links) | `python3 scripts/update.py --quick` |
| view the site locally | `python3 scripts/serve.py` |
| see what's in the database | `python3 scripts/supabase_store.py --stats` |
| see recent arrivals | `python3 scripts/supabase_store.py --new 7` |
| check everything still works | `python3 scripts/selftest.py` |
| push manual changes | `git add . && git commit -m "msg" && git push` |

---

## Cheat sheet: what's stored where

```
Your PC                     GitHub                        Supabase
┌─────────────┐      ┌──────────────────┐          ┌─────────────────┐
│ .env        │      │ Actions secrets  │          │ apps  (1619)    │
│  ↓ keys     │ push │  ↓ same 3 keys   │  writes  │  first_seen     │
│ crawl       │ ───► │ crawl nightly    │ ───────► │ runs  (log)     │
└─────────────┘      └────────┬─────────┘          └────────┬────────┘
                              │ deploys                      │ reads
                              ▼                              ▼
                     GitHub Pages (free)  ◄────── your browser
                              │
                     sourceshelf.html + data/apps.json
                        (the JSON fallback)
```

- **Supabase = truth.** `first_seen` lives there permanently, so "new today" is real.
- **JSON = fallback.** The build bakes a snapshot into the page, so it renders
  instantly and still works if the database is down or not yet configured.
- **Nothing costs money.** Actions free tier is 2,000 min/month; you use ~300.
