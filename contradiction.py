import re
from evidence import Evidence

def numeric_value(text):
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text.replace(",", ""))
    return float(m.group()) if m else None

def detect(evidence):
    if len(evidence) < 2:
        return []

    conflicts = []
    numeric = [(e, numeric_value(e.value)) for e in evidence]
    numeric = [(e,v) for e,v in numeric if v is not None]

    if len(numeric) >= 2:
        values = {}
        for e,v in numeric:
            values.setdefault(v, []).append(e.value)
        if len(values) > 1:
            conflicts.append({
                "type": "numeric_disagreement",
                "values": sorted(values.keys()),
            })

    return conflicts
