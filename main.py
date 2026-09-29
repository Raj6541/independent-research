import json
from datetime import datetime
from question_parser import parse_question, to_dict
from query_planner import plan_queries
from search import search_web, remove_duplicates, get_domain
from page_reader import read_page
from fact_extractor import extract_facts, as_dict
from reasoner import reason
from answer_engine import build_answer

def main():
    print("=" * 80)
    print("INDEPENDENT RESEARCH ENGINE V1.0")
    print("Question -> Search -> Facts -> Evidence Graph -> Reasoning -> Answer")
    print("No LLM | No AI API")
    print("=" * 80)

    raw = input("\nEnter your question: ").strip()
    if not raw:
        return

    question = parse_question(raw)
    print("\nQUESTION MODEL")
    print(json.dumps(to_dict(question), indent=2))

    facts = []
    seen = set()

    for query in plan_queries(question):
        print("\nSEARCH:", query)
        results = search_web(query, max_results=8)
        for result in remove_duplicates(results):
            url = result["url"]
            if url in seen:
                continue
            seen.add(url)

            text = read_page(url)
            if not text:
                text = result.get("snippet", "")

            if text:
                new_facts = extract_facts(text, url, question)
                facts.extend(new_facts)
                print("  FACTS:", len(new_facts))

            if len(facts) >= 100:
                break
        if len(facts) >= 100:
            break

    print("\nREASONING...")
    result = reason(question, facts)
    print("\n" + "=" * 80)
    print(build_answer(question, result))
    print("=" * 80)

    output = {
        "timestamp": datetime.now().isoformat(),
        "question": to_dict(question),
        "answer": result["answer"],
        "confidence": result["confidence"],
        "conflicts": result["conflicts"],
        "facts": [as_dict(x) for x in facts],
    }

    with open("research_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\nSaved: research_results.json")

if __name__ == "__main__":
    main()
