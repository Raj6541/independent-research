#!/usr/bin/env python3
"""Independent Research Engine v1.0 - deterministic web research, no LLM/API."""
import argparse,json,re,sys,time
from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from urllib.parse import parse_qs,quote,unquote,urlparse
import requests
from bs4 import BeautifulSoup

VERSION="1.0.0"; USER_AGENT="IndependentResearchEngine/1.0 (research tool)"
STOPWORDS=set("""a an and are as at be been being by for from has have had he her here hers him his how i if in into is it its me more most my of on or our ours she so than that the their them there these they this those to was we were what when where which who why will with you your yours can could would should do does did about after before during over under""".split())
TRUSTED={"gov.in":.98,"nic.in":.97,"ac.in":.90,"edu.in":.90,"gov":.98,"edu":.90,"who.int":.99,"un.org":.98,"worldbank.org":.97,"imf.org":.97,"oecd.org":.96,"nasa.gov":.99,"python.org":.99,"docs.python.org":.99,"britannica.com":.88,"wikipedia.org":.74}
LOW_VALUE={"pinterest.com","quora.com","medium.com"}
BLOCKED_EXTENSIONS={".jpg",".jpeg",".png",".gif",".webp",".svg",".mp4",".mp3",".zip",".rar",".7z",".exe",".dmg",".iso"}
DEFAULT_TIMEOUT=15; DEFAULT_DELAY=.8; DEFAULT_MAX_PAGES=18; DEFAULT_MAX_ROUNDS=3; DEFAULT_THRESHOLD=.58; DEFAULT_MAX_CHARS=50000

@dataclass
class SearchResult:
    title:str; url:str; snippet:str; domain:str=""; query:str=""; search_rank:int=0; score:float=0
@dataclass
class PageDocument:
    url:str; title:str; domain:str; text:str; status:int; content_type:str; fetched_at:str; word_count:int=0
@dataclass
class Evidence:
    claim:str; sentence:str; url:str; domain:str; score:float; kind:str="statement"
@dataclass
class Report:
    question:str; answer:str; confidence:float; evidence:list=field(default_factory=list); sources:list=field(default_factory=list); contradictions:list=field(default_factory=list); rounds:int=0; notes:list=field(default_factory=list); generated_at:str=""

def now_iso(): return datetime.now(timezone.utc).isoformat()
def clean(x): return re.sub(r"\s+"," ",x or "").strip()
def tokens(x): return [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]{1,}",x.lower()) if w not in STOPWORDS and len(w)>2]
def similarity(a,b):
    A,B=set(tokens(a)),set(tokens(b)); return len(A&B)/len(A|B) if A and B else 0
def domain_of(url):
    try:
        h=urlparse(url).netloc.lower().split("@")[-1].split(":")[0]; return h[4:] if h.startswith("www.") else h
    except Exception:return ""
