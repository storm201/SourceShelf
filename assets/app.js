/* ============================================================
   SOURCESHELF — client
   Vanilla JS, zero dependencies. Loads the pre-built dataset
   (window.__SOURCESHELF__) and filters it fully in memory.
   ============================================================ */
(function () {
  "use strict";

  const DATA = window.__SOURCESHELF__ || { meta: { count: 0 }, apps: [] };
  const ALL = DATA.apps || [];
  const META = DATA.meta || {};
  const CFG = window.__SUPABASE__ || null;   // optional live data source

  // ---------------------------------------------------------- icons
  const I = {
    star: '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>',
    gh: '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.1.1 1.7 1.2 1.7 1.2 1 1.7 2.7 1.2 3.4.9.1-.7.4-1.2.7-1.5-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 016 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z"/></svg>',
    dl: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M7 11l5 5 5-5"/><path d="M4 21h16"/></svg>',
    x: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    ext: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/></svg>',
  };

  const OS_ICON = {
    windows: '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M3 5.5l7.5-1v7H3v-6zM3 18.5l7.5 1v-7H3v6zM11.5 4.3L21 3v8.5h-9.5V4.3zM11.5 19.7L21 21v-8.5h-9.5v7.2z"/></svg>',
    macos: '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M16.4 12.7c0-2.4 2-3.6 2.1-3.6-1.1-1.7-2.9-1.9-3.5-1.9-1.5-.2-2.9.9-3.6.9-.8 0-1.9-.9-3.1-.8-1.6 0-3.1.9-3.9 2.4-1.7 2.9-.4 7.2 1.2 9.6.8 1.2 1.8 2.5 3 2.5 1.2 0 1.7-.8 3.1-.8 1.5 0 1.9.8 3.1.8 1.3 0 2.2-1.2 3-2.4.9-1.4 1.3-2.7 1.3-2.8-.1 0-2.7-1-2.7-3.9zM14 5.4c.7-.8 1.1-1.9 1-3-1 0-2.2.7-2.9 1.5-.6.7-1.1 1.9-1 3 1.1.1 2.2-.6 2.9-1.5z"/></svg>',
    linux: '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c-2 0-3.2 1.7-3.2 3.8 0 1.4-.3 2.3-1.1 3.4C6.5 10.8 6 12.3 6 14c0 1 .2 1.8.6 2.6-.6.5-1 1.2-1 2 0 1 .8 1.9 1.9 2.2 1 .3 2 .5 3 .5s2-.2 3-.5c1.1-.3 1.9-1.2 1.9-2.2 0-.8-.4-1.5-1-2 .4-.8.6-1.6.6-2.6 0-1.7-.5-3.2-1.7-4.8-.8-1.1-1.1-2-1.1-3.4C15.2 3.7 14 2 12 2z"/></svg>',
    android: '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M6 9h12v8a2 2 0 01-2 2H8a2 2 0 01-2-2V9zm-3 .5A1.5 1.5 0 014.5 11v4a1.5 1.5 0 01-3 0v-4A1.5 1.5 0 013 9.5zm18 0a1.5 1.5 0 011.5 1.5v4a1.5 1.5 0 01-3 0v-4A1.5 1.5 0 0121 9.5zM7.5 7c.3-1.7 1.4-3 3-3.7l-1-1.7.8-.5 1.1 1.9c.5-.1 1-.2 1.6-.2s1.1.1 1.6.2L16.7 1l.8.5-1 1.7c1.6.7 2.7 2 3 3.7h-12z"/></svg>',
    web: '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 3 2.5 15 0 18M12 3c-2.5 3-2.5 15 0 18"/></svg>',
    server: '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><path d="M7 7.5h.01M7 16.5h.01"/></svg>',
    cli: '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M4 7l5 5-5 5M12 19h8"/></svg>',
    ext: '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><path d="M9 3h6v3.5a2 2 0 002 2H21v6h-3.5a2 2 0 00-2 2V21H9v-4.5a2 2 0 00-2-2H3v-6h4a2 2 0 002-2V3z"/></svg>',
  };
  const CAT_ICON = {
    "AI & LLM": "M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z",
    "Developer Tools": "M8 6l-5 6 5 6M16 6l5 6-5 6",
    "Privacy & Security": "M12 3l7 3v6c0 4.4-3 8-7 9-4-1-7-4.6-7-9V6l7-3z",
    "Notes & Knowledge": "M6 3h9l4 4v14H6V3zM9 11h7M9 15h5",
    "Productivity": "M4 6h16M4 12h16M4 18h10",
    "Media & Audio": "M9 18V6l10-2v12M9 18a3 3 0 11-3-3M19 16a3 3 0 11-3-3",
    "Video & Streaming": "M3 6h13v12H3zM16 10l5-3v10l-5-3",
    "Photos & Design": "M3 5h18v14H3zM3 16l5-5 4 4 3-3 6 6",
    "Files & Sync": "M3 7h6l2 2h10v10H3zM3 7V5h6l2 2",
    "Communication": "M21 12a8 8 0 11-3 6.2L4 20l1.8-3.6A8 8 0 0121 12z",
    "Self-Hosting & Homelab": "M4 5h16v5H4zM4 14h16v5H4zM7 7.5h.01M7 16.5h.01",
    "Automation": "M12 3v4M12 17v4M3 12h4M17 12h4M12 8a4 4 0 100 8 4 4 0 000-8z",
    "Networking": "M12 3a3 3 0 100 6 3 3 0 000-6zM5 15a3 3 0 100 6 3 3 0 000-6zM19 15a3 3 0 100 6 3 3 0 000-6zM12 9v3M12 12L6 15M12 12l6 3",
    "System & Utilities": "M12 8a4 4 0 100 8 4 4 0 000-8zM12 2v3M12 19v3M2 12h3M19 12h3",
    "Reading & Books": "M4 5h7v15H4zM13 5h7v15h-7z",
    "Health & Fitness": "M12 20s-7-4.5-7-9a4 4 0 017-2.6A4 4 0 0119 11c0 4.5-7 9-7 9z",
    "Finance": "M12 3v18M8 7h6a3 3 0 010 6H9a3 3 0 000 6h7",
    "Education": "M3 8l9-4 9 4-9 4-9-4zM7 11v5c0 1.5 2.2 3 5 3s5-1.5 5-3v-5",
    "Gaming & Emulation": "M7 8h10a4 4 0 014 4v2a4 4 0 01-4 4H7a4 4 0 01-4-4v-2a4 4 0 014-4zM9 11v4M7 13h4M16 12h.01M18 14h.01",
    "Download & Torrent": "M12 3v11M8 11l4 4 4-4M4 20h16",
    "Maps & Travel": "M9 3l6 2 6-2v16l-6 2-6-2-6 2V5l6-2zM9 3v16M15 5v16",
    "Monitoring & Dashboards": "M3 3v18h18M7 15l3-4 3 3 5-7",
    "Other": "M12 8a4 4 0 100 8 4 4 0 000-8z",
  };

  const catIcon = (c) => `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${CAT_ICON[c] || CAT_ICON.Other}"/></svg>`;

  const PLAT_META = {
    "Windows": ["windows", "Windows", OS_ICON.windows],
    "macOS": ["macos", "macOS", OS_ICON.macos],
    "Linux": ["linux", "Linux", OS_ICON.linux],
    "Android": ["android", "Android", OS_ICON.android],
    "iOS": ["ios", "iOS", OS_ICON.macos],
    "Web": ["web", "Web", OS_ICON.web],
    "Self-Hosted": ["self", "Self-Hosted", OS_ICON.server],
    "CLI / TUI": ["cli", "CLI / TUI", OS_ICON.cli],
    "Browser Extension": ["bext", "Extension", OS_ICON.ext],
    "VS Code": ["vsc", "VS Code", OS_ICON.ext],
  };

  // ---------------------------------------------------------- state
  const S = { q: "", cats: [], plats: [], lics: [], minStars: 0, sort: "stars",
            recent: false, newOnly: false, view: "all" };
  const PAGE = 48;
  let filtered = [];
  let rendered = 0;
  let observer = null;

  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtN = (n) => n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, "") + "k" : String(n);
  const fmtSize = (b) => !b ? "" : b > 1048576 ? (b / 1048576).toFixed(b > 10485760 ? 0 : 1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB";

  // ---------------------------------------------------------- index
  // Pre-compute one lowercase blob per app so search is a single indexOf pass.
  for (const a of ALL) {
    a.avatar = "https://github.com/" + a.owner + ".png?size=96";
    a._s = (a.name + " " + a.owner + " " + a.description + " " + (a.topics || []).join(" ") +
      " " + a.category + " " + (a.platforms || []).join(" ") + " " + (a.license || "")).toLowerCase();
    a._dl = a.release && a.release.assets && a.release.assets.length ? a.release : null;
    // stars gained per day since the repo was created — a real "hot" signal
    a._trend = a.stars / Math.max(a.ageDays || 365, 60);
    a._delta = a.starsDelta || 0;
  }

  // "hot" = the fastest-growing ~6% of the catalog (stars/day since creation)
  const HOT = (() => {
    const t = ALL.map((a) => a._trend).sort((x, y) => x - y);
    return t.length ? t[Math.floor(t.length * 0.94)] : Infinity;
  })();
  const isHot = (a) => a._trend >= HOT && a.stars >= 2000;

  // ------------------------------------------------- daily new arrivals
  // `META.newArrivals` is written by the crawler: [{date, count, apps:[...]}]
  // oldest-first so we can render newest-first without re-sorting strings.
  let ARRIVALS = (META.newArrivals || []).slice();
  let LIVE = false;                       // true once Supabase answers
  let LIVE_TOTAL = 0;                     // true row count in the window
  const LIVE_LIMIT = 300;                 // rows fetched for the strip itself
  // The crawler records a baseline on its first run and flags nothing as new.
  // The UI must honour that, or day one reads as "1,619 added today".
  const SEED_RUN = META.baseline === false || META.seedRun === true;

  function dayLabel(d) {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const dt = new Date(d + "T00:00:00");
    const diff = Math.round((today - dt) / 86400000);
    if (diff === 0) return "Today";
    if (diff === 1) return "Yesterday";
    if (diff > 1 && diff < 7) return diff + " days ago";
    return dt.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function arrivalsTotal() {
    return ARRIVALS.reduce((n, g) => n + (g.apps ? g.apps.length : 0), 0);
  }

  function todayGroup() {
    if (!ARRIVALS.length) return null;
    const d = new Date(); d.setHours(0, 0, 0, 0);
    const iso = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") +
                "-" + String(d.getDate()).padStart(2, "0");
    return ARRIVALS.find((g) => g.date === iso) || null;
  }

  function nsCard(a) {
    return `<a class="ns-card" href="${esc(a.url)}" target="_blank" rel="noopener" title="${esc(a.id)}">
      <div class="ns-body">
        <span class="ns-name">${esc(a.name)}</span>
        <span class="ns-meta">★ ${fmtN(a.stars)} · ${esc(a.category)}</span>
        <p class="ns-desc">${esc(a.description || "")}</p>
      </div>
    </a>`;
  }

  function renderStrip() {
    const strip = $("#newstrip"), rail = $("#ns-rail");
    const g = todayGroup();
    const total = arrivalsTotal();
    if (!g && !total) { strip.hidden = true; return; }
    strip.hidden = false;
    const show = g || ARRIVALS[0];
    $("#newstrip-t").textContent = g ? "Added today" : "New this week";
    $("#ns-count").textContent = "+" + show.count;
    rail.innerHTML = (show.apps || []).slice(0, 12).map(nsCard).join("");
    $("#ns-more").textContent = total > show.count
      ? "See all " + total + " new arrivals →" : "See all new arrivals →";
  }

  function renderNewView() {
    const body = $("#newview-body");
    if (!ARRIVALS.length) {
      body.innerHTML = `<div class="nv-empty">
        <b>No new arrivals yet</b>
        ${SEED_RUN
          ? "This run recorded the baseline: every app already in the catalogue " +
            "got a discovery date, but nothing counts as new yet. From the next " +
            "crawl onward, anything genuinely unseen appears here by day."
          : "The nightly crawl lists apps here as it finds them."}
      </div>`;
    } else {
      body.innerHTML = ARRIVALS.map((g) => {
        const isToday = dayLabel(g.date) === "Today";
        return `
        <div class="nv-day">
          <div class="nv-day-h">
            <h3>${esc(dayLabel(g.date))}</h3>
            <span class="nv-d">${esc(g.date)}</span>
            <span class="nv-n">${g.count} app${g.count === 1 ? "" : "s"}</span>
          </div>
          <div class="grid g3">${g.apps.map((a) => arrivalCard(a, isToday)).join("")}</div>
        </div>`;
      }).join("");
    }
    const total = arrivalsTotal();
    const src = LIVE ? "live from Supabase"
              : (META.historySource === "supabase" ? "Supabase history" : "JSON snapshot");
    const shown = total;
    let line = "";
    if (total) {
      line = `<b>${shown.toLocaleString()}</b> ` +
             `app${shown === 1 ? "" : "s"} in the last 7 days · source: ${esc(src)}`;
      if (LIVE_TOTAL > shown) {
        line += ` · showing the newest ${shown.toLocaleString()} of ` +
                `${LIVE_TOTAL.toLocaleString()}`;
      }
    }
    $("#newview-sub").innerHTML = line;
  }

  // cards in the grouped view reuse the main card but need a full app object
  const BY_ID = new Map(ALL.map((a) => [a.id, a]));
  function arrivalCard(a, isToday) {
    const full = BY_ID.get(a.id);
    if (full) {
      // No per-row "new" mark here: this whole view is new arrivals, grouped by
      // the night each was found. Marking every row would be noise.
      return cardHTML(full, { forceNew: false });
    }
    // fall back to the lightweight record shipped in newArrivals
    return cardHTML(Object.assign({
      id: a.id, name: a.name, owner: a.owner, url: a.url, stars: a.stars,
      forks: 0, description: a.description, category: a.category,
      platforms: a.platforms || [], license: a.license, topics: [],
      avatar: "https://github.com/" + a.owner + ".png?size=96",
      _dl: null, _trend: 0, _delta: 0, isNew: false,
    }, { forceNew: false }));
  }

  // ---------------------------------------------------------- facets
  function facets() {
    const cats = new Map(), plats = new Map(), lics = new Map();
    for (const a of ALL) {
      cats.set(a.category, (cats.get(a.category) || 0) + 1);
      for (const p of a.platforms || []) plats.set(p, (plats.get(p) || 0) + 1);
      if (a.license) lics.set(a.license, (lics.get(a.license) || 0) + 1);
    }
    return { cats, plats, lics };
  }
  const F = facets();

  function buildSidebar() {
    // categories
    const cats = [...F.cats.entries()].sort((a, b) => b[1] - a[1]);
    $("#f-cats").innerHTML = cats.map(([c, n]) =>
      `<button class="fitem" data-cat="${esc(c)}"><span class="ico">${catIcon(c)}</span><span class="t">${esc(c)}</span><span class="c">${n}</span></button>`
    ).join("");

    const platOrder = ["Windows", "macOS", "Linux", "Android", "iOS", "Web", "Self-Hosted", "CLI / TUI", "Browser Extension", "VS Code"];
    const plats = [...F.plats.entries()].sort((a, b) => {
      const ia = platOrder.indexOf(a[0]), ib = platOrder.indexOf(b[0]);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
    $("#f-plats").innerHTML = plats.map(([p, n]) => {
      const m = PLAT_META[p] || ["", p, ""];
      return `<button class="fitem" data-plat="${esc(p)}"><span class="ico">${m[2]}</span><span class="t">${esc(m[1])}</span><span class="c">${n}</span></button>`;
    }).join("");

    const lics = [...F.lics.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    $("#f-lics").innerHTML = lics.map(([l, n]) =>
      `<label class="chk"><input type="checkbox" data-lic="${esc(l)}"><span class="t" style="flex:1">${esc(l)}</span><span class="c">${n}</span></label>`
    ).join("");
  }

  function buildTiles() {
    const top = [...F.cats.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
    $("#tiles").innerHTML = top.map(([c, n]) =>
      `<button class="tile" data-cat="${esc(c)}"><div class="ti">${catIcon(c)}</div><b>${esc(c)}</b><span>${n} app${n === 1 ? "" : "s"}</span></button>`
    ).join("");
  }

  // ---------------------------------------------------------- filter
  function apply() {
    const q = S.q.trim().toLowerCase();
    const qs = q ? q.split(/\s+/).filter(Boolean) : null;
    const out = [];
    for (let i = 0; i < ALL.length; i++) {
      const a = ALL[i];
      if (a.stars < S.minStars) continue;
      if (S.cats.length && !S.cats.includes(a.category)) continue;
      if (S.lics.length && !S.lics.includes(a.license)) continue;
      if (S.recent && (a.ageDays || 9999) > 180) continue;
      if (S.newOnly && !a.isNew) continue;
      if (S.plats.length) {
        let ok = false;
        for (const p of S.plats) if (a.platforms.indexOf(p) > -1) { ok = true; break; }
        if (!ok) continue;
      }
      if (qs) {
        let ok = true;
        for (let k = 0; k < qs.length; k++) if (a._s.indexOf(qs[k]) < 0) { ok = false; break; }
        if (!ok) continue;
      }
      out.push(a);
    }
    sortInPlace(out);
    filtered = out;
    return out;
  }

  function sortInPlace(list) {
    const s = S.sort;
    if (s === "stars") list.sort((a, b) => b.stars - a.stars);
    else if (s === "trending") list.sort((a, b) => b._trend - a._trend);
    else if (s === "recent") list.sort((a, b) => (b.pushedAt || "").localeCompare(a.pushedAt || ""));
    else if (s === "new") list.sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
    else if (s === "az") list.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
    else if (s === "forks") list.sort((a, b) => b.forks - a.forks);
    else if (s === "added") list.sort((a, b) => (b.isNew === true) - (a.isNew === true) || b.stars - a.stars);
    else if (s === "gain") list.sort((a, b) => b._delta - a._delta);
  }

  // ---------------------------------------------------------- render
  function cardHTML(a, opts) {
    const forceNew = opts && typeof opts.forceNew === "boolean" ? opts.forceNew : null;
    const showNew = forceNew === null ? !!a.isNew : forceNew;
    const plats = (a.platforms || []).slice(0, 4).map((p) => {
      const m = PLAT_META[p];
      return `<span class="tag os">${m ? m[2] : ""} ${esc(m ? m[1] : p)}</span>`;
    }).join("");
    const over = (a.platforms || []).length - 4;
    const dl = a._dl;
    const btn = dl
      ? `<a class="btn primary" href="${esc(bestAsset(a).url)}" target="_blank" rel="noopener" title="Download ${esc(bestAsset(a).name)}">${I.dl} Download<span class="n">${fmtSize(bestAsset(a).size)}</span></a>`
      : `<a class="btn primary" href="${esc(a.url)}/releases" target="_blank" rel="noopener" title="Open the releases page">${I.dl} Get app</a>`;
    return `<article class="card" data-id="${esc(a.id)}" tabindex="0">
      <div class="card-h">
        <div class="card-logo" aria-hidden="true"><span>${esc((a.name[0] || "?").toUpperCase())}</span><img src="${esc(a.avatar)}" alt="" loading="lazy" decoding="async" onerror="this.remove()"></div>
        <div class="card-t">
          <a class="card-name" href="${esc(a.url)}" target="_blank" rel="noopener" data-stop="1" title="${esc(a.owner + "/" + a.name)}">${esc(a.name)}</a>
          <div class="card-owner">${esc(a.owner)}</div>
        </div>
        <span class="card-stars">${I.star}${fmtN(a.stars)}</span>
      </div>
      <p class="card-desc">${esc(a.description)}</p>
      <div class="card-tags">
        ${showNew ? '<span class="tag badge-new">new</span>'
        : (isHot(a) ? '<span class="tag badge-hot">hot</span>' : "")}
        <span class="tag cat">${esc(a.category)}</span>
        ${plats}${over > 0 ? `<span class="tag">+${over}</span>` : ""}
        ${a.license ? `<span class="tag lic">${esc(a.license)}</span>` : ""}
      </div>
      <div class="card-f">
        ${btn}
        <a class="btn gh" href="${esc(a.url)}" target="_blank" rel="noopener" data-stop="1" aria-label="GitHub repository">${I.gh}</a>
        <button class="btn gh" data-detail="${esc(a.id)}" aria-label="Details">⋯</button>
      </div>
    </article>`;
  }

  function bestAsset(a) {
    const assets = a.release.assets;
    const want = navigator.userAgent.match(/Win/i) ? "windows"
      : navigator.userAgent.match(/Mac/i) ? "macos"
      : navigator.userAgent.match(/Android/i) ? "android"
      : "linux";
    const exact = assets.find((x) => (x.os || []).includes(want));
    return exact || assets[0];
  }


  const grid = $("#grid");
  const sentinel = $("#sentinel");

  function render(reset) {
    if (reset) { grid.innerHTML = ""; rendered = 0; }


    if (!filtered.length) {
      grid.innerHTML = `<div class="empty"><h3>No apps match those filters</h3>
        <p>Try raising the star floor, clearing a platform filter, or searching a different term.</p></div>`;
      $("#load-note").textContent = "";
      observe(false);
      return;
    }

    const end = Math.min(filtered.length, rendered + PAGE);
    const frag = document.createElement("div");
    frag.innerHTML = filtered.slice(rendered, end).map(cardHTML).join("");
    const nodes = Array.from(frag.children);
    for (const n of nodes) grid.appendChild(n);
    rendered = end;
    $("#load-note").textContent = rendered < filtered.length
      ? `Showing ${rendered} of ${filtered.length} — scroll for more`
      : `${filtered.length} app${filtered.length === 1 ? "" : "s"} shown`;
    observe(rendered < filtered.length);
  }

  function observe(on) {
    if (observer) { observer.disconnect(); observer = null; }
    if (!on) return;
    observer = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting)) { observe(false); render(false); }
    }, { rootMargin: "600px 0px" });
    observer.observe(sentinel);
  }

  // ---------------------------------------------------------- chrome
  function updateChrome() {
    const n = filtered.length;
    $("#count").innerHTML = `<b>${n.toLocaleString()}</b> of ${ALL.length.toLocaleString()} apps`;
    const pills = [];
    for (const c of S.cats) pills.push([c, "cat", c]);
    for (const p of S.plats) pills.push([p, "plat", p]);
    for (const l of S.lics) pills.push([l, "lic", l]);
    if (S.recent) pills.push(["Updated recently", "recent", ""]);
    if (S.newOnly) pills.push(["Added today", "new", ""]);
    if (S.minStars > 0) pills.push([`${fmtN(S.minStars)}+ stars`, "stars", ""]);
    const bar = $("#active");
    if (!pills.length) { bar.classList.remove("show"); bar.innerHTML = ""; }
    else {
      bar.classList.add("show");
      bar.innerHTML = `<span class="lbl">Filters</span>` + pills.map(([label, kind, val]) =>
        `<span class="pill">${esc(label)}<button data-rm="${kind}" data-val="${esc(val)}" aria-label="Remove">${I.x}</button></span>`
      ).join("") + `<button class="clear-all" id="clear-all">Clear all</button>`;
    }
    // sidebar selection states
    $$("[data-cat]").forEach((b) => b.classList.toggle("on", S.cats.includes(b.dataset.cat)));
    $$("[data-plat]").forEach((b) => b.classList.toggle("on", S.plats.includes(b.dataset.plat)));
    $$("[data-lic]").forEach((i) => { i.checked = S.lics.includes(i.dataset.lic); });
    // hero vs browse
    if (S.view === "new") return;
    const browsing = S.q || S.cats.length || S.plats.length || S.lics.length || S.minStars || S.recent || S.newOnly;
    const tiles = $("#tiles-wrap");
    if (tiles) tiles.style.display = browsing ? "none" : "";
    const strip = $("#newstrip");
    if (strip && !strip.hidden) strip.style.display = browsing ? "none" : "";
    $("#hero-title").innerHTML = browsing
      ? (S.cats.length === 1 ? esc(S.cats[0]) : "Search results")
      : `Every open-source app worth installing, <em>on one shelf</em>`;
    $("#hero-sub").innerHTML = browsing
      ? (n ? `${n.toLocaleString()} matching app${n === 1 ? "" : "s"}.`
           : "Nothing in the catalogue matches.")
      : `Crawled nightly from GitHub — <b>${ALL.length.toLocaleString()} apps</b> across <b>${F.cats.size} categories</b>, free and open source, with direct download links.`;
  }

  function refresh(reset) {
    apply();
    render(true);
    updateChrome();
    syncURL();
  }

  // ---------------------------------------------------------- view modes
  function setView(v, opts) {
    S.view = v === "new" ? "new" : "all";
    const isNew = S.view === "new";
    $("#newview").hidden = !isNew;
    const nvh = $("#newview-t");
    if (nvh) nvh.hidden = true;   // the hero above already names this view
    $("#newstrip").hidden = isNew ? true : !($("#newstrip").hidden);
    $("#grid").style.display = isNew ? "none" : "";
    $("#load-note").style.display = isNew ? "none" : "";
    $("#active").style.display = isNew ? "none" : "";
    $(".toolbar").style.display = isNew ? "none" : "";

    if (isNew) {
      const tw = $("#tiles-wrap");
      if (tw) tw.style.display = "none";
      $("#hero-title").innerHTML = "Fresh finds, <em>every single day</em>";
      $("#hero-sub").innerHTML = "Apps the automation discovered that weren't in the catalog before.";
      renderNewView();
    } else {
      $("#newview-body").innerHTML = "";
      renderStrip();
      updateChrome();
    }
    $$("[data-view]").forEach((b) => b.classList.toggle("on", b.dataset.view === S.view));
    if (!opts || !opts.silent) syncURL();
    if (isNew && (!opts || !opts.noScroll)) window.scrollTo({ top: 0, behavior: "smooth" });
    else if (isNew) window.scrollTo({ top: 0 });
  }

  // ---------------------------------------------------------- URL state
  let urlTimer;
  function syncURL() {
    clearTimeout(urlTimer);
    urlTimer = setTimeout(() => {
      const p = new URLSearchParams();
      if (S.q) p.set("q", S.q);
      if (S.cats.length) p.set("cat", S.cats.join(","));
      if (S.plats.length) p.set("plat", S.plats.join(","));
      if (S.lics.length) p.set("lic", S.lics.join(","));
      if (S.minStars) p.set("stars", S.minStars);
      if (S.sort !== "stars") p.set("sort", S.sort);
      if (S.recent) p.set("recent", "1");
      if (S.view === "new") p.set("view", "new");
      const qs = p.toString();
      try { history.replaceState(null, "", qs ? "?" + qs : location.pathname); } catch (e) { }
    }, 250);
  }

  function readURL() {
    const p = new URLSearchParams(location.search);
    if (p.get("q")) S.q = p.get("q");
    if (p.get("cat")) S.cats = p.get("cat").split(",").filter(Boolean);
    if (p.get("plat")) S.plats = p.get("plat").split(",").filter(Boolean);
    if (p.get("lic")) S.lics = p.get("lic").split(",").filter(Boolean);
    if (p.get("stars")) S.minStars = +p.get("stars") || 0;
    if (p.get("sort")) S.sort = p.get("sort");
    if (p.get("recent")) S.recent = true;
    if (p.get("view") === "new") S.view = "new";
    $("#q").value = S.q;
    $("#qwrap").classList.toggle("has-val", !!S.q);
    $("#sort").value = S.sort;
    $("#star-range").value = S.minStars;
    $("#stars-val").textContent = S.minStars ? fmtN(S.minStars) + "+" : "any";
    $("#recent").checked = S.recent;
  }

  // ---------------------------------------------------------- drawer
  const drawer = $("#drawer"), scrim = $("#scrim");
  let drawerOpen = false;

  function openDetail(id) {
    const a = ALL.find((x) => x.id === id);
    if (!a) return;
    const assets = (a.release && a.release.assets) || [];
    const dlBlock = assets.length ? `
      <div class="dsec"><h4>Direct downloads · ${esc(a.release.tag || "")}</h4>
        ${assets.slice(0, 14).map((x) => `<a class="asset" href="${esc(x.url)}" target="_blank" rel="noopener">
            <span class="an">${esc(x.name)}</span>
            <span class="as">${fmtSize(x.size)}</span>
          </a>`).join("")}
        ${a.release.page ? `<a class="asset" href="${esc(a.release.page)}" target="_blank" rel="noopener"><span class="an" style="font-family:var(--sans)">All releases &amp; checksums</span>${I.ext}</a>` : ""}
      </div>` : `
      <div class="dsec"><h4>Downloads</h4>
        <div class="note">No pre-built binaries published in a GitHub release for this project — it may be installed from source, via a package manager, or self-hosted with Docker. Check the repository for the official install steps.</div>
      </div>`;

    $("#drawer-body").innerHTML = `
      <div class="dsec"><p class="ddesc">${esc(a.description)}</p></div>
      <div class="dsec"><div class="stat-row">
        <div class="stat"><b>${fmtN(a.stars)}</b><span>Stars</span></div>
        <div class="stat"><b>${fmtN(a.forks)}</b><span>Forks</span></div>
        <div class="stat"><b>${a.license || "—"}</b><span>License</span></div>
      </div></div>
      <div class="dsec"><div style="display:flex;gap:7px;flex-wrap:wrap">
        <span class="tag cat">${esc(a.category)}</span>
        ${(a.platforms || []).map((p) => `<span class="tag os">${esc(p)}</span>`).join("")}
      </div></div>
      ${dlBlock}
      <div class="dsec"><h4>Repository</h4>
        <a class="btn wide" href="${esc(a.url)}" target="_blank" rel="noopener">${I.gh} ${esc(a.id)}</a>
        ${a.homepage ? `<a class="btn wide" style="margin-top:6px" href="${esc(a.homepage)}" target="_blank" rel="noopener">${I.ext} Official website</a>` : ""}
      </div>
      <div class="dsec"><h4>Activity</h4>
        <div class="note">Last push ${esc(a.pushedAt || "unknown")} · created ${esc(a.createdAt || "unknown")}${a.language ? ` · primary language ${esc(a.language)}` : ""}</div>
      </div>
      ${(a.topics || []).length ? `<div class="dsec"><h4>Topics</h4><div style="display:flex;gap:5px;flex-wrap:wrap">${a.topics.map((t) => `<button class="tag" data-topic="${esc(t)}">${esc(t)}</button>`).join("")}</div></div>` : ""}
    `;
    $("#drawer-head").innerHTML = `
      <div class="drawer-logo" aria-hidden="true"><span>${esc((a.name[0] || "?").toUpperCase())}</span><img src="${esc(a.avatar)}" alt="" onerror="this.remove()"></div>
      <div style="min-width:0">
        <div class="card-name" style="font-size:15px">${esc(a.name)}</div>
        <div class="card-owner">${esc(a.owner)}</div>
      </div>
      <button class="x" id="drawer-x" aria-label="Close">${I.x}</button>`;
    $("#drawer-x").onclick = closeDrawer;
    drawer.classList.add("on"); scrim.classList.add("on"); drawerOpen = true;
    document.body.style.overflow = "hidden";
  }
  function closeDrawer() {
    drawer.classList.remove("on"); scrim.classList.remove("on"); drawerOpen = false;
    document.body.style.overflow = "";
  }

  // ---------------------------------------------------------- events
  const qEl = $("#q"), qwrap = $("#qwrap");
  let qTimer;
  qEl.addEventListener("input", () => {
    qwrap.classList.toggle("has-val", !!qEl.value);
    clearTimeout(qTimer);
    qTimer = setTimeout(() => { S.q = qEl.value; refresh(); }, 70);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== qEl) { e.preventDefault(); qEl.focus(); qEl.select(); }
    else if ((e.key === "Enter" || e.key === " ") &&
             document.activeElement && document.activeElement.classList.contains("card")) {
      if (!e.target.closest("a, [data-stop]")) {
        e.preventDefault();
        openDetail(document.activeElement.dataset.id);
      }
    }
    else if (e.key === "Escape") {
      if (drawerOpen) closeDrawer();
      else if (document.activeElement === qEl) { qEl.value = ""; S.q = ""; qwrap.classList.remove("has-val"); refresh(); qEl.blur(); }
    }
  });

  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-cat],[data-plat],[data-lic],[data-detail],[data-rm],[data-topic],#clear-all,#drawer-x,.scrimbutton");
    if (e.target.id === "clear-all") {
      S.q = ""; qEl.value = ""; qwrap.classList.remove("has-val");
      S.cats = []; S.plats = []; S.lics = []; S.minStars = 0; S.recent = false; S.newOnly = false;
      $("#star-range").value = 0; $("#stars-val").textContent = "any"; $("#recent").checked = false;
      refresh(); return;
    }
    const rm = e.target.closest("[data-rm]");
    if (rm) {
      const kind = rm.dataset.rm, val = rm.dataset.val;
      if (kind === "cat") S.cats = S.cats.filter((x) => x !== val);
      if (kind === "plat") S.plats = S.plats.filter((x) => x !== val);
      if (kind === "lic") S.lics = S.lics.filter((x) => x !== val);
      if (kind === "recent") { S.recent = false; $("#recent").checked = false; }
      if (kind === "new") { S.newOnly = false; }
      if (kind === "stars") { S.minStars = 0; $("#star-range").value = 0; $("#stars-val").textContent = "any"; }
      refresh(); return;
    }
    const det = e.target.closest("[data-detail]");
    if (det) { e.preventDefault(); openDetail(det.dataset.detail); return; }

    // A catalogue row is itself the control for opening details. Links inside
    // it (name, download, repository) opt out with data-stop.
    if (!e.target.closest("a, [data-stop]")) {
      const row = e.target.closest(".card");
      if (row && row.dataset.id) { openDetail(row.dataset.id); return; }
    }
    const topic = e.target.closest("[data-topic]");
    if (topic) { closeDrawer(); S.q = topic.dataset.topic; qEl.value = S.q; qwrap.classList.add("has-val"); refresh(); return; }
    if (e.target.closest("#drawer-x")) { closeDrawer(); return; }
    if (e.target === scrim) { closeDrawer(); return; }

    const cat = e.target.closest("[data-cat]");
    if (cat) {
      const v = cat.dataset.cat;
      S.cats = S.cats.includes(v) ? S.cats.filter((x) => x !== v) : S.cats.concat(v);
      refresh(); closeSide(); window.scrollTo({ top: 0, behavior: "smooth" }); return;
    }
    const plat = e.target.closest("[data-plat]");
    if (plat) {
      const v = plat.dataset.plat;
      S.plats = S.plats.includes(v) ? S.plats.filter((x) => x !== v) : S.plats.concat(v);
      refresh(); return;
    }
  });

  document.addEventListener("change", (e) => {
    const lic = e.target.closest("[data-lic]");
    if (lic) {
      const v = lic.dataset.lic;
      S.lics = lic.checked ? S.lics.concat(v) : S.lics.filter((x) => x !== v);
      refresh(); return;
    }
    if (e.target.id === "recent") { S.recent = e.target.checked; refresh(); return; }
    if (e.target.id === "sort") { S.sort = e.target.value; refresh(); syncURL(); return; }
  });

  let starTimer;
  $("#star-range").addEventListener("input", (e) => {
    const v = +e.target.value;
    $("#stars-val").textContent = v ? fmtN(v) + "+" : "any";
    S.minStars = v;
    clearTimeout(starTimer);
    starTimer = setTimeout(refresh, 120);
  });

  $("#sort").value = S.sort;

  $("#qclear").addEventListener("click", () => {
    qEl.value = ""; S.q = ""; qwrap.classList.remove("has-val"); refresh(); qEl.focus();
  });
  $$("[data-clear]").forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.clear === "cat") S.cats = [];
    refresh();
  }));

  // mobile sidebar
  function closeSide() {
    $(".side").classList.remove("on");
    const sc = $("#scrim-side");
    if (sc) sc.classList.remove("on");
  }
  $("#menu").addEventListener("click", () => {
    const on = $(".side").classList.toggle("on");
    const sc = $("#scrim-side");
    if (sc) sc.classList.toggle("on", on);
  });
  $("#scrim-side").addEventListener("click", closeSide);

  // --------------------------------------------------- storage indicator
  // Makes it obvious whether the page is backed by Supabase or the JSON snapshot.
  function setSource(kind, label, tip) {
    const el = $("#data-source");
    if (!el) return;
    el.querySelector("span").textContent = label;
    el.title = tip || label;
    el.classList.toggle("on", kind === "live");
    el.classList.toggle("warn", kind === "warn");
    el.dataset.kind = kind;
  }

  // One-line hint, shown only when this build has no database connection.
  function showBuildHint() {
    const box = document.getElementById("build-hint");
    if (!box) return;
    let dismissed = false;
    try { dismissed = localStorage.getItem("sourceshelf.hint") === "off"; } catch (e) {}
    if (dismissed) return;
    box.hidden = false;
    const x = document.getElementById("build-hint-x");
    if (x) x.onclick = () => {
      box.hidden = true;
      try { localStorage.setItem("sourceshelf.hint", "off"); } catch (e) {}
    };
  }

  // ------------------------------------------------- live Supabase refresh
  // Purely additive: the page is already fully rendered from baked data.
  // If Supabase is configured (and reachable), merge fresher star counts and
  // any arrivals that landed since this build, then re-render the badges.
  async function liveRefresh() {
    if (!CFG || !CFG.url || !CFG.anonKey) {
      LIVE = false;
      setSource("static", "JSON snapshot",
        "No Supabase configured — this page was built from data/apps.json. " +
        "Add SUPABASE_URL + SUPABASE_ANON_KEY to switch to live storage.");
      showBuildHint();
      return;
    }
    setSource("pending", "connecting…", "Contacting Supabase…");
    const since = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);
    const url = CFG.url.replace(/\/$/, "") + "/rest/v1/apps" +
      "?select=id,name,owner,stars,category,description,platforms,license,first_seen,url" +
      "&first_seen=gte." + encodeURIComponent(since) +
      "&order=first_seen.desc,stars.desc&limit=" + LIVE_LIMIT;
    try {
      const r = await fetch(url, {
        // count=exact makes PostgREST report the true total in Content-Range,
        // so the badge can say 1,619 instead of silently stopping at the
        // page size. Without this the number looked like a bug.
        headers: {
          apikey: CFG.anonKey,
          Authorization: "Bearer " + CFG.anonKey,
          Prefer: "count=exact",
        },
      });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const rows = await r.json();
      if (!Array.isArray(rows)) throw new Error("unexpected payload");
      LIVE = true;
      setSource("live", "Live · Supabase",
        "Reading " + CFG.url + " — the JSON snapshot is only a fallback.");
      document.body.dataset.live = "1";

      // Total rows in the window, from "0-299/1619". Not the page size.
      LIVE_TOTAL = rows.length;
      const cr = r.headers.get("content-range") || "";
      const m = /\/(\d+)$/.exec(cr);
      if (m) LIVE_TOTAL = parseInt(m[1], 10);

      // A seeding run records discovery dates but claims nothing is new, and
      // every row in the database carries today's date. Building an arrivals
      // strip from that would announce the whole catalogue as "added today".
      if (SEED_RUN) {
        ARRIVALS = [];
        renderStrip();
        renderNewView();
        const badge = $("#nav-badge");
        if (badge) { badge.textContent = ""; badge.hidden = true; }
        return;
      }

      if (!rows.length) return;
      mergeLive(rows);
      renderStrip();
      renderNewView();
      const badge = $("#nav-badge");
      // the true window total, not the number of rows we chose to render
      const n = Math.max(LIVE_TOTAL, arrivalsTotal());
      if (badge && n) { badge.textContent = n; badge.hidden = false; }
    } catch (e) {
      // The baked dataset is already on screen, so this is never fatal —
      // but say so plainly rather than pretending we're live.
      LIVE = false;
      setSource("warn", "Fallback · JSON",
        "Supabase unreachable (" + e.message + ") — using the built-in JSON snapshot.");
      console.warn("live refresh skipped:", e.message);
    }
  }

  function mergeLive(rows) {
    const byDay = new Map(ARRIVALS.map((g) => [g.date, g]));
    for (const r of rows) {
      const day = String(r.first_seen || "").slice(0, 10);
      if (!day) continue;
      const existing = BY_ID.get(r.id);
      if (existing) {                       // fresher star count
        existing.stars = r.stars;
        existing._trend = existing.stars / Math.max(existing.ageDays || 365, 60);
      }
      let g = byDay.get(day);
      if (!g) { g = { date: day, count: 0, apps: [] }; byDay.set(day, g); }
      if (!g.apps.some((a) => a.id === r.id)) {
        g.apps.push({
          id: r.id, name: r.name, owner: r.owner, url: r.url || ("https://github.com/" + r.id),
          description: r.description || "", stars: r.stars, category: r.category,
          platforms: r.platforms || [], license: r.license,
          hasDownload: !!(existing && existing._dl),
        });
      }
    }
    ARRIVALS = [...byDay.values()]
      .map((g) => ({ ...g, count: g.apps.length, apps: g.apps.sort((a, b) => b.stars - a.stars) }))
      .sort((a, b) => b.date.localeCompare(a.date));
  }

  // ---------------------------------------------------------- boot
  // header badge + nav wiring
  const badge = $("#nav-badge");
  const totalNew = arrivalsTotal();
  if (badge) {
    if (totalNew > 0) { badge.textContent = totalNew; badge.hidden = false; }
    else badge.hidden = true;
  }
  $$("[data-view]").forEach((b) => {
    b.addEventListener("click", () => setView(b.dataset.view));
  });
  const nsMore = $("#ns-more");
  if (nsMore) nsMore.addEventListener("click", () => setView("new"));
  renderStrip();
  $("#updated").textContent = META.generatedAt
    ? "updated " + new Date(META.generatedAt).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    : "local dataset";
  $("#total").textContent = ALL.length.toLocaleString();

  buildSidebar();
  buildTiles();
  readURL();
  apply();
  render(true);
  updateChrome();
  setView(S.view, { silent: true, noScroll: true });
  if (S.view === "all") renderStrip();
  liveRefresh();
})();
