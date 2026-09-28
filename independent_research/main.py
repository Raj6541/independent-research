import json
from datetime import datetime
from researcher import research

def save_results(question, results):
    data = {
        "question": question,
        "timestamp": datetime.now().isoformat(),
        "results": results
    }

    with open("research_results.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def display_results(results):
    print("\n")
    print("=" * 80)
    print("RESEARCH RESULTS")
    print("=" * 80)

    if not results:
        print("\nNo results found.")
        return

    for index, result in enumerate(results, start=1):
        print(f"\n[{index}] {result['title']}")
        print(f"Domain : {result['domain']}")
        print(f"Score  : {result['score']}")
        print(f"URL    : {result['url']}")

        if result["snippet"]:
            print(f"Info   : {result['snippet']}")

        print("-" * 80)

def main():
    print("=" * 80)
    print("INDEPENDENT RESEARCH ENGINE V0.1")
    print("No LLM | No AI API | Python + Web")
    print("=" * 80)

    question = input("\nEnter your question: ").strip()

    if not question:
        print("Question cannot be empty.")
        return

    results = research(question)
    display_results(results)
    save_results(question, results)

    print("\nResearch saved to:")
    print("research_results.json")

if __name__ == "__main__":
    main()