def canonical_url(url):
    try:
        p=urlparse(url); host=domain_of(url); path=re.sub(r"/+","/",p.path or "/")
        if path!="/" and path.endswith("/"): path=path[:-1]
        ignored={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid","ref"}
        q=[]
        for k in sorted(parse_qs(p.query)):
            if k.lower() in ignored: continue
            q += [(k,v) for v in parse_qs(p.query)[k]]
        query="&".join(f"{quote(k)}={quote(v)}" for k,v in q)
        return f"{p.scheme.lower() or 'https'}://{host}{path}"+(f"?{query}" if query else "")
    except Exception:return url.strip()
def authority(d):
    d=d.lower(); s=.50
    for k,v in TRUSTED.items():
        if d==k or d.endswith("."+k): s=max(s,v)
    if d in LOW_VALUE:s=min(s,.38)
    return s
def question_type(q):
    q=q.lower()
    if re.search(r"\b(who|founder|ceo|president|person)\b",q): return "person"
    if re.search(r"\b(when|date|year|history|founded|born|died)\b",q): return "history"
    if re.search(r"\b(where|location|place|capital)\b",q): return "location"
    if re.search(r"\b(how many|number|population|percentage|percent|rate)\b",q): return "numeric"
    if re.search(r"\b(why|cause|reason|impact|effect)\b",q): return "causal"
    if re.search(r"\b(latest|current|today|now|recent|newest)\b",q): return "current"
    return "general"
def build_queries(question,round_no=1,missing=None):
    q=clean(question); kind=question_type(q)
    suf={"person":["official","biography"],"history":["official history","timeline"],"location":["official","facts"],"numeric":["statistics","official data"],"causal":["evidence causes","study analysis"],"current":["latest official","2026"],"general":["facts","official"]}[kind]
    arr=[q]+[f"{q} {x}" for x in suf]
    if missing: arr += [f"{q} {x}" for x in list(missing)[:3]]
    if round_no>1: arr += [f"{q} report evidence",f"{q} site:gov.in",f"{q} source data"]
    out=[]; seen=set()
    for x in arr:
        x=clean(x)
        if x.lower() not in seen: seen.add(x.lower()); out.append(x)
    return out[:8]
def relevance(text,question):
    q,s=set(tokens(question)),set(tokens(text)); return min(1,(len(q&s)/len(q))*1.8) if q else 0
def numbers(text):
    return re.findall(r"\b\d+(?:[.,]\d+)?(?:\s?(?:%|percent|million|billion|thousand|km|m|kg|°C|°F))?\b",text,re.I)
def sentence_split(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",clean(text)) if 30<=len(x.strip())<=900]

class WebSearch:
    def __init__(self,timeout=DEFAULT_TIMEOUT,delay=DEFAULT_DELAY,max_results=8):
        self.timeout,self.delay,self.max_results=timeout,delay,max_results
        self.session=requests.Session(); self.session.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"en-US,en;q=0.9"})
    def search_one(self,query):
        try:
            r=self.session.get("https://html.duckduckgo.com/html/?q="+quote(query),timeout=self.timeout); r.raise_for_status()
        except requests.RequestException as e: print(f"  [search error] {e}"); return []
        soup=BeautifulSoup(r.text,"html.parser"); out=[]
        for rank,item in enumerate(soup.select(".result"),1):
            a=item.select_one(".result__a")
            if not a: continue
            href=a.get("href","").strip()
            if "uddg=" in href:
                try: href=unquote(parse_qs(urlparse(href).query).get("uddg",[href])[0])
                except Exception: pass
            title=clean(a.get_text(" ",strip=True)); sn=item.select_one(".result__snippet"); snippet=clean(sn.get_text(" ",strip=True) if sn else "")
            if href and title: out.append(SearchResult(title,canonical_url(href),snippet,domain_of(href),query,rank))
            if len(out)>=self.max_results: break
        time.sleep(self.delay); return out
    def search(self,queries):
        unique={}
        for i,q in enumerate(queries,1):
            print(f"  Search {i}/{len(queries)}: {q}")
            for x in self.search_one(q):
                k=canonical_url(x.url)
                if k not in unique: unique[k]=x
                else: unique[k].search_rank=min(unique[k].search_rank,x.search_rank)
        return list(unique.values())

class PageReader:
    def __init__(self,timeout=DEFAULT_TIMEOUT,delay=DEFAULT_DELAY,max_chars=DEFAULT_MAX_CHARS):
        self.timeout,self.delay,self.max_chars=timeout,delay,max_chars
        self.session=requests.Session(); self.session.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"en-US,en;q=0.9"})
    def fetch(self,url):
        p=urlparse(url)
        if p.scheme not in {"http","https"} or any(p.path.lower().endswith(x) for x in BLOCKED_EXTENSIONS): return None
        try:
            r=self.session.get(url,timeout=self.timeout,allow_redirects=True); ct=r.headers.get("content-type","").lower()
            if r.status_code>=400 or "text/html" not in ct:return None
            soup=BeautifulSoup(r.text,"html.parser")
            for tag in soup(["script","style","noscript","svg","canvas","nav","footer","header","form","aside","iframe","template"]):tag.decompose()
            title=clean(soup.title.get_text(" ",strip=True) if soup.title else "")
            main=soup.find("main") or soup.find("article") or soup.body or soup
            text=clean(main.get_text(" ",strip=True))[:self.max_chars]
            if len(text.split())<40:return None
            final=canonical_url(r.url)
            return PageDocument(final,title,domain_of(final),text,r.status_code,ct,now_iso(),len(text.split()))
        except Exception:return None
        finally:time.sleep(self.delay)

