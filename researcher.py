import re
import time
import requests
from collections import Counter
from bs4 import BeautifulSoup
from search import search_web, remove_duplicates, get_domain

USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
HEADERS={"User-Agent":USER_AGENT,"Accept-Language":"en-US,en;q=0.9"}
TRUSTED={"gov.in":10,"nic.in":10,"gov":10,"edu":8,"ac.in":8,"who.int":10,"un.org":10,"worldbank.org":9,"nasa.gov":10,"britannica.com":8,"wikipedia.org":6}
STOP=set("a an and are as at be been by for from has have had he her here him his how i if in into is it its me more most my of on or our she so than that the their them there these they this those to was we were what when where which who why will with you your can could would should do does did about after before during over under".split())

def words(text):
    return [w for w in re.findall(r"[A-Za-z0-9]+",text.lower()) if len(w)>2 and w not in STOP]

def domain_score(domain):
    score=4
    for d,p in TRUSTED.items():
        if domain==d or domain.endswith("."+d): score=max(score,p)
    return score

def relevance(text,query):
    q=set(words(query)); t=set(words(text))
    return len(q&t)/len(q)*10 if q else 0

def classify(question):
    q=question.lower()
    if re.search(r"\b(who|person|founder|author|inventor|president|ceo)\b",q): return "person"
    if re.search(r"\b(when|year|date|founded|born|died|established)\b",q): return "date"
    if re.search(r"\b(where|location|capital|located)\b",q): return "location"
    if re.search(r"\b(how many|how much|percentage|percent|population|number|distance|area|height|weight)\b",q): return "number"
    if re.search(r"\b(why|cause|reason|effect|impact)\b",q): return "cause"
    if re.search(r"\b(compare|difference|versus|vs\.?|better)\b",q): return "comparison"
    if re.search(r"\b(what is|what are|define|meaning|explain)\b",q): return "definition"
    return "general"

def build_queries(question,kind):
    q=question.strip()
    extra={
        "person":["official biography","who"],
        "date":["official history","date year"],
        "location":["official location","where"],
        "number":["statistics","official data"],
        "cause":["research evidence","causes"],
        "comparison":["comparison","difference"],
        "definition":["definition","official explanation"],
        "general":["facts","official source"]
    }[kind]
    return [q]+[q+" "+x for x in extra]

def fetch_page(url,timeout=15):
    try:
        r=requests.get(url,headers=HEADERS,timeout=timeout,allow_redirects=True)
        if r.status_code>=400 or "text/html" not in r.headers.get("content-type","").lower(): return ""
        soup=BeautifulSoup(r.text,"html.parser")
        for tag in soup(["script","style","noscript","svg","canvas","nav","footer","header","form","aside","iframe","template"]): tag.decompose()
        blocks=soup.select("article,main,[role='main']")
        text=" ".join(x.get_text(" ",strip=True) for x in blocks) if blocks else (soup.body or soup).get_text(" ",strip=True)
        return re.sub(r"\s+"," ",text)[:90000]
    except requests.RequestException:
        return ""

def split_sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+",text) if 30<=len(x.strip())<=900]

def evidence(text,question,url,kind):
    out=[]
    for s in split_sentences(text):
        rel=relevance(s,question)
        if rel<1.0: continue
        out.append({"text":s,"url":url,"domain":get_domain(url),"relevance":round(rel,2),"kind":kind})
    return sorted(out,key=lambda x:x["relevance"],reverse=True)[:15]

def candidate(sentence,question,kind):
    q=question.lower()
    patterns={
        "person":[r"\b(?:is|was|named|known as)\s+([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,4})"],
        "date":[r"\b(?:in|on|during|from)\s+(\d{3,4}(?:\s*(?:BC|BCE|AD|CE))?)\b",r"\b(\d{4})\b"],
        "number":[r"\b(\d+(?:[.,]\d+)?\s*(?:%|percent|million|billion|thousand|km|m|kg|years?|people)?)\b"],
        "location":[r"\b(?:located in|situated in|capital of|based in)\s+([A-Z][A-Za-z .,'-]{2,60})"],
    }
    pats=patterns.get(kind,[])
    for p in pats:
        m=re.search(p,sentence)
        if m: return m.group(1).strip(" .,;:")
    return ""

