def build_answer(question, reasoning):
    if not reasoning["answer"]:
        return "I could not establish a sufficiently supported answer."

    answer = reasoning["answer"]
    text = f"Answer: {answer}\n\nConfidence: {reasoning['confidence']:.0%}"

    if reasoning["conflicts"]:
        text += "\n\nPossible conflicting evidence was detected. The answer above has the strongest combined source support."

    text += "\n\nSupporting evidence:"
    for ev in reasoning["evidence"][:5]:
        text += f"\n- {ev.value} | {', '.join(ev.domains)}"

    return text
