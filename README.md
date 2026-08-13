# One Author

A tiny Flask archive of arXiv papers whose metadata lists exactly one author.

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

The daily job looks back two days and ignores duplicate arXiv IDs. For a simple
historical backfill, run (for example) `python fetch.py --days 365`. Use
`--max-results` if a category has more than 1,000 results in that period.
The website's date picker can also fetch and open an inclusive UTC submission
date range of up to 31 days.

The GitHub Actions workflow runs every day at 05:17 UTC and commits changes to
`papers.db`. Repository workflow permissions must allow Actions to write.