def evidence_score(sentence,question,domain,rank):
    signal=.15 if numbers(sentence) else 0
    if re.search(r"\b(is|was|were|has|had|reported|according|found|measured|announced|published|states|shows|estimated)\b",sentence,re.I):signal+=.15
    rank_signal=max(0,1-(rank-1)/20)
    return round(min(1,authority(domain)*.45+relevance(sentence,question)*.30+signal*.15+rank_signal*.10),4)
def extract_evidence(page,question,rank=10):
    c=[Evidence(s,s,page.url,page.domain,evidence_score(s,question,page.domain,rank)) for s in sentence_split(page.text) if relevance(s,question)>=.15]
    c.sort(key=lambda x:x.score,reverse=True); out=[]
    for x in c:
        if all(similarity(x.claim,y.claim)<.78 for y in out):out.append(x)
        if len(out)>=8:break
    return out
def contradiction(a,b):
    na,nb=a.lower(),b.lower()
    if numbers(na) and numbers(nb) and numbers(na)!=numbers(nb) and similarity(na,nb)>=.48:return True
    pairs=[("yes","no"),("true","false"),("increased","decreased"),("increase","decrease"),("higher","lower"),("more","less"),("before","after"),("largest","smallest"),("present","absent")]
    return any(re.search(rf"\b{x}\b",na) and re.search(rf"\b{y}\b",nb) and similarity(na,nb)>=.30 for x,y in pairs)
def find_contradictions(evidence):
    out=[]
    for i in range(len(evidence)):
        for j in range(i+1,len(evidence)):
            a,b=evidence[i],evidence[j]
            if a.domain!=b.domain and contradiction(a.sentence,b.sentence):
                out.append({"source_a":a.url,"source_b":b.url,"claim_a":a.sentence,"claim_b":b.sentence,"score_a":a.score,"score_b":b.score})
                if len(out)>=20:return out
    return out
def confidence(evidence,conflicts):
    if not evidence:return 0
    top=sorted(evidence,key=lambda x:x.score,reverse=True); domains=len({x.domain for x in top[:12]})
    avg=sum(x.score for x in top[:5])/min(5,len(top)); independence=min(1,domains/4); penalty=min(.35,len(conflicts)*.035)
    return round(max(0,min(1,avg*.55+independence*.30+min(1,len(top)/8)*.15-penalty)),3)
def group_claims(evidence):
    groups=[]
    for x in evidence:
        for g in groups:
            if similarity(x.claim,g[0].claim)>=.42:g.append(x);break
        else:groups.append([x])
    return groups
def consensus(evidence):
    scored=[]
    for g in group_claims(evidence):
        score=sum(x.score for x in g)+min(len({x.domain for x in g}),4)*.35; scored.append((score,g))
    scored.sort(reverse=True,key=lambda x:x[0]); return [sorted(g,key=lambda x:x.score,reverse=True)[0] for _,g in scored[:3]]
def build_answer(question,evidence,conflicts,conf):
    if not evidence:return "I could not find enough usable evidence to construct a reliable answer from the retrieved pages.",["No sufficiently relevant evidence was extracted."]
    intro="Based on the strongest available evidence:" if conf>=.78 else "The available evidence indicates:" if conf>=.58 else "The available evidence is limited, so this is tentative:"
    used=set(); lines=[intro]
    for x in consensus(evidence):
        if x.sentence.lower() not in used:used.add(x.sentence.lower());lines.append("- "+clean(x.sentence))
    notes=[]
    if conflicts:notes.append(f"{len(conflicts)} possible cross-source disagreement(s) were detected.")
    domains=sorted({x.domain for x in consensus(evidence)})
    if domains:notes.append("Primary evidence domains: "+", ".join(domains))
    return "\n".join(lines),notes

