"""Fetch page categories from English Wikipedia via the API."""

import time
import urllib.parse
import requests


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "COSC301-OntologyAnalysis/1.0 (university project)"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = USER_AGENT


def fetch_categories(title: str) -> list[str]:
    """Return the category names for a Wikipedia article title.

    Hidden categories (maintenance/tracking) are excluded.
    """
    params = {
        "action": "query",
        "titles": urllib.parse.unquote(title),
        "prop": "categories",
        "cllimit": "max",
        "clshow": "!hidden",
        "format": "json",
    }
    resp = SESSION.get(WIKIPEDIA_API, params=params)
    resp.raise_for_status()
    data = resp.json()

    pages = data.get("query", {}).get("pages", {})
    categories = []
    for page in pages.values():
        for cat in page.get("categories", []):
            # Strip "Category:" prefix
            cat_name = cat["title"].replace("Category:", "", 1)
            categories.append(cat_name)
    return categories


def fetch_categories_batch(titles: list[str], delay: float = 0.5) -> dict[str, list[str]]:
    """Fetch categories for multiple titles with rate limiting.

    Returns dict mapping title -> list of category names.
    """
    result = {}
    for title in titles:
        result[title] = fetch_categories(title)
        time.sleep(delay)
    return result
