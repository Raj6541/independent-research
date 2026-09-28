import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)

def search_web(query, max_results=10):
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"[SEARCH ERROR] {error}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result in soup.select(".result"):
        title_element = result.select_one(".result__title")
        link_element = result.select_one(".result__a")
        snippet_element = result.select_one(".result__snippet")

        if not link_element:
            continue

        title = (
            title_element.get_text(" ", strip=True)
            if title_element
            else link_element.get_text(" ", strip=True)
        )
        link = link_element.get("href", "").strip()
        snippet = (
            snippet_element.get_text(" ", strip=True)
            if snippet_element
            else ""
        )

        if not link:
            continue

        results.append({
            "title": title,
            "url": link,
            "snippet": snippet
        })

        if len(results) >= max_results:
            break

    return results

def get_domain(url):
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""

def remove_duplicates(results):
    seen = set()
    unique = []

    for result in results:
        url = result["url"]
        if url in seen:
            continue
        seen.add(url)
        unique.append(result)

    return unique
