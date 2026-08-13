"""Fetch recent single-author papers from arXiv into SQLite."""

import argparse
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from app import connect, init_db
from config import CATEGORIES

API_URL = "https://export.arxiv.org/api/query"
ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def text(entry, name):
    return " ".join(entry.findtext(name, default="", namespaces=ATOM).split())


def fetch_category(category, start, end, max_results):
    query = f"cat:{category} AND submittedDate:[{start} TO {end}]"
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": "single-author-archive/1.0 (contact: local-archive)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return ET.parse(response).getroot().findall("atom:entry", ATOM)


def fetch_date(day, max_results=1000):
    """Fetch and save single-author papers submitted on one YYYY-MM-DD date."""
    return fetch_range(day, day, max_results)


def fetch_range(start_day, end_day, max_results=5000):
    """Fetch and save papers within an inclusive YYYY-MM-DD range."""
    start = start_day.replace("-", "")
    end = end_day.replace("-", "")
    return ingest(f"{start}0000", f"{end}2359", max_results)


def paper_from(entry):
    authors = entry.findall("atom:author", ATOM)
    if len(authors) != 1:
        return None

    arxiv_url = text(entry, "atom:id")
    arxiv_id = re.sub(r"v\d+$", "", arxiv_url.split("/abs/", 1)[-1])
    links = {link.get("title"): link.get("href") for link in entry.findall("atom:link", ATOM)}
    categories = [item.get("term") for item in entry.findall("atom:category", ATOM)]
    primary = entry.find("arxiv:primary_category", ATOM)

    return (
        arxiv_id,
        text(entry, "atom:title"),
        text(authors[0], "atom:name"),
        text(entry, "atom:summary"),
        primary.get("term") if primary is not None else categories[0],
        ",".join(categories),
        text(entry, "atom:published"),
        text(entry, "atom:updated"),
        arxiv_url,
        links.get("pdf", f"https://arxiv.org/pdf/{arxiv_id}"),
    )


def ingest(start, end, max_results):
    init_db()
    accepted = 0
    with connect() as database:
        for index, category in enumerate(CATEGORIES):
            if index:
                time.sleep(3)
            entries = fetch_category(category, start, end, max_results)
            papers = [paper for entry in entries if (paper := paper_from(entry))]
            before = database.total_changes
            database.executemany(
                "INSERT OR IGNORE INTO papers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                papers,
            )
            added = database.total_changes - before
            accepted += added
            print(f"{category}: checked {len(entries)}, added {added}")
    return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=2, help="look back this many days (default: 2)")
    parser.add_argument("--max-results", type=int, default=1000, help="limit per category")
    args = parser.parse_args()
    if args.days < 1 or args.max_results < 1:
        parser.error("--days and --max-results must be positive")

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    accepted = ingest(f"{since:%Y%m%d%H%M}", "999912312359", args.max_results)
    print(f"Done: added {accepted} paper(s).")


if __name__ == "__main__":
    main()
