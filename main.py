import json
from datetime import datetime
from researcher import research

def main():
    print("="*80)
    print("INDEPENDENT RESEARCH ENGINE V0.3")
    print("Search -> Read -> Extract -> Compare -> Decide -> Re-search")
    print("No LLM | No AI API")
    print("="*80)
    question=input("\nEnter your question: ").strip()
    if not question:
        print("Question cannot be empty.")
        return
    result=research(question)
    print("\n"+"="*80)
    print("ANSWER")
    print("="*80)
    print(result["answer"])
    print(f"\nConfidence: {result['confidence']:.0%}")
    print(f"Question type: {result['question_type']}")
    if result["candidates"]:
        print("\nANSWER CANDIDATES")
        print("-"*80)
        for item in result["candidates"]:
            print(f"- {item['answer']} | support={item['support']} | {item['source']}")
    if result["conflicts"]:
        print("\nCONFLICTS DETECTED")
        for item in result["conflicts"]:
            print(f"- {item['candidate']} | support={item['support']}")
    print("\nTOP SOURCES")
    print("-"*80)
    for i,s in enumerate(result["sources"][:10],1):
        print(f"{i}. {s['title']}")
        print(f"   {s['url']} | score={s['score']}")
    with open("research_results.json","w",encoding="utf-8") as f:
        json.dump({"question":question,"timestamp":datetime.now().isoformat(),**result},f,ensure_ascii=False,indent=2)
    print("\nSaved: research_results.json")

if __name__=="__main__":
    main()
