"""Small arXiv API helper shared by the daily static-data updater."""

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API_URL = "https://export.arxiv.org/api/query"
ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def text(entry, name):
    return " ".join(entry.findtext(name, default="", namespaces=ATOM).split())


def fetch_category(category, start, end, max_results):
    """Return arXiv API entries for one category and submission-time window."""
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


def paper_from(entry):
    """Return one normalized record, or None unless it has exactly one author."""
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
