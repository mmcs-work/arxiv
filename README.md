# One Author

An archive of arXiv Computer Science papers whose metadata lists exactly one author.

## Run it

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python fetch.py
python app.py
```

Open <http://127.0.0.1:5000>. The database is created automatically.

## Choose categories

Edit the `CATEGORIES` dictionary in [`config.py`](config.py). It currently
watches every category in arXiv's Computer Science taxonomy; the first five
entries are the most prominent in the site selector.

The local Flask app is useful for experimenting. The public archive is a static
GitHub Pages site with data stored alongside it in this repository.

## Static public archive

This repository includes a static site in `pages/` and generated JSON under
`pages/data/`. It makes no third-party API calls: the browser fetches only the
small files needed for the current category or date range.

With Python 3.11 or newer, build the historical data once:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python static_data/build.py --database backfill/papers.db
   ```

In GitHub **Settings → Pages**, set the source to **GitHub Actions**. Pushes
deploy the site; the daily job refreshes the latest two days at 09:37 UTC.

## What is deployed

- Frontend source: [`pages/`](pages/), deployed by the `Deploy archive site`
  workflow once GitHub Pages is enabled for this repository.
- Historical coverage: 84,592 single-author CS-classified arXiv records from
  1990-01-01 through 2026-08-13.

The frontend uses same-origin JSON files from GitHub Pages. It needs no server,
token, or external search/indexing service.

## How the pieces fit together

```text
arXiv OAI-PMH backfill ──> backfill/papers.db ──> static_data/build.py ──> pages/data
arXiv API (daily) ─────────────────────────────> static_data/build.py ──> pages/data
GitHub Pages <──────────────────────────────────────────── pages/app.js fetches pages/data
```

`backfill/harvest.py` is the resumable, one-time historical collector.
`static_data/build.py --database ...` creates per-month files for exact date
ranges, per-category files for topic browsing, and a compact title/author
search index. Each paper keeps its exact submission timestamp.

## Routine operation and recovery

The `Update static archive data` GitHub Action runs at 09:37 UTC each day. It
uses a two-day overlap so a late-indexed record can be picked up on the next run.

- If a scheduled update fails, run the workflow manually with a larger `days`
  value. Rewriting an existing day is safe.

The generated `pages/data/` files are committed intentionally: GitHub Pages
serves them directly. The old Hugging Face integration has been removed.
