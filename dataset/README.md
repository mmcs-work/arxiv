---
configs:
- config_name: default
  data_files:
  - split: train
    path: "data/**/*.parquet"
---

# Single-author arXiv Computer Science

Metadata for arXiv records classified in Computer Science that list exactly one author.
Records are partitioned by submission day and refreshed daily from the arXiv API.

This dataset contains metadata only. arXiv is the source of truth; use each record's
`arxiv_url` and `pdf_url` to read the paper.
