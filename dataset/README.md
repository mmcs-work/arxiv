---
configs:
- config_name: default
  data_files:
  - split: train
    path: "data/**/*.parquet"
- config_name: fast
  data_files:
  - split: train
    path:
    - "monthly/**/*.parquet"
    - "updates/**/*.parquet"
---

# Single-author arXiv Computer Science

Metadata for arXiv records classified in Computer Science that list exactly one author.
`default` retains the original daily-file import. `fast` stores historical data
in monthly files and adds new submissions as daily update files; it is the
configuration used by the public archive because it makes filtering much faster.

This dataset contains metadata only. arXiv is the source of truth; use each record's
`arxiv_url` and `pdf_url` to read the paper.
