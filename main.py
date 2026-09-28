import json
from datetime import datetime
from researcher import research

def main():
    print("=" * 80)
    print("INDEPENDENT RESEARCH ENGINE V0.2")
    print("Search -> Read pages -> Extract evidence -> Build answer")
    print("No LLM | No AI API")
    print("=" * 80)
    question = input("\nEnter your question: ").strip()
    if not question:
        print("Question cannot be empty.")
        return
    results = research(question)
    print("\n" + "=" * 80)
    print("ANSWER")
    print("=" * 80)
    print(results["answer"])
    print(f"\nConfidence: {results['confidence']:.0%}")
    print("\nTOP SOURCES")
    print("-" * 80)
    for i, source in enumerate(results["sources"][:10], 1):
        print(f"{i}. {source['title']}")
        print(f"   {source['url']}")
        print(f"   Score: {source['score']}")
    data = {
        "question": question,
        "timestamp": datetime.now().isoformat(),
        **results
    }
    with open("research_results.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print("\nFull results saved to: research_results.json")

if __name__ == "__main__":
    main()
