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

The local Flask app is useful for experimenting. For a public, maintenance-free
archive, use the static GitHub Pages + Hugging Face Dataset setup below.

## Publish the public archive

This repository includes a static site in `pages/`, and a small publisher in
`dataset/`. The publisher makes one small Parquet file per submission day. This
means the daily update only replaces the recent days rather than re-uploading
the whole archive.

1. Create a **public** Hugging Face Dataset, or let the first command create it.
   Make a write token at <https://huggingface.co/settings/tokens>.
2. Set the dataset name in [`pages/config.js`](pages/config.js).
3. With Python 3.11 or newer, publish the historical database once:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt -r dataset/requirements.txt
   # Put HF_TOKEN=hf_your_write_token in .env (see .env.example).
   # HF_DATASET is optional; it defaults to your-username/single-author-arxiv.
   python dataset/publish.py --database backfill/papers.db --upload
   ```

4. On GitHub, add `HF_TOKEN` as an Actions secret. Add `HF_DATASET` as an
   Actions variable only if you chose a dataset name other than the default. In
   **Settings → Pages**, set the source to **GitHub Actions**. Pushes deploy the
   site; the daily job refreshes the latest three days at 09:37 UTC.

## What is deployed

- Data: [mainakmanna/single-author-arxiv](https://huggingface.co/datasets/mainakmanna/single-author-arxiv)
- Frontend source: [`pages/`](pages/), deployed by the `Deploy archive site`
  workflow once GitHub Pages is enabled for this repository.
- Historical coverage: 84,592 single-author CS-classified arXiv records from
  1990-01-01 through 2026-08-13.

The frontend queries Hugging Face's public Dataset Viewer API directly. It has
no server and never receives a write token, so the dataset must remain public.

## How the pieces fit together

```text
arXiv OAI-PMH backfill ──> backfill/papers.db ──> dataset/publish.py ──> Hugging Face Dataset
arXiv API (daily) ─────────────────────────────> dataset/publish.py ──> Hugging Face Dataset
GitHub Pages <────────────────────── pages/app.js queries Hugging Face's public API
```

`backfill/harvest.py` is the resumable, one-time historical collector.
`dataset/publish.py --database ... --upload` converts its SQLite output into
day-partitioned Parquet files. The published layout is `data/YYYY/YYYY-MM-DD.parquet`.
`dataset/publish.py --recent --upload` refetches a short date overlap, then
replaces only those day files. arXiv IDs are de-duplicated before writing.

## Routine operation and recovery

The `Update public dataset` GitHub Action runs at 09:37 UTC each day. It uses a
two-day overlap so a late-indexed record can be picked up on the next run.

- `HF_TOKEN` is a GitHub Actions **secret** with Hugging Face dataset-write access.
- `HF_DATASET` is optional; when omitted, the script derives
  `YOUR_HF_USERNAME/single-author-arxiv` from the token.
- `.env` is for local use only, is ignored by Git, and must never be committed.
- If a scheduled update fails, run the workflow manually with a larger `days`
  value. Rewriting an existing day is safe.

The source Parquet build directory (`dataset/build/`) is generated and ignored;
it can be deleted after a successful upload and recreated at any time from
`backfill/papers.db`.
