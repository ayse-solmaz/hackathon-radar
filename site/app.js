const TYPES = {
  all: "Tümü",
  hackathon: "Hackathon",
  ideathon: "Ideathon",
  datathon: "Datathon",
  yarisma: "Yarışma",
};
const ICON = { hackathon: "💻", ideathon: "💡", datathon: "📊", yarisma: "🏆" };

const $ = (id) => document.getElementById(id);
const state = { type: "all", events: [] };
const DAY = 86400000;
const today = new Date(new Date().toDateString());

const fmt = (iso) =>
  iso ? new Date(iso + "T00:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" }) : null;
const daysLeft = (iso) => (iso ? Math.round((new Date(iso + "T00:00:00") - today) / DAY) : null);
const isNew = (e) => e.first_seen && (today - new Date(e.first_seen + "T00:00:00")) / DAY <= 2;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function store(key, val) {
  try { localStorage.setItem(key, val); } catch {}
}
function load(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function card(e) {
  const due = e.deadline || e.end || e.start;
  const left = daysLeft(due);
  const label = e.deadline ? "Son başvuru" : e.end ? "Bitiş" : e.start ? "Tarih" : "Tarih";
  const leftText = left == null ? "" : left === 0 ? "Bugün!" : left > 0 ? `${left} gün kaldı` : "";
  const where = e.online ? "🌐 Online" : e.location ? `📍 ${e.location}` : e.turkey ? "📍 Türkiye" : "";
  const thumb = e.image
    ? `<div class="thumb" style="background-image:url('${esc(e.image)}')"></div>`
    : `<div class="thumb"><span class="ph">${ICON[e.type] || "🏁"}</span></div>`;
  return `
  <a class="card" href="${esc(e.url)}" target="_blank" rel="noopener">
    ${thumb}
    <div class="body">
      <div class="tags">
        <span class="tag t-${e.type}">${TYPES[e.type] || e.type}</span>
        ${isNew(e) ? '<span class="tag new">Yeni</span>' : ""}
        ${e.turkey ? '<span class="tag src">🇹🇷</span>' : ""}
        <span class="tag src">${esc(e.source)}</span>
      </div>
      <h3>${esc(e.title)}</h3>
      ${e.organizer || where ? `<p class="info">${[e.organizer && "🏢 " + esc(e.organizer), esc(where)].filter(Boolean).join(" · ")}</p>` : ""}
      ${e.prize ? `<p class="info">🏆 ${esc(e.prize)}</p>` : ""}
      ${e.summary ? `<p class="summary">${esc(e.summary)}</p>` : ""}
    </div>
    <div class="due">
      <span>${due ? `${label}: ${fmt(due)}` : "Tarih belirtilmemiş"}</span>
      <strong class="${left != null && left <= 3 ? "soon" : ""}">${leftText}</strong>
    </div>
  </a>`;
}

function render() {
  const q = $("q").value.trim().toLocaleLowerCase("tr");
  const where = $("where").value;
  const source = $("source").value;
  const onlyNew = $("onlyNew").checked;

  let list = state.events.filter((e) => {
    if (state.type !== "all" && e.type !== state.type) return false;
    if (source !== "all" && e.source !== source) return false;
    if (where === "tr" && !e.turkey) return false;
    if (where === "online" && !e.online) return false;
    if (where === "tr-online" && !(e.turkey || e.online)) return false;
    if (onlyNew && !isNew(e)) return false;
    if (q) {
      const hay = [e.title, e.organizer, e.location, e.summary, e.source, ...(e.tags || [])].join(" ").toLocaleLowerCase("tr");
      if (!q.split(/\s+/).every((w) => hay.includes(w))) return false;
    }
    return true;
  });

  if ($("sort").value === "new") {
    list = list.slice().sort((a, b) => (b.first_seen || "").localeCompare(a.first_seen || ""));
  } else if ($("sort").value === "tr") {
    // stable sort: Turkey events first, each group keeps deadline order
    list = list.slice().sort((a, b) => b.turkey - a.turkey);
  }

  const trCount = list.filter((e) => e.turkey).length;
  const sectioned = $("sort").value === "tr" && trCount > 0 && trCount < list.length;
  $("grid").innerHTML = sectioned
    ? `<h2 class="section">🇹🇷 Türkiye <small>${trCount}</small></h2>` +
      list.slice(0, trCount).map(card).join("") +
      `<h2 class="section">🌍 Online & dünya <small>${list.length - trCount}</small></h2>` +
      list.slice(trCount).map(card).join("")
    : list.map(card).join("");
  $("count").textContent = `${list.length} etkinlik gösteriliyor`;
  $("empty").hidden = list.length > 0;
  store("filters", JSON.stringify({ type: state.type, where, source, sort: $("sort").value }));
}

function renderChips() {
  const counts = state.events.reduce((m, e) => ((m[e.type] = (m[e.type] || 0) + 1), m), {});
  $("types").innerHTML = Object.entries(TYPES)
    .map(([k, v]) => {
      const n = k === "all" ? state.events.length : counts[k] || 0;
      return `<button class="chip" data-type="${k}" aria-pressed="${state.type === k}">${v} <small>${n}</small></button>`;
    })
    .join("");
}

async function init() {
  const res = await fetch("data/events.json", { cache: "no-cache" });
  const data = await res.json();
  state.events = data.events;

  const updated = new Date(data.updated_at).toLocaleString("tr-TR", { dateStyle: "medium", timeStyle: "short" });
  const tr = state.events.filter((e) => e.turkey).length;
  $("meta").textContent = `${data.count} aktif etkinlik · 🇹🇷 ${tr} Türkiye · Güncellendi: ${updated}`;

  const sources = [...new Set(state.events.map((e) => e.source))].sort((a, b) => a.localeCompare(b, "tr"));
  $("source").innerHTML += sources.map((s) => `<option>${esc(s)}</option>`).join("");

  try {
    const saved = JSON.parse(load("filters") || "{}");
    if (saved.type in TYPES) state.type = saved.type;
    for (const k of ["where", "source", "sort"]) {
      if (saved[k] && [...$(k).options].some((o) => o.value === saved[k])) $(k).value = saved[k];
    }
  } catch {}

  renderChips();
  render();

  $("types").addEventListener("click", (ev) => {
    const b = ev.target.closest(".chip");
    if (!b) return;
    state.type = b.dataset.type;
    renderChips();
    render();
  });
  for (const id of ["q", "where", "source", "sort", "onlyNew"]) {
    $(id).addEventListener(id === "q" ? "input" : "change", render);
  }
}

init().catch((err) => {
  $("meta").textContent = "Veri yüklenemedi.";
  console.error(err);
});
