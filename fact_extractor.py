import re
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
from question_parser import Question

@dataclass
class Fact:
    subject: str
    relation: str
    value: str
    sentence: str
    url: str
    domain: str
    score: float

def domain(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host

def sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if 25 <= len(x.strip()) <= 900]

def relevance(sentence, question):
    terms = set(re.findall(r"[a-z0-9]+", question.raw.lower()))
    terms -= {"the","a","an","is","are","was","were","what","who","when","where","why","how","of","in","on","to","for"}
    if not terms:
        return 0
    low = sentence.lower()
    return sum(1 for t in terms if t in low) / len(terms)

def extract_facts(text, url, question, limit=25):
    out = []
    for s in sentences(text):
        rel = relevance(s, question)
        if rel < 0.25:
            continue

        value = ""
        if question.answer_type == "number":
            m = re.search(r"\b\d[\d,]*(?:\.\d+)?\s*(?:%|percent|million|billion|thousand|km²|km|m|kg|years?|people)?\b", s, re.I)
            if m: value = m.group(0)
        elif question.answer_type == "date":
            m = re.search(r"\b(?:\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4}|\d{4})\b", s)
            if m: value = m.group(0)
        elif question.answer_type == "person":
            m = re.search(r"\b(?:by|founded by|created by|invented by|written by|named)\s+([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,4})", s)
            if m: value = m.group(1)
        elif question.answer_type == "place":
            m = re.search(r"\b(?:located in|situated in|capital of|based in)\s+([A-Z][A-Za-z .,'-]{2,60})", s)
            if m: value = m.group(1).strip(" .,")
        else:
            value = s

        if not value:
            value = s

        out.append(Fact(question.subject, question.relation, value, s, url, domain(url), round(rel, 3)))

    return sorted(out, key=lambda x: x.score, reverse=True)[:limit]

def as_dict(fact):
    return asdict(fact)
