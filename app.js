(() => {
  const CATEGORY_ORDER = [
    ["building", "Building"],
    ["colored", "16 Colors"],
    ["redstone", "Redstone"],
    ["equipment", "Equipment"],
    ["food", "Food"],
    ["potions", "Potions"],
    ["sets", "Sets"],
    ["other", "Other"],
  ];

  const STORAGE_KEY = "mccostcalc.prefs";
  const state = {
    versions: [],
    latest: null,
    version: null,
    data: null,
    category: "building",
    query: "",
    selected: [], // {id, qty}
    fuelType: "coal",
    mode: "false",
  };

  const el = {
    version: document.getElementById("versionSelect"),
    search: document.getElementById("search"),
    categories: document.getElementById("categories"),
    grid: document.getElementById("itemGrid"),
    empty: document.getElementById("emptyHint"),
    selected: document.getElementById("selected"),
    fuel: document.getElementById("fuelType"),
    mode: document.getElementById("mode"),
    go: document.getElementById("goBtn"),
    clear: document.getElementById("clearBtn"),
    results: document.getElementById("results"),
  };

  function prefs() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); }
    catch { return {}; }
  }
  function savePrefs() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: state.version,
      fuelType: state.fuelType,
      mode: state.mode,
    }));
  }

  function urlVersion() {
    return new URLSearchParams(location.search).get("v") || "";
  }

  function setUrlVersion(version) {
    const url = new URL(location.href);
    if (!version || version === state.latest) url.searchParams.delete("v");
    else url.searchParams.set("v", version);
    history.replaceState(null, "", url);
  }

  async function fetchJson(path) {
    const res = await fetch(path, { cache: "no-cache" });
    if (!res.ok) throw new Error(`Failed to load ${path}`);
    return res.json();
  }

  function itemName(id) {
    return state.data?.items?.[id]?.name || id.replace(/[/_]/g, " ");
  }

  function iconPath(id) {
    return state.data?.items?.[id]?.icon || `icons/${id.replaceAll("/", "__")}.png`;
  }

  function iconImg(id, title) {
    const img = document.createElement("img");
    img.src = iconPath(id);
    img.alt = title || itemName(id);
    img.loading = "lazy";
    img.width = 40;
    img.height = 40;
    img.addEventListener("error", () => {
      if (img.dataset.failed) return;
      img.dataset.failed = "1";
      // waxed / oxidized copper variants often share the base texture
      const fallback = id
        .replace(/^waxed_/, "")
        .replace(/exposed_|weathered_|oxidized_/, "");
      if (fallback !== id && state.data?.items?.[fallback]) {
        img.src = iconPath(fallback);
        return;
      }
      const span = document.createElement("span");
      span.className = "icon-fallback";
      span.textContent = (title || itemName(id)).slice(0, 2);
      img.replaceWith(span);
    });
    return img;
  }

  function craftableIds() {
    const items = state.data.items;
    return Object.keys(items).filter((id) => items[id].recipe).sort((a, b) =>
      itemName(a).localeCompare(itemName(b), undefined, { sensitivity: "base" })
    );
  }

  function visibleIds() {
    const q = state.query.trim().toLowerCase();
    return craftableIds().filter((id) => {
      const item = state.data.items[id];
      if (!q && item.category !== state.category) return false;
      if (!q) return true;
      const catOk = state.category === "all" || item.category === state.category || q;
      // When searching, search across every category.
      const hay = `${item.name} ${id}`.toLowerCase();
      return hay.includes(q) && (q ? true : catOk);
    });
  }

  function renderCategories() {
    const counts = {};
    for (const id of craftableIds()) {
      const cat = state.data.items[id].category || "other";
      counts[cat] = (counts[cat] || 0) + 1;
    }
    el.categories.replaceChildren();
    for (const [id, label] of CATEGORY_ORDER) {
      if (!counts[id]) continue;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = `${label} (${counts[id]})`;
      btn.className = id === state.category && !state.query ? "active" : "";
      btn.addEventListener("click", () => {
        state.category = id;
        state.query = "";
        el.search.value = "";
        renderCategories();
        renderGrid();
      });
      el.categories.append(btn);
    }
  }

  function renderGrid() {
    const ids = visibleIds();
    el.empty.classList.toggle("hidden", ids.length > 0);
    el.grid.replaceChildren();
    for (const id of ids) {
      const name = itemName(id);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "item-btn";
      btn.title = name;
      btn.setAttribute("aria-label", name);
      btn.append(iconImg(id, name));
      btn.addEventListener("click", () => addItem(id));
      el.grid.append(btn);
    }
  }

  function addItem(id) {
    const existing = state.selected.find((row) => row.id === id);
    if (existing) {
      existing.qty += 1;
    } else {
      state.selected.push({ id, qty: 1 });
    }
    renderSelected();
  }

  function renderSelected() {
    if (!state.selected.length) {
      el.selected.innerHTML = '<p class="empty">Click items on the left to add them, then enter how many you need.</p>';
      return;
    }
    el.selected.replaceChildren();
    state.selected.forEach((row, index) => {
      const wrap = document.createElement("div");
      wrap.className = "selected-row";
      const name = document.createElement("div");
      name.className = "name";
      name.textContent = itemName(row.id);
      const qty = document.createElement("input");
      qty.type = "number";
      qty.min = "0";
      qty.step = "1";
      qty.value = row.qty;
      qty.addEventListener("change", () => {
        const n = Number(qty.value);
        row.qty = Number.isFinite(n) && n > 0 ? n : 0;
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove";
      remove.setAttribute("aria-label", `Remove ${itemName(row.id)}`);
      remove.textContent = "×";
      remove.addEventListener("click", () => {
        state.selected.splice(index, 1);
        renderSelected();
      });
      wrap.append(iconImg(row.id), name, qty, remove);
      el.selected.append(wrap);
    });
  }

  function renderFuel() {
    const fuel = state.data.fuel || {};
    el.fuel.replaceChildren();
    const keys = Object.keys(fuel);
    if (!keys.includes(state.fuelType)) {
      state.fuelType = keys.includes("coal") ? "coal" : keys[0];
    }
    for (const id of keys) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = itemName(id);
      if (id === state.fuelType) opt.selected = true;
      el.fuel.append(opt);
    }
  }

  function craft(item, qty, stack = []) {
    const out = {};
    const rec = state.data.items[item];
    const recipe = rec && rec.recipe;
    if (!recipe || stack.includes(item)) {
      out[item] = (out[item] || 0) + qty;
      return out;
    }
    const nextStack = stack.concat(item);
    for (const [ing, amount] of Object.entries(recipe)) {
      const need = amount * qty;
      if (ing === "fuel") {
        const burn = state.data.fuel[state.fuelType] || 1;
        const fuelId = state.fuelType;
        out[fuelId] = (out[fuelId] || 0) + need / burn;
      } else {
        const part = craft(ing, need, nextStack);
        for (const [k, v] of Object.entries(part)) out[k] = (out[k] || 0) + v;
      }
    }
    return out;
  }

  function displayAmount(n) {
    if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n));
    return String(Math.floor(n) + 1);
  }

  function stackInfo(id, amount) {
    const size = state.data.items[id]?.stackSize || 64;
    if (!(amount > size)) return "";
    const stacks = amount / size;
    let text = `${stacks.toFixed(2)} stacks`;
    if (stacks >= 27 && stacks < 54) text += ` · ${(stacks / 27).toFixed(2)} chests`;
    if (stacks >= 54) text += ` · ${(stacks / 54).toFixed(2)} double chests`;
    return text;
  }

  function calculate() {
    const totals = {};
    for (const row of state.selected) {
      if (!row.qty || !state.data.items[row.id]) continue;
      const part = craft(row.id, row.qty);
      for (const [k, v] of Object.entries(part)) totals[k] = (totals[k] || 0) + v;
    }

    const mobsToKill = {};
    const mobTable = state.mode === "looting" ? state.data.mobsLooting3 : state.data.mobs;
    if (state.mode !== "false" && mobTable) {
      for (const [item, amount] of Object.entries(totals)) {
        const info = mobTable[item];
        if (!info) continue;
        const kills = Math.round(info.kills * amount * 100) / 100;
        const prev = mobsToKill[info.entity] || 0;
        if (kills > prev) mobsToKill[info.entity] = kills;
      }
    }

    const wrap = document.createElement("div");
    wrap.className = "results";
    const heading = document.createElement("h2");
    heading.textContent = "You will need";
    wrap.append(heading);

    const materialIds = Object.keys(totals).filter((id) => totals[id] > 0).sort((a, b) =>
      itemName(a).localeCompare(itemName(b), undefined, { sensitivity: "base" })
    );
    let shown = 0;
    for (const id of materialIds) {
      if (state.mode !== "false" && mobTable?.[id]) continue;
      shown += 1;
      const row = document.createElement("div");
      row.className = "result-row";
      const name = document.createElement("span");
      name.textContent = `${itemName(id)}  ×  ${displayAmount(totals[id])}`;
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = stackInfo(id, totals[id]);
      row.append(iconImg(id), name, meta);
      wrap.append(row);
    }

    if (state.mode !== "false") {
      for (const [entity, kills] of Object.entries(mobsToKill)) {
        const row = document.createElement("div");
        row.className = "result-row";
        const name = document.createElement("span");
        const label = entity.replaceAll("_", " ");
        const n = Math.ceil(kills);
        name.textContent = `Kill an average of ${n} ${label}${n === 1 ? "" : "s"}`;
        row.append(iconImg(entity), name);
        wrap.append(row);
        if (state.mode === "looting" && entity === "ghast") {
          const note = document.createElement("p");
          note.className = "note";
          note.textContent = "Are you sure you can kill ghasts with Looting III?";
          wrap.append(note);
        }
        if (state.mode === "looting" && (entity === "iron_golem" || entity === "evoker")) {
          const note = document.createElement("p");
          note.className = "note";
          note.textContent = `Looting III has no effect on ${label} drops.`;
          wrap.append(note);
        }
      }
    }

    if (!shown && !Object.keys(mobsToKill).length) {
      wrap.append(Object.assign(document.createElement("p"), {
        className: "empty",
        textContent: "Select at least one item and a quantity, then calculate.",
      }));
    }
    el.results.replaceChildren(wrap);
    el.results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function loadVersion(version) {
    state.version = version;
    state.data = await fetchJson(`data/${encodeURIComponent(version)}.json`);
    // Keep selected items that still exist; drop the rest.
    state.selected = state.selected.filter((row) => state.data.items[row.id]?.recipe);
    if (!CATEGORY_ORDER.some(([id]) => id === state.category) ||
        !craftableIds().some((id) => state.data.items[id].category === state.category)) {
      state.category = CATEGORY_ORDER.find(([id]) =>
        craftableIds().some((item) => state.data.items[item].category === id)
      )?.[0] || "other";
    }
    setUrlVersion(version);
    savePrefs();
    renderFuel();
    renderCategories();
    renderGrid();
    renderSelected();
    el.results.innerHTML = '<p class="empty">Results will show up here — raw materials, stacks, and optional mob counts.</p>';
  }

  async function init() {
    const index = await fetchJson("data/versions.json");
    state.versions = index.versions;
    state.latest = index.latest;
    const stored = prefs();
    const requested = urlVersion() || stored.version || index.latest;
    const available = new Set(index.versions.map((v) => v.id));
    const initial = available.has(requested) ? requested : index.latest;
    state.fuelType = stored.fuelType || "coal";
    state.mode = stored.mode || "false";
    el.mode.value = state.mode;

    el.version.replaceChildren();
    for (const v of index.versions) {
      const opt = document.createElement("option");
      opt.value = v.id;
      const latestMark = v.id === index.latest ? " (latest)" : "";
      opt.textContent = v.id + latestMark;
      if (v.id === initial) opt.selected = true;
      el.version.append(opt);
    }

    el.version.addEventListener("change", () => loadVersion(el.version.value));
    el.search.addEventListener("input", () => {
      state.query = el.search.value;
      renderCategories();
      renderGrid();
    });
    el.fuel.addEventListener("change", () => {
      state.fuelType = el.fuel.value;
      savePrefs();
    });
    el.mode.addEventListener("change", () => {
      state.mode = el.mode.value;
      savePrefs();
    });
    el.go.addEventListener("click", calculate);
    el.clear.addEventListener("click", () => {
      state.selected = [];
      renderSelected();
      el.results.innerHTML = '<p class="empty">Results will show up here — raw materials, stacks, and optional mob counts.</p>';
    });

    await loadVersion(initial);
  }

  init().catch((err) => {
    el.results.innerHTML = `<p class="note">Could not load recipe data: ${err.message}</p>`;
  });
})();
