# Single-author arXiv CS

A small, static archive of single-author papers from arXiv's Computer Science
(CS) branch. The website lets people browse a category, select any date range,
search titles or authors, and open the full abstract. It is hosted
on GitHub Pages and needs no server, database, token, or external service at
runtime.

## How it works

`pages/` is the website. Its JSON data lives in `pages/data/` and is committed
to this repository so GitHub Pages can serve it directly:

```text
arXiv → collection scripts → pages/data → GitHub Pages
```

The browser downloads only the category, month, or search index it needs.

## Daily updates

[`Update static archive data`](.github/workflows/update-static-data.yml) runs
every day at 09:37 UTC. It fetches the last two days from arXiv, keeps
single-author records, merges them into `pages/data/`, and commits only when
there is new data. The normal Pages workflow then deploys the site.

Run the workflow manually from GitHub Actions to refresh more days after an
interruption. Overlapping days are safe.

## RSS feeds

The newest papers are available at `/feed.xml`. Each category also has its own
feed at `/feeds/<category>.xml`, for example `/feeds/cs.LG.xml`. The feeds are
rebuilt with the daily archive update.

## Make an archive for other arXiv categories

1. Edit [`config.py`](config.py) and replace `CATEGORIES` with the arXiv
   category codes you want (for example, `stat.ML` or `math.PR`). The labels
   become the website selector labels.
2. Fetch the full history with the one-time, resumable collector:

   ```sh
   python backfill/harvest.py
   ```

   The collector currently requests arXiv's Computer Science OAI-PMH set. For
   another top-level archive, change `set: "cs"` in
   [`backfill/harvest.py`](backfill/harvest.py) to the appropriate arXiv set.
3. Build the static files and commit them:

   ```sh
   python static_data/build.py --database backfill/papers.db
   ```

4. Push to `main`. With GitHub Pages set to **GitHub Actions**, the site deploys
   automatically. The daily updater will then use your revised categories.

All scripts use Python's standard library; Python 3.11 or newer is sufficient.

## Repository map

- `pages/` — the deployed website and its static data.
- `config.py` — categories and labels to collect.
- `fetch.py` — small arXiv API parser used by daily updates.
- `static_data/build.py` — creates or refreshes website JSON.
- `backfill/` — optional one-time historical collector; its SQLite output stays
  local and is ignored by Git.
- `.github/workflows/` — daily refresh and Pages deployment.
