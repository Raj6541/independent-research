import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse, parse_qs, unquote

USER_AGENT = "IndependentResearch/1.0 (+https://github.com/Raj6541/independent-research)"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

def get_domain(url):
    try:
        host = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""

def clean_url(url):
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # DuckDuckGo sometimes returns a redirect URL containing uddg.
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            url = unquote(qs["uddg"][0])
        return url.strip()
    except Exception:
        return url.strip()

def _parse_results(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # DDG HTML has changed markup over time, so use several selectors.
    candidates = soup.select(".result") or soup.select(".web-result") or soup.select("article")
    for item in candidates:
        link = (
            item.select_one("a.result__a")
            or item.select_one("a.result-link")
            or item.select_one("h2 a")
            or item.find("a", href=True)
        )
        if not link:
            continue

        url = clean_url(link.get("href", ""))
        if not url.startswith(("http://", "https://")):
            continue

        title = link.get_text(" ", strip=True)
        snippet_el = (
            item.select_one(".result__snippet")
            or item.select_one(".result-snippet")
            or item.select_one(".snippet")
        )
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results

def search_web(query, max_results=10, timeout=15):
    endpoints = [
        "https://html.duckduckgo.com/html/?q=",
        "https://lite.duckduckgo.com/lite/?q=",
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(
                endpoint + quote(query),
                headers=HEADERS,
                timeout=timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            results = _parse_results(response.text)
            if results:
                return results[:max_results]
        except requests.RequestException:
            continue

    print("[SEARCH ERROR] Search engine returned no usable results.")
    return []

def remove_duplicates(results):
    seen = set()
    unique = []
    for result in results:
        key = clean_url(result.get("url", "")).rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique
