# Historical CS backfill

This is intentionally separate from the website. It harvests every arXiv
record in the Computer Science OAI-PMH set, keeps only records with exactly one
author, and writes them to `backfill/papers.db`.

```sh
python backfill/harvest.py
```

It resumes automatically after an interruption. The first run can take a long
time; use `--max-pages 1` for a small trial. To publish its result, run:

```sh
python static_data/build.py --database backfill/papers.db
```
