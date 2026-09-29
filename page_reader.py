import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 IndependentResearch/1.0",
    "Accept-Language": "en-US,en;q=0.9",
}

def read_page(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code >= 400:
            return ""
        if "text/html" not in r.headers.get("content-type", "").lower():
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","noscript","svg","canvas","nav","footer","header","form","aside","iframe","template"]):
            tag.decompose()
        main = soup.find("article") or soup.find("main") or soup.body or soup
        return re.sub(r"\s+", " ", main.get_text(" ", strip=True))[:100000]
    except requests.RequestException:
        return ""
