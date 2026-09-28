from search import search_web, remove_duplicates, get_domain

TRUSTED_DOMAINS = {
    "gov.in": 10,
    "nic.in": 10,
    "gov": 10,
    "edu": 8,
    "ac.in": 8,
    "who.int": 10,
    "un.org": 10,
    "worldbank.org": 9,
    "britannica.com": 8,
    "nasa.gov": 10,
}

def domain_score(domain):
    score = 0
    for trusted_domain, points in TRUSTED_DOMAINS.items():
        if domain == trusted_domain or domain.endswith("." + trusted_domain):
            score = max(score, points)
    return score

def relevance_score(result, query):
    text = (result["title"] + " " + result["snippet"]).lower()
    words = [
        word.strip(".,!?;:()[]{}\"'")
        for word in query.lower().split()
    ]
    words = [word for word in words if len(word) > 2]

    if not words:
        return 0

    matches = sum(1 for word in words if word in text)
    return matches / len(words) * 10

def score_result(result, query):
    domain = get_domain(result["url"])
    authority = domain_score(domain)
    relevance = relevance_score(result, query)
    total = authority * 0.6 + relevance * 0.4
    return round(total, 2)

def research(query, results_per_query=8):
    print("\n[1] Creating search queries...")

    queries = [
        query,
        query + " facts",
        query + " official",
    ]

    all_results = []

    print("[2] Searching web...")

    for search_query in queries:
        print(f"    → {search_query}")
        results = search_web(search_query, max_results=results_per_query)
        all_results.extend(results)

    print("[3] Removing duplicate results...")
    all_results = remove_duplicates(all_results)

    print("[4] Scoring sources...")

    for result in all_results:
        result["domain"] = get_domain(result["url"])
        result["score"] = score_result(result, query)

    all_results.sort(key=lambda item: item["score"], reverse=True)
    return all_results
