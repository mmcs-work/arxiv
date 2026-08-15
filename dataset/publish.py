"""Create and publish day-partitioned Parquet metadata for Hugging Face."""

import argparse
import os
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

OUTPUT = Path(__file__).parent / "build"
COLUMNS = (
    "arxiv_id", "title", "author", "abstract", "primary_category", "categories",
    "published", "updated", "arxiv_url", "pdf_url",
)


def normalize(row):
    """Turn a database/API tuple into a JSON/Parquet-friendly record."""
    return dict(zip(COLUMNS, row))


def database_rows(database):
    with sqlite3.connect(database) as connection:
        cursor = connection.execute(
            f"SELECT {', '.join(COLUMNS)} FROM papers ORDER BY published, arxiv_id"
        )
        yield from (normalize(row) for row in cursor)


def recent_rows(days):
    # Importing the existing small API client keeps the arXiv parsing in one place.
    from config import CATEGORIES
    from fetch import fetch_category, paper_from

    now = datetime.now(timezone.utc)
    first_day = (now - timedelta(days=days)).date()
    start = f"{first_day:%Y%m%d}0000"
    end = f"{now:%Y%m%d%H%M}"
    found = {}
    for index, category in enumerate(CATEGORIES):
        if index:
            time.sleep(3)
        for entry in fetch_category(category, start, end, max_results=2000):
            paper = paper_from(entry)
            if paper:
                found[paper[0]] = normalize(paper)
    return [row for row in found.values() if row["published"][:10] >= str(first_day)]


def write_partitions(rows, output):
    by_day = defaultdict(list)
    for row in rows:
        by_day[row["published"][:10]].append(row)

    schema = pa.schema([(column, pa.string()) for column in COLUMNS])
    written = []
    for day, records in sorted(by_day.items()):
        target = output / "data" / day[:4] / f"{day}.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(records, schema=schema)
        pq.write_table(table, target, compression="zstd")
        written.append(target)
    return written


def upload(paths, output, initial):
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN")
    repository = os.environ.get("HF_DATASET")
    if not token or not repository:
        raise SystemExit("Set HF_TOKEN and HF_DATASET (for example, alice/single-author-arxiv).")

    api = HfApi(token=token)
    api.create_repo(repository, repo_type="dataset", private=False, exist_ok=True)
    card = Path(__file__).with_name("README.md")
    api.upload_file(
        path_or_fileobj=str(card), path_in_repo="README.md", repo_id=repository,
        repo_type="dataset", commit_message="Describe dataset",
    )
    if initial:
        api.upload_folder(
            folder_path=str(output / "data"), path_in_repo="data", repo_id=repository,
            repo_type="dataset", commit_message="Publish historical metadata",
        )
    else:
        for path in paths:
            api.upload_file(
                path_or_fileobj=str(path), path_in_repo=str(path.relative_to(output)),
                repo_id=repository, repo_type="dataset", commit_message=f"Refresh {path.stem}",
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--database", type=Path, help="SQLite database from backfill/harvest.py")
    source.add_argument("--recent", action="store_true", help="Fetch recent records from arXiv")
    parser.add_argument("--days", type=int, default=3, help="Recent overlap in days (default: 3)")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--upload", action="store_true", help="Upload to the public Hugging Face dataset")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")

    rows = recent_rows(args.days) if args.recent else list(database_rows(args.database))
    paths = write_partitions(rows, args.output)
    print(f"Wrote {len(rows):,} records across {len(paths):,} day file(s).")
    if args.upload:
        upload(paths, args.output, initial=not args.recent)


if __name__ == "__main__":
    main()
