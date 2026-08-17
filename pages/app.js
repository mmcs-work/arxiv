const perPage = 20;
const cache = new Map();
let shown = [];
let currentPage = 1;
let renderVersion = 0;

const categories = {};

const form = document.querySelector("#filters");
const paperList = document.querySelector("#papers");
const status = document.querySelector("#status");
const pagination = document.querySelector("#pagination");
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
const pageNumber = document.querySelector("#page-number");
const rssCategory = document.querySelector("#rss-category");
const rssOpen = document.querySelector("#rss-open");
const rssCopy = document.querySelector("#rss-copy");
const rssToggle = document.querySelector("#rss-toggle");
const rssPanel = document.querySelector("#rss-panel");
const themeToggle = document.querySelector("#theme-toggle");

function url(path) { return new URL(path, document.baseURI).href; }
async function data(path) {
  if (!cache.has(path)) {
    const response = await fetch(url(path));
    if (response.status === 404 && path.startsWith("data/months/")) {
      cache.set(path, Promise.resolve([]));
      return cache.get(path);
    }
    if (!response.ok) throw new Error("Archive data is not available yet.");
    cache.set(path, response.json());
  }
  return cache.get(path);
}
function filters() { return Object.fromEntries(new FormData(form)); }
function monthRange(start, end) {
  const first = new Date(`${(start || "1990-01").slice(0, 7)}-01T00:00:00Z`);
  const last = new Date(`${(end || new Date().toISOString()).slice(0, 7)}-01T00:00:00Z`);
  const months = [];
  for (let date = first; date <= last; date.setUTCMonth(date.getUTCMonth() + 1)) months.push(date.toISOString().slice(0, 7));
  return months;
}
function matches(item, active) {
  return (!active.category || item.primary_category === active.category || item.categories.split(",").includes(active.category))
    && (!active.start || item.published.slice(0, 10) >= active.start)
    && (!active.end || item.published.slice(0, 10) <= active.end);
}
function card(item) {
  const article = document.createElement("article");
  const title = document.createElement("a");
  title.href = item.arxiv_url || `https://arxiv.org/abs/${item.arxiv_id}`; title.target = "_blank"; title.rel = "noreferrer"; title.textContent = item.title;
  const meta = document.createElement("p"); meta.className = "meta"; meta.textContent = `${item.author} · ${item.published.slice(0, 10)} · ${item.primary_category}`;
  const abstract = document.createElement("details"); abstract.className = "abstract";
  const summary = document.createElement("summary"); summary.textContent = "Read abstract";
  const text = document.createElement("p"); text.textContent = item.abstract;
  abstract.append(summary, text);
  article.append(title, meta, abstract);
  return article;
}
async function pageRecords(page) {
  if (page.every(item => item.abstract)) return page;
  const months = [...new Set(page.map(item => item.published.slice(0, 7)))];
  const full = (await Promise.all(months.map(month => data(`data/months/${month}.json`)))).flat();
  const byId = new Map(full.map(item => [item.arxiv_id, item]));
  return page.map(item => byId.get(item.arxiv_id) || item);
}
async function render() {
  const version = ++renderVersion;
  const pages = Math.ceil(shown.length / perPage);
  const page = shown.slice((currentPage - 1) * perPage, currentPage * perPage);
  if (page.length) status.textContent = "Loading page…";
  const records = await pageRecords(page);
  if (version !== renderVersion) return;
  paperList.replaceChildren(...records.map(card));
  status.textContent = shown.length ? `${shown.length.toLocaleString()} paper${shown.length === 1 ? "" : "s"}.` : "No papers found.";
  pagination.hidden = !shown.length;
  previous.disabled = currentPage === 1;
  next.disabled = currentPage === pages;
  pageNumber.textContent = `Page ${currentPage} of ${pages}`;
}
async function load() {
  const active = filters(); currentPage = 1; renderVersion += 1; paperList.replaceChildren(); status.textContent = "Loading archive…"; pagination.hidden = true;
  try {
    let records;
    if (active.query.trim()) {
      const query = active.query.trim().toLowerCase();
      const index = await data("data/search.json");
      const matchedIndex = index.filter(item => `${item.title} ${item.author}`.toLowerCase().includes(query) && matches(item, active)).slice(0, 100);
      const months = [...new Set(matchedIndex.map(item => item.published.slice(0, 7)))];
      const full = (await Promise.all(months.map(month => data(`data/months/${month}.json`)))).flat();
      const ids = new Set(matchedIndex.map(item => item.arxiv_id));
      records = full.filter(item => ids.has(item.arxiv_id));
    } else if (active.start || active.end) {
      const months = monthRange(active.start, active.end);
      status.textContent = `Loading ${months.length} monthly archive${months.length === 1 ? "" : "s"}…`;
      records = (await Promise.all(months.map(month => data(`data/months/${month}.json`)))).flat();
    } else if (active.category) {
      records = await data(`data/categories/${active.category}.json`);
    } else {
      records = await data("data/search.json");
    }
    shown = records.filter(item => matches(item, active)).sort((a, b) => b.published.localeCompare(a.published));
    render();
  } catch (error) { status.textContent = error.message; }
}
form.addEventListener("submit", event => { event.preventDefault(); load(); });
previous.addEventListener("click", () => { currentPage -= 1; render(); window.scrollTo({ top: 0, behavior: "smooth" }); });
next.addEventListener("click", () => { currentPage += 1; render(); window.scrollTo({ top: 0, behavior: "smooth" }); });
rssCopy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(url(rssOpen.getAttribute("href")));
    rssCopy.textContent = "Copied";
    setTimeout(() => { rssCopy.textContent = "Copy link"; }, 1600);
  } catch {
    rssCopy.textContent = "Open to copy";
  }
});
rssToggle.addEventListener("click", () => {
  rssPanel.open = true;
  rssPanel.scrollIntoView({ behavior: "smooth", block: "center" });
});
const savedTheme = localStorage.getItem("theme");
if (savedTheme === "dark") document.documentElement.dataset.theme = "dark";
themeToggle.addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme === "dark";
  document.documentElement.dataset.theme = dark ? "" : "dark";
  localStorage.setItem("theme", dark ? "light" : "dark");
  themeToggle.textContent = dark ? "☾" : "☀";
  themeToggle.setAttribute("aria-label", dark ? "Use dark theme" : "Use light theme");
});
if (savedTheme === "dark") { themeToggle.textContent = "☀"; themeToggle.setAttribute("aria-label", "Use light theme"); }
async function initialize() {
  try {
    Object.assign(categories, (await data("data/manifest.json")).categories || {});
    for (const [code, name] of Object.entries(categories)) {
      form.elements.category.add(new Option(`${code} — ${name}`, code));
      rssCategory.add(new Option(`${code} — ${name}`, code));
    }
    rssCategory.addEventListener("change", () => {
      rssOpen.href = rssCategory.value ? `feeds/${rssCategory.value}.xml` : "feed.xml";
    });
    load();
  } catch (error) { status.textContent = error.message; }
}
initialize();
