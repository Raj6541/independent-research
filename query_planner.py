from question_parser import Question

def plan_queries(q: Question):
    base = q.raw.strip()
    queries = [base]

    if q.intent == "comparison":
        queries += [base + " facts", base + " comparison", base + " official data"]
    elif q.intent == "numeric":
        queries += [base + " statistics", base + " official data", base + " dataset"]
    elif q.answer_type == "person":
        queries += [base + " official", base + " biography", base + " history"]
    elif q.answer_type == "date":
        queries += [base + " official history", base + " timeline"]
    elif q.answer_type == "place":
        queries += [base + " official", base + " location"]
    elif q.intent == "causal":
        queries += [base + " causes", base + " evidence", base + " research"]
    elif q.intent == "definition":
        queries += [base + " definition", base + " official explanation"]
    else:
        queries += [base + " facts", base + " official source", base + " explained"]

    return list(dict.fromkeys(queries))
