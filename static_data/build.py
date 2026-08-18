"""Fetch and parse papers from the arXiv API."""

import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


ARXIV_API = "https://export.arxiv.org/api/query"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

TIMEOUT = 60
MAX_RETRIES = 5

USER_AGENT = (
    "single-author-arxiv-cs/1.0 "
    "(https://github.com/mmcs-work/single-author-arxiv-cs)"
)


def get_text(element, path, default=""):
    """Return stripped text from an XML child element."""
    child = element.find(path, NS)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def fetch_with_retry(request, category):
    """Fetch a URL with retry/backoff for transient network failures."""
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.read()

        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600

            if not retryable or attempt == MAX_RETRIES - 1:
                raise

            retry_after = exc.headers.get("Retry-After")

            if retry_after:
                try:
                    delay = int(retry_after)
                except ValueError:
                    delay = 5 * (2 ** attempt)
            else:
                delay = 5 * (2 ** attempt)

            delay = min(delay, 120)

            print(
                f"arXiv HTTP {exc.code} for {category}; "
                f"retrying in {delay}s "
                f"({attempt + 1}/{MAX_RETRIES})...",
                flush=True,
            )

            time.sleep(delay)

        except (
            TimeoutError,
            socket.timeout,
            urllib.error.URLError,
            ConnectionError,
        ) as exc:
            if attempt == MAX_RETRIES - 1:
                raise

            delay = min(5 * (2 ** attempt), 120)

            print(
                f"arXiv request failed for {category}: {exc}; "
                f"retrying in {delay}s "
                f"({attempt + 1}/{MAX_RETRIES})...",
                flush=True,
            )

            time.sleep(delay)

    raise RuntimeError(f"Failed to fetch arXiv category {category}")


def fetch_category(category, start_date, end_date, max_results=2000):
    """Fetch arXiv entries for a category within a submitted-date range."""
    query = (
        f"cat:{category} "
        f"AND submittedDate:[{start_date} TO {end_date}]"
    )

    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    url = ARXIV_API + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/atom+xml",
        },
    )

    print(
        f"Fetching {category} "
        f"({start_date} -> {end_date}, max {max_results})...",
        flush=True,
    )

    data = fetch_with_retry(request, category)

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise RuntimeError(
            f"arXiv returned invalid XML for {category}"
        ) from exc

    entries = root.findall("atom:entry", NS)

    print(
        f"{category}: received {len(entries)} "
        f"{'entry' if len(entries) == 1 else 'entries'}",
        flush=True,
    )

    return entries


def clean_text(value):
    """Collapse repeated whitespace/newlines into ordinary spaces."""
    return " ".join(value.split())


def get_arxiv_id(entry):
    """Extract the bare arXiv identifier from an Atom entry."""
    value = get_text(entry, "atom:id")
    value = value.rstrip("/").rsplit("/", 1)[-1]

    if "v" in value:
        base, version = value.rsplit("v", 1)
        if version.isdigit():
            value = base

    return value


def get_authors(entry):
    """Return all author names from an Atom entry."""
    authors = []

    for author in entry.findall("atom:author", NS):
        name = get_text(author, "atom:name")
        if name:
            authors.append(name)

    return authors


def get_categories(entry):
    """Return all arXiv categories attached to an entry."""
    categories = []

    for element in entry.findall("atom:category", NS):
        category = element.attrib.get("term", "").strip()

        if category and category not in categories:
            categories.append(category)

    return categories


def get_primary_category(entry):
    """Return the paper's primary arXiv category."""
    element = entry.find("arxiv:primary_category", NS)

    if element is None:
        return ""

    return element.attrib.get("term", "").strip()


def get_links(entry):
    """Return the abstract and PDF URLs."""
    arxiv_url = ""
    pdf_url = ""

    for link in entry.findall("atom:link", NS):
        href = link.attrib.get("href", "").strip()
        rel = link.attrib.get("rel", "")
        link_type = link.attrib.get("type", "")
        title = link.attrib.get("title", "")

        if rel == "alternate" and href:
            arxiv_url = href

        if title == "pdf" or link_type == "application/pdf":
            pdf_url = href

    return arxiv_url, pdf_url


def paper_from(entry):
    """Convert an arXiv entry into a single-author paper record."""
    authors = get_authors(entry)

    if len(authors) != 1:
        return None

    arxiv_id = get_arxiv_id(entry)

    if not arxiv_id:
        return None

    title = clean_text(get_text(entry, "atom:title"))
    abstract = clean_text(get_text(entry, "atom:summary"))

    primary_category = get_primary_category(entry)
    categories = get_categories(entry)

    published = get_text(entry, "atom:published")
    updated = get_text(entry, "atom:updated")

    arxiv_url, pdf_url = get_links(entry)

    if not arxiv_url:
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

    if not pdf_url:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

    return (
        arxiv_id,
        title,
        authors[0],
        abstract,
        primary_category,
        ",".join(categories),
        published,
        updated,
        arxiv_url,
        pdf_url,
    )
