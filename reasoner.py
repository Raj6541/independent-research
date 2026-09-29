from evidence import build_evidence
from contradiction import detect

def reason(question, facts):
    evidence = build_evidence(facts)
    conflicts = detect(evidence)

    if not evidence:
        return {
            "answer": None,
            "confidence": 0.0,
            "evidence": [],
            "conflicts": conflicts,
        }

    top = evidence[0]
    total = sum(x.support for x in evidence[:5])
    dominance = top.support / total if total else 0
    independence = min(top.sources / 4, 1.0)

    confidence = min(.98, .45 + dominance * .30 + independence * .20)
    if conflicts:
        confidence *= .82

    return {
        "answer": top.value,
        "confidence": round(confidence, 3),
        "evidence": evidence,
        "conflicts": conflicts,
    }
