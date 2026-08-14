# Historical CS backfill

This is intentionally separate from the website app. It harvests every arXiv
record in the Computer Science OAI-PMH set, saves only records with exactly one
author, and writes them to `backfill/papers.db`.

```sh
python backfill/harvest.py
```

It resumes automatically after an interruption. The first run can take a long
time; use `--max-pages 1` for a small trial. The normal website database at
`papers.db` is never changed.
