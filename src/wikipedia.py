"""Fetch page categories from English Wikipedia via the API."""

import time
import urllib.parse
import requests


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "COSC301-OntologyAnalysis/1.0 (university project)"
MAX_RETRIES = 4
SESSION = requests.Session()
SESSION.headers["User-Agent"] = USER_AGENT


def _get_with_retry(params: dict, retries: int = MAX_RETRIES) -> dict:
    """GET with exponential backoff on 429 errors."""
    for attempt in range(retries):
        resp = SESSION.get(WIKIPEDIA_API, params=params)
        if resp.status_code == 429 and attempt < retries - 1:
            wait = 2 ** (attempt + 1)
            print(f"    Wikipedia 429, retrying in {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()


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
    data = _get_with_retry(params)

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


def fetch_parent_categories_batch(category_names: list[str], delay: float = 0.5) -> dict[str, list[str]]:
    """Fetch parent categories for a batch of category names.

    Takes category names WITHOUT the 'Category:' prefix.
    Returns dict mapping each input category to its parent category names.
    Uses the Wikipedia API's multi-title support (up to 50 at a time).
    """
    result: dict[str, list[str]] = {c: [] for c in category_names}

    for i in range(0, len(category_names), 50):
        batch = category_names[i:i + 50]
        titles_param = "|".join(f"Category:{urllib.parse.unquote(c)}" for c in batch)
        params = {
            "action": "query",
            "titles": titles_param,
            "prop": "categories",
            "cllimit": "max",
            "clshow": "!hidden",
            "format": "json",
        }
        data = _get_with_retry(params)

        # Build a lookup from normalized/resolved title back to our input name
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            page_title = page.get("title", "")
            # Strip "Category:" prefix to match our input format
            cat_name = page_title.replace("Category:", "", 1)
            parents = []
            for cat in page.get("categories", []):
                parent_name = cat["title"].replace("Category:", "", 1)
                parents.append(parent_name)
            if cat_name in result:
                result[cat_name] = parents

        time.sleep(delay)

    return result


def fetch_category_chain(start_categories: list[str], max_depth: int = 5, delay: float = 0.5) -> dict[int, list[str]]:
    """BFS up the Wikipedia category parent hierarchy.

    Returns {depth: [category_names]} where depth 0 is not included
    (that's the article's direct categories).
    """
    visited = set(start_categories)
    current_level = list(start_categories)
    result = {}

    for depth in range(1, max_depth + 1):
        if not current_level:
            break

        parents_map = fetch_parent_categories_batch(current_level, delay=delay)
        all_parents = []
        for parent_list in parents_map.values():
            for p in parent_list:
                if p not in visited:
                    visited.add(p)
                    all_parents.append(p)

        if all_parents:
            result[depth] = all_parents
        current_level = all_parents

    return result