class ResearchEngine:
    def __init__(self,max_pages=DEFAULT_MAX_PAGES,rounds=DEFAULT_MAX_ROUNDS,threshold=DEFAULT_THRESHOLD,timeout=DEFAULT_TIMEOUT,delay=DEFAULT_DELAY):
        self.max_pages,self.rounds,self.threshold=max_pages,rounds,threshold; self.search=WebSearch(timeout,delay); self.reader=PageReader(timeout,delay)
    def run(self,question):
        question=clean(question)
        if not question:raise ValueError("Question cannot be empty.")
        results={}; evidence=[]; notes=[]; conflicts=[]; completed=0
        for rnd in range(1,self.rounds+1):
            completed=rnd; print(f"\n{'='*72}\nRESEARCH ROUND {rnd}/{self.rounds}\n{'='*72}")
            for r in self.search.search(build_queries(question,rnd)):
                rel=relevance(r.title+" "+r.snippet,question); rank=max(0,1-(r.search_rank-1)/20)
                r.score=round(authority(r.domain)*.55+rel*.30+rank*.15,4); results.setdefault(canonical_url(r.url),r)
            ranked=sorted(results.values(),key=lambda x:x.score,reverse=True); print(f"\n[FETCH] Candidate pages: {len(ranked)}")
            fetched={x.url for x in evidence}
            for r in ranked[:self.max_pages]:
                if r.url in fetched:continue
                print(f"  Reading: {r.domain} — {r.title[:65]}")
                page=self.reader.fetch(r.url)
                if page:evidence.extend(extract_evidence(page,question,r.search_rank))
            dedup=[]
            for x in sorted(evidence,key=lambda x:x.score,reverse=True):
                if not any(x.url==old.url and similarity(x.claim,old.claim)>=.80 for old in dedup):dedup.append(x)
            evidence=dedup[:120]; conflicts=find_contradictions(evidence); conf=confidence(evidence,conflicts)
            print(f"[EVIDENCE] {len(evidence)} claims"); print(f"[SOURCES]  {len({x.domain for x in evidence})} domains"); print(f"[CONFLICT] {len(conflicts)} possible conflicts"); print(f"[CONFIDENCE] {conf:.1%}")
            if conf>=self.threshold and len(evidence)>=4:notes.append(f"Stopped after round {rnd}: evidence threshold reached.");break
            if rnd<self.rounds:notes.append(f"Round {rnd} was below threshold; additional research attempted.")
        conf=confidence(evidence,conflicts); answer,answer_notes=build_answer(question,evidence,conflicts,conf); notes.extend(answer_notes)
        return Report(question,answer,conf,sorted(evidence,key=lambda x:x.score,reverse=True),sorted(results.values(),key=lambda x:x.score,reverse=True),conflicts,completed,notes,now_iso())

def print_report(r):
    print("\n"+"="*80+"\nFINAL RESEARCH REPORT\n"+"="*80); print(f"\nQuestion:\n{r.question}"); print(f"\nConfidence: {r.confidence:.1%}"); print(f"Research rounds: {r.rounds}"); print("\nANSWER\n"+"-"*80); print(r.answer)
    print("\nTOP SOURCES\n"+"-"*80)
    for i,s in enumerate(r.sources[:10],1):print(f"{i}. {s.title}\n   {s.domain} | score={s.score:.3f}\n   {s.url}")
    if r.contradictions:
        print("\nPOSSIBLE CONFLICTS\n"+"-"*80)
        for i,c in enumerate(r.contradictions[:5],1):print(f"{i}. A: {c['claim_a']}\n   B: {c['claim_b']}")
    print("\nNOTES\n"+"-"*80)
    for n in r.notes:print("- "+n)
def save_report(r,filename):
    with open(filename,"w",encoding="utf-8") as f:json.dump(asdict(r),f,ensure_ascii=False,indent=2)

def main():
    p=argparse.ArgumentParser(description="Independent rule-based web research engine.")
    p.add_argument("question",nargs="*"); p.add_argument("--max-pages",type=int,default=DEFAULT_MAX_PAGES); p.add_argument("--rounds",type=int,default=DEFAULT_MAX_ROUNDS); p.add_argument("--threshold",type=float,default=DEFAULT_THRESHOLD); p.add_argument("--timeout",type=int,default=DEFAULT_TIMEOUT); p.add_argument("--delay",type=float,default=DEFAULT_DELAY); p.add_argument("--output",default="research_report.json")
    a=p.parse_args(); question=" ".join(a.question).strip() if a.question else input("Enter your question: ").strip()
    if not question:print("Question cannot be empty.",file=sys.stderr);return 1
    try:
        r=ResearchEngine(a.max_pages,a.rounds,a.threshold,a.timeout,a.delay).run(question); print_report(r); save_report(r,a.output); print(f"\nFull report saved to: {a.output}"); return 0
    except KeyboardInterrupt:print("\nStopped.");return 130
    except Exception as e:print(f"\nFatal error: {e}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
