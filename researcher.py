import re
import time
import requests
from bs4 import BeautifulSoup
from search import search_web, remove_duplicates, get_domain

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

TRUSTED_DOMAINS = {
    "gov.in":10, "nic.in":10, "gov":10, "edu":8, "ac.in":8,
    "who.int":10, "un.org":10, "worldbank.org":9, "nasa.gov":10,
    "britannica.com":8, "wikipedia.org":6
}
STOPWORDS=set("a an and are as at be been by for from has have had he her here him his how i if in into is it its me more most my of on or our she so than that the their them there these they this those to was we were what when where which who why will with you your can could would should do does did about after before during over under".split())

def domain_score(domain):
    score=4
    for trusted,points in TRUSTED_DOMAINS.items():
        if domain==trusted or domain.endswith("."+trusted):
            score=max(score,points)
    return score

def words(text):
    return [w for w in re.findall(r"[A-Za-z0-9]+",text.lower()) if len(w)>2 and w not in STOPWORDS]

def relevance_score(text,query):
    q=set(words(query))
    return len(q & set(words(text)))/len(q)*10 if q else 0

def score_result(result,query):
    return round(domain_score(result["domain"])*.55+relevance_score(result["title"]+" "+result["snippet"],query)*.45,2)

def fetch_page(url,timeout=15):
    try:
        r=requests.get(url,headers=HEADERS,timeout=timeout,allow_redirects=True)
        if r.status_code>=400 or "text/html" not in r.headers.get("content-type","").lower():
            return ""
        soup=BeautifulSoup(r.text,"html.parser")
        for tag in soup(["script","style","noscript","svg","canvas","nav","footer","header","form","aside","iframe","template"]):
            tag.decompose()
        # Prefer article/main content, but fall back to body.
        blocks=soup.select("article,main,[role='main']")
        if blocks:
            text=" ".join(x.get_text(" ",strip=True) for x in blocks)
        else:
            text=(soup.body or soup).get_text(" ",strip=True)
        text=re.sub(r"\s+"," ",text)
        return text[:80000]
    except requests.RequestException:
        return ""

def sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+",text) if 35<=len(x.strip())<=800]

def extract_evidence(text,query,url,limit=10):
    found=[]
    for sentence in sentences(text):
        score=relevance_score(sentence,query)
        if score>=1.0:
            found.append({"text":sentence,"url":url,"domain":get_domain(url),"relevance":round(score,2)})
    found.sort(key=lambda x:x["relevance"],reverse=True)
    return found[:limit]

def build_queries(query):
    return [query,query+" facts",query+" official source",query+" information",query+" explained"]

def make_answer(evidence,search_results):
    if not evidence:
        # Search snippets are still useful evidence when pages block automated reading.
        usable=[x for x in search_results if x.get("snippet")]
        if usable:
            usable=sorted(usable,key=lambda x:x.get("score",0),reverse=True)[:5]
            text="I could not read the source pages directly, but the search results provide these relevant findings:\n\n"
            for i,x in enumerate(usable,1):
                text+=f"{i}. {x['snippet']}\n   Source: {x['url']}\n"
            return text,.35
        return "No usable search results or readable source evidence were returned. Try again or check your internet connection.",0.0

    selected=[]; domains=set()
    for item in sorted(evidence,key=lambda x:x["relevance"],reverse=True):
        if item["domain"] in domains and len(selected)<2:
            continue
        selected.append(item); domains.add(item["domain"])
        if len(selected)>=5: break

    avg=sum(x["relevance"] for x in selected)/len(selected)
    confidence=min(.95,.40+avg/20+min(len(domains),4)*.08)
    text="Based on the retrieved sources:\n\n"
    for i,item in enumerate(selected,1):
        text+=f"{i}. {item['text']}\n   Source: {item['url']}\n"
    return text,round(confidence,2)

def research(query,results_per_query=6,pages_to_read=12):
    print("\n[1] Creating search queries...")
    queries=build_queries(query)
    print("[2] Searching web...")
    results=[]
    for q in queries:
        print("    ->",q)
        results.extend(search_web(q,results_per_query))
    results=remove_duplicates(results)
    if not results:
        return {"answer":"Search returned no results. The search provider may be blocking automated requests or the network may be unavailable.","confidence":0.0,"sources":[],"evidence":[]}

    print(f"[3] Found {len(results)} search results.")
    for item in results:
        item["domain"]=get_domain(item["url"])
        item["score"]=score_result(item,query)
    results.sort(key=lambda x:x["score"],reverse=True)

    print("[4] Reading source pages...")
    evidence=[]
    for item in results[:pages_to_read]:
        print("    ->",item["domain"],item["title"][:55])
        page=fetch_page(item["url"])
        if page:
            evidence.extend(extract_evidence(page,query,item["url"]))
        time.sleep(.3)

    print(f"[5] Extracted {len(evidence)} evidence items.")
    answer,confidence=make_answer(evidence,results)
    return {"answer":answer,"confidence":confidence,"sources":results,"evidence":evidence}
