import re
from dataclasses import dataclass, asdict

@dataclass
class Question:
    raw: str
    intent: str
    answer_type: str
    subject: str
    relation: str
    operation: str = "lookup"

def parse_question(text: str) -> Question:
    q = text.strip()
    l = q.lower()

    intent = "general"
    answer_type = "text"
    operation = "lookup"
    relation = "related_to"

    if re.search(r"\bwho\b", l):
        intent, answer_type, relation = "lookup", "person", "person"
    elif re.search(r"\bwhen\b|\bwhat year\b|\bwhat date\b", l):
        intent, answer_type, relation = "lookup", "date", "date"
    elif re.search(r"\bwhere\b|\bwhat is the capital\b", l):
        intent, answer_type, relation = "lookup", "place", "location"
    elif re.search(r"\bhow many\b|\bhow much\b|\bpopulation\b|\bpercentage\b|\bpercent\b", l):
        intent, answer_type, relation = "numeric", "number", "quantity"
    elif re.search(r"\bwhich is (the )?(largest|biggest|highest|longest|oldest|smallest|lowest|shortest|newest)\b", l):
        intent, answer_type = "comparison", "entity"
        operation = re.search(r"\b(largest|biggest|highest|longest|oldest|smallest|lowest|shortest|newest)\b", l).group(1)
    elif re.search(r"\b(compare|difference between|versus|vs\.? )\b", l):
        intent, answer_type = "comparison", "comparison"
    elif re.search(r"\bwhy\b|\bcause\b", l):
        intent, answer_type, relation = "causal", "explanation", "cause"
    elif re.search(r"\bwhat is\b|\bwhat are\b|\bdefine\b|\bmeaning of\b", l):
        intent, answer_type, relation = "definition", "definition", "definition"

    subject = re.sub(r"\?$", "", q)
    subject = re.sub(r"^(who|what|when|where|why|how)\b", "", subject, flags=re.I).strip()
    return Question(q, intent, answer_type, subject, relation, operation)

def to_dict(q: Question):
    return asdict(q)
