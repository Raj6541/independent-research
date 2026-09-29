from collections import defaultdict
from dataclasses import dataclass, asdict
from fact_extractor import Fact

TRUSTED = {
    "gov.in": 1.0, "nic.in": 1.0, "gov": 1.0, "edu": .9,
    "ac.in": .9, "who.int": 1.0, "un.org": 1.0,
    "worldbank.org": .95, "nasa.gov": 1.0, "britannica.com": .85,
    "wikipedia.org": .65,
}

def authority(domain):
    score = .5
    for d, value in TRUSTED.items():
        if domain == d or domain.endswith("." + d):
            score = max(score, value)
    return score

@dataclass
class Evidence:
    value: str
    support: float
    sources: int
    domains: list
    facts: list

def normalize(value):
    return " ".join(value.lower().strip().split())

def build_evidence(facts):
    groups = defaultdict(list)
    for fact in facts:
        groups[normalize(fact.value)].append(fact)

    result = []
    for value, items in groups.items():
        domains = sorted(set(x.domain for x in items))
        support = sum(x.score * authority(x.domain) for x in items)
        support += min(len(domains), 5) * .20
        result.append(Evidence(value, round(support, 4), len(items), domains, items))
    return sorted(result, key=lambda x: x.support, reverse=True)
