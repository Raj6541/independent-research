import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse, parse_qs, unquote

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

def get_domain(url):
    try:
        host = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""

def clean_url(url):
    try:
        if not url:
            return ""
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
        if "url" in qs and "yahoo" in parsed.netloc:
            return unquote(qs["url"][0])
        return url.strip()
    except Exception:
        return url.strip()

def parse_duckduckgo(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select(".result"):
        link = item.select_one("a.result__a") or item.select_one("a[href]")
        if not link:
            continue
        url = clean_url(link.get("href", ""))
        if not url.startswith(("http://", "https://")):
            continue
        title = link.get_text(" ", strip=True)
        snip = item.select_one(".result__snippet")
        snippet = snip.get_text(" ", strip=True) if snip else ""
        if title:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results

def parse_bing(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select("li.b_algo"):
        link = item.select_one("h2 a")
        if not link:
            continue
        url = clean_url(link.get("href", ""))
        title = link.get_text(" ", strip=True)
        snip = item.select_one(".b_caption p") or item.select_one("p")
        snippet = snip.get_text(" ", strip=True) if snip else ""
        if url.startswith(("http://", "https://")) and title:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results

def search_duckduckgo(query, timeout=15):
    for base in (
        "https://html.duckduckgo.com/html/?q=",
        "https://lite.duckduckgo.com/lite/?q="
    ):
        try:
            r = requests.get(base + quote(query), headers=HEADERS, timeout=timeout)
            if r.ok:
                results = parse_duckduckgo(r.text)
                if results:
                    return results
        except requests.RequestException:
            pass
    return []

def search_bing(query, timeout=15):
    try:
        r = requests.get("https://www.bing.com/search?q=" + quote(query),
                         headers=HEADERS, timeout=timeout)
        if r.ok:
            return parse_bing(r.text)
    except requests.RequestException:
        pass
    return []

def search_web(query, max_results=10, timeout=15):
    # Try more than one provider because public HTML search pages can block automation.
    results = search_duckduckgo(query, timeout)
    if len(results) < 3:
        results += search_bing(query, timeout)

    seen = set()
    unique = []
    for item in results:
        url = clean_url(item.get("url", "")).rstrip("/")
        if not url or url.lower() in seen:
            continue
        seen.add(url.lower())
        unique.append({
            "title": item.get("title", "").strip(),
            "url": url,
            "snippet": item.get("snippet", "").strip()
        })
        if len(unique) >= max_results:
            break
    return unique

def remove_duplicates(results):
    seen = set()
    unique = []
    for result in results:
        key = clean_url(result.get("url", "")).rstrip("/").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(result)
    return unique
