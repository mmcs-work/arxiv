"""Harvest all historical single-author Computer Science metadata from arXiv."""

import argparse
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATABASE = BASE_DIR / "papers.db"
OAI_URL = "https://oaipmh.arxiv.org/oai"
OAI = "{http://www.openarchives.org/OAI/2.0/}"
ARXIV = "{http://arxiv.org/OAI/arXiv/}"


def connect():
    database = sqlite3.connect(DATABASE)
    database.execute("PRAGMA journal_mode=WAL")
    database.execute("PRAGMA synchronous=NORMAL")
    return database


def initialize(database):
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS papers (
            arxiv_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            abstract TEXT NOT NULL,
            primary_category TEXT NOT NULL,
            categories TEXT NOT NULL,
            published TEXT NOT NULL,
            updated TEXT NOT NULL,
            arxiv_url TEXT NOT NULL,
            pdf_url TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def value(element, name):
    return " ".join((element.findtext(ARXIV + name, default="") or "").split())


def paper(record):
    metadata = record.find(OAI + "metadata")
    entry = metadata.find(ARXIV + "arXiv") if metadata is not None else None
    if entry is None:
        return None

    authors = entry.findall(f"{ARXIV}authors/{ARXIV}author")
    if len(authors) != 1:
        return None
    author = " ".join(
        part
        for part in (value(authors[0], "forenames"), value(authors[0], "keyname"))
        if part
    )
    arxiv_id = value(entry, "id")
    categories = value(entry, "categories").split()
    if not arxiv_id or not author or not categories:
        return None

    return (
        arxiv_id,
        value(entry, "title"),
        author,
        value(entry, "abstract"),
        categories[0],
        ",".join(categories),
        value(entry, "created"),
        value(entry, "updated"),
        f"https://arxiv.org/abs/{arxiv_id}",
        f"https://arxiv.org/pdf/{arxiv_id}",
    )


def request(token):
    params = {"verb": "ListRecords"}
    if token:
        params["resumptionToken"] = token
    else:
        params.update({"metadataPrefix": "arXiv", "set": "cs"})
    url = f"{OAI_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "single-author-archive/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return ET.parse(response).getroot()


def state(database, key):
    row = database.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
    return row[0] if row else ""


def harvest(delay, max_pages):
    with connect() as database:
        initialize(database)
        token = state(database, "resumption_token")
        page = int(state(database, "pages") or 0)
        saved = 0

        while max_pages is None or page < max_pages:
            if page:
                time.sleep(delay)
            root = request(token)
            error = root.find(OAI + "error")
            if error is not None:
                raise RuntimeError(error.text or error.get("code", "OAI-PMH error"))

            records = root.findall(f"{OAI}ListRecords/{OAI}record")
            papers = [item for record in records if (item := paper(record))]
            next_token = root.findtext(f"{OAI}ListRecords/{OAI}resumptionToken", default="")
            before = database.total_changes
            with database:
                database.executemany(
                    "INSERT OR IGNORE INTO papers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    papers,
                )
                database.execute(
                    "INSERT OR REPLACE INTO state VALUES ('resumption_token', ?)",
                    (next_token,),
                )
                database.execute("INSERT OR REPLACE INTO state VALUES ('pages', ?)", (str(page + 1),))
            added = database.total_changes - before - 2
            saved += added
            page += 1
            print(f"page {page}: checked {len(records)}, added {added}, total added {saved}", flush=True)
            if not next_token:
                print("Complete.", flush=True)
                return
            token = next_token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=3, help="seconds between requests (default: 3)")
    parser.add_argument("--max-pages", type=int, help="stop after this many pages; useful for a trial run")
    args = parser.parse_args()
    if args.delay < 0 or args.max_pages is not None and args.max_pages < 1:
        parser.error("--delay must be non-negative and --max-pages must be positive")
    try:
        harvest(args.delay, args.max_pages)
    except Exception as error:
        print(f"Stopped: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