def rank_candidates(items,question,kind):
    counts=Counter()
    examples={}
    for item in items:
        c=candidate(item["text"],question,kind)
        if c:
            key=c.lower()
            weight=max(.1,item["relevance"]/10)*max(.5,domain_score(item["domain"])/10)
            counts[key]+=weight
            examples.setdefault(key,item)
    ranked=counts.most_common()
    return [(key,score,examples[key]) for key,score in ranked]

def conflicts(items,question,kind):
    ranked=rank_candidates(items,question,kind)
    if len(ranked)<2: return []
    top=ranked[:4]
    total=sum(x[1] for x in top)
    if total and top[0][1]/total<.72:
        return [{"candidate":x[0],"support":round(x[1],2),"source":x[2]["url"]} for x in top]
    return []

def construct_answer(question,kind,items):
    ranked=rank_candidates(items,question,kind)
    if ranked and kind in {"person","date","number","location"}:
        top=ranked[0]
        support=top[1]
        other=sum(x[1] for x in ranked[1:4])
        confidence=min(.96,.45+support/(support+other+1)*.45+min(len({x["domain"] for x in items if candidate(x["text"],question,kind).lower()==top[0]}),3)*.04)
        ex=top[2]
        return f"The most supported answer is: {ex['text']}\n\nExtracted answer: {top[0]}",round(confidence,2),ranked

    selected=[]; seen=set()
    for x in sorted(items,key=lambda x:x["relevance"],reverse=True):
        if x["domain"] in seen and len(selected)<3: continue
        selected.append(x); seen.add(x["domain"])
        if len(selected)>=4: break
    if not selected: return "No usable evidence was found.",0.0,ranked
    avg=sum(x["relevance"] for x in selected)/len(selected)
    return "\n".join(["Based on the strongest retrieved evidence:"]+[f"- {x['text']}\n  Source: {x['url']}" for x in selected]),round(min(.9,.35+avg/20+min(len(seen),4)*.08),2),ranked

def research(query,results_per_query=7,pages_to_read=14,rounds=2):
    kind=classify(query)
    print(f"\n[QUESTION TYPE] {kind}")
    all_results=[]; all_evidence=[]
    for rnd in range(1,rounds+1):
        print(f"\n[RESEARCH ROUND {rnd}/{rounds}]")
        queries=build_queries(query,kind)
        if rnd>1:
            queries += [query+" exact answer",query+" facts verified",query+" reliable source"]
        for q in queries:
            print("  Search:",q)
            all_results.extend(search_web(q,results_per_query))
        all_results=remove_duplicates(all_results)
        for x in all_results:
            x["domain"]=get_domain(x["url"])
            x["score"]=round(domain_score(x["domain"])*.55+relevance(x["title"]+" "+x["snippet"],query)*.45,2)
        all_results.sort(key=lambda x:x["score"],reverse=True)
        print(f"[RESULTS] {len(all_results)}")
        print("[READING SOURCES]")
        for x in all_results[:pages_to_read]:
            page=fetch_page(x["url"])
            if page: all_evidence.extend(evidence(page,query,x["url"],kind))
            elif x.get("snippet"):
                all_evidence.append({"text":x["snippet"],"url":x["url"],"domain":x["domain"],"relevance":round(relevance(x["snippet"],query),2),"kind":kind})
            time.sleep(.2)
        answer,confidence,ranked=construct_answer(query,kind,all_evidence)
        print(f"[EVIDENCE] {len(all_evidence)} | [CONFIDENCE] {confidence:.0%}")
        if confidence>=.72 or rnd==rounds:
            break
        print("[DECISION] Evidence is weak; researching again.")
    conflict=conflicts(all_evidence,query,kind)
    if conflict:
        answer+="\n\nPossible disagreement detected between candidate answers:\n"+ "\n".join(f"- {x['candidate']} (support {x['support']})" for x in conflict)
    return {"answer":answer,"confidence":confidence,"question_type":kind,"sources":all_results,"evidence":all_evidence,"candidates":[{"answer":x[0],"support":round(x[1],2),"source":x[2]["url"]} for x in ranked[:5]],"conflicts":conflict}
