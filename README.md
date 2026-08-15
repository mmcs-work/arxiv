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
2. In [`pages/config.js`](pages/config.js), replace `YOUR_HF_USERNAME/...` with
   your dataset name, for example `mainak/single-author-arxiv`.
3. With Python 3.11 or newer, publish the historical database once:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt -r dataset/requirements.txt
   export HF_TOKEN=hf_your_write_token
   export HF_DATASET=mainak/single-author-arxiv
   python dataset/publish.py --database backfill/papers.db --upload
   ```

4. On GitHub, add `HF_TOKEN` as an Actions secret and `HF_DATASET` as an Actions
   variable with the same dataset name. In **Settings → Pages**, set the source
   to **GitHub Actions**. Pushes deploy the site; the daily job refreshes the
   latest three days at 09:37 UTC.

The frontend queries Hugging Face's public Dataset Viewer API directly, so it
needs no server and never exposes your token. The dataset must stay public for
this version.
