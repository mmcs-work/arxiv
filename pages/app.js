const config = window.ARCHIVE_CONFIG;
const server = "https://datasets-server.huggingface.co";
const perPage = 20;
let offset = 0;
let lastMode = "browse";

const categories = {
  "cs.AI": "Artificial Intelligence", "cs.AR": "Hardware Architecture", "cs.CC": "Computational Complexity",
  "cs.CE": "Computational Engineering", "cs.CG": "Computational Geometry", "cs.CL": "Computation and Language",
  "cs.CR": "Cryptography and Security", "cs.CV": "Computer Vision", "cs.CY": "Computers and Society",
  "cs.DB": "Databases", "cs.DC": "Distributed Computing", "cs.DL": "Digital Libraries", "cs.DM": "Discrete Mathematics",
  "cs.DS": "Data Structures and Algorithms", "cs.ET": "Emerging Technologies", "cs.FL": "Formal Languages",
  "cs.GL": "General Literature", "cs.GR": "Graphics", "cs.GT": "Computer Science and Game Theory",
  "cs.HC": "Human-Computer Interaction", "cs.IR": "Information Retrieval", "cs.IT": "Information Theory",
  "cs.LG": "Machine Learning", "cs.LO": "Logic in Computer Science", "cs.MA": "Multiagent Systems",
  "cs.MM": "Multimedia", "cs.MS": "Mathematical Software", "cs.NA": "Numerical Analysis",
  "cs.NE": "Neural and Evolutionary Computing", "cs.NI": "Networking and Internet Architecture",
  "cs.OH": "Other Computer Science", "cs.OS": "Operating Systems", "cs.PF": "Performance",
  "cs.PL": "Programming Languages", "cs.RO": "Robotics", "cs.SC": "Symbolic Computation",
  "cs.SD": "Sound", "cs.SE": "Software Engineering", "cs.SI": "Social and Information Networks",
  "cs.SY": "Systems and Control"
};

const form = document.querySelector("#filters");
const paperList = document.querySelector("#papers");
const status = document.querySelector("#status");
const more = document.querySelector("#more");
const category = form.elements.category;
for (const [code, name] of Object.entries(categories)) category.add(new Option(`${code} — ${name}`, code));

function configured() { return config && config.dataset && !config.dataset.startsWith("YOUR_"); }
function parameters(values) { return new URLSearchParams({ dataset: config.dataset, config: config.config, split: config.split, ...values }); }
function selected() { return Object.fromEntries(new FormData(form)); }
function esc(value) { return String(value).replaceAll("'", "''"); }

async function request(endpoint, values) {
  const response = await fetch(`${server}/${endpoint}?${parameters(values)}`);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "The archive is not ready yet. Try again shortly.");
  return body;
}

function matches(row, filters) {
  return (!filters.category || row.primary_category === filters.category || row.categories.split(",").includes(filters.category))
    && (!filters.start || row.published.slice(0, 10) >= filters.start)
    && (!filters.end || row.published.slice(0, 10) <= filters.end);
}

function card(row) {
  const article = document.createElement("article");
  const date = row.published.slice(0, 10);
  const title = document.createElement("a");
  title.href = row.arxiv_url; title.target = "_blank"; title.rel = "noreferrer"; title.textContent = row.title;
  const meta = document.createElement("p"); meta.className = "meta"; meta.textContent = `${row.author} · ${date} · ${row.primary_category}`;
  const abstract = document.createElement("p"); abstract.className = "abstract"; abstract.textContent = row.abstract;
  article.append(title, meta, abstract);
  return article;
}

async function load(append = false) {
  if (!configured()) { status.textContent = "Set your public Hugging Face dataset in pages/config.js, then this archive is ready."; return; }
  const filters = selected();
  if (!append) { offset = 0; paperList.replaceChildren(); }
  status.textContent = "Searching the archive…";
  try {
    let data;
    if (filters.query.trim()) {
      lastMode = "search";
      data = await request("search", { query: filters.query.trim(), offset, length: 100 });
    } else {
      lastMode = "browse";
      const clauses = [];
      if (filters.category) clauses.push(`"primary_category" = '${esc(filters.category)}'`);
      if (filters.start) clauses.push(`"published" >= '${esc(filters.start)}'`);
      if (filters.end) clauses.push(`"published" <= '${esc(filters.end)} 23:59:59'`);
      data = await request("filter", { where: clauses.join(" AND ") || "\"arxiv_id\" <> ''", orderby: "\"published\" DESC", offset, length: perPage });
    }
    const rows = data.rows.map(item => item.row).filter(row => matches(row, filters));
    rows.slice(0, perPage).forEach(row => paperList.append(card(row)));
    offset += lastMode === "search" ? 100 : perPage;
    const noun = rows.length === 1 ? "paper" : "papers";
    status.textContent = rows.length ? `${rows.length} ${noun}${data.partial ? " (partial index)" : ""}.` : "No papers found.";
    more.hidden = rows.length === 0 || (!filters.query && rows.length < perPage);
  } catch (error) {
    status.textContent = error.message;
    more.hidden = true;
  }
}

form.addEventListener("submit", event => { event.preventDefault(); load(); });
more.addEventListener("click", () => load(true));
load();
