const perPage = 20;
const cache = new Map();
let shown = [];
let offset = 0;

const categories = {
  "cs.AI": "Artificial Intelligence", "cs.AR": "Hardware Architecture", "cs.CC": "Computational Complexity", "cs.CE": "Computational Engineering", "cs.CG": "Computational Geometry", "cs.CL": "Computation and Language", "cs.CR": "Cryptography and Security", "cs.CV": "Computer Vision", "cs.CY": "Computers and Society", "cs.DB": "Databases", "cs.DC": "Distributed Computing", "cs.DL": "Digital Libraries", "cs.DM": "Discrete Mathematics", "cs.DS": "Data Structures and Algorithms", "cs.ET": "Emerging Technologies", "cs.FL": "Formal Languages", "cs.GL": "General Literature", "cs.GR": "Graphics", "cs.GT": "Computer Science and Game Theory", "cs.HC": "Human-Computer Interaction", "cs.IR": "Information Retrieval", "cs.IT": "Information Theory", "cs.LG": "Machine Learning", "cs.LO": "Logic in Computer Science", "cs.MA": "Multiagent Systems", "cs.MM": "Multimedia", "cs.MS": "Mathematical Software", "cs.NA": "Numerical Analysis", "cs.NE": "Neural and Evolutionary Computing", "cs.NI": "Networking and Internet Architecture", "cs.OH": "Other Computer Science", "cs.OS": "Operating Systems", "cs.PF": "Performance", "cs.PL": "Programming Languages", "cs.RO": "Robotics", "cs.SC": "Symbolic Computation", "cs.SD": "Sound", "cs.SE": "Software Engineering", "cs.SI": "Social and Information Networks", "cs.SY": "Systems and Control"
};

const form = document.querySelector("#filters");
const paperList = document.querySelector("#papers");
const status = document.querySelector("#status");
const more = document.querySelector("#more");
for (const [code, name] of Object.entries(categories)) form.elements.category.add(new Option(`${code} — ${name}`, code));

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
  title.href = item.arxiv_url; title.target = "_blank"; title.rel = "noreferrer"; title.textContent = item.title;
  const meta = document.createElement("p"); meta.className = "meta"; meta.textContent = `${item.author} · ${item.published.slice(0, 10)} · ${item.primary_category}`;
  const abstract = document.createElement("details"); abstract.className = "abstract";
  const summary = document.createElement("summary"); summary.textContent = "Read abstract";
  const text = document.createElement("p"); text.textContent = item.abstract;
  abstract.append(summary, text);
  article.append(title, meta, abstract);
  return article;
}
function render() {
  const page = shown.slice(offset, offset + perPage);
  page.forEach(item => paperList.append(card(item)));
  offset += page.length;
  status.textContent = shown.length ? `${shown.length.toLocaleString()} paper${shown.length === 1 ? "" : "s"}.` : "No papers found.";
  more.hidden = offset >= shown.length;
}
async function load() {
  const active = filters(); offset = 0; paperList.replaceChildren(); status.textContent = "Loading archive…"; more.hidden = true;
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
      records = await data("data/latest.json");
    }
    shown = records.filter(item => matches(item, active)).sort((a, b) => b.published.localeCompare(a.published));
    render();
  } catch (error) { status.textContent = error.message; }
}
form.addEventListener("submit", event => { event.preventDefault(); load(); });
more.addEventListener("click", render);
load();
