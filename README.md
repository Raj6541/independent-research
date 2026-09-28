# Independent Research Engine v1.0

Advanced single-file, rule-based web research engine.

## No LLM
This project does not use an LLM or AI API. It uses Python, web search,
HTML parsing, deterministic scoring, evidence comparison and heuristics.

## Features
- Multi-query planning
- Web search
- Webpage fetching
- HTML cleanup
- Evidence extraction
- Source authority scoring
- Relevance scoring
- Cross-source comparison
- Basic contradiction detection
- Confidence estimation
- Autonomous multi-round research
- JSON report output

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Or:

```bash
python main.py "What is the highest mountain in Rajasthan?"
```

Advanced:

```bash
python main.py "Your question" --rounds 4 --max-pages 25 --threshold 0.65
```

## Important
Scores are heuristics, not proof. Contradiction detection is deliberately
conservative and can miss nuanced disagreements. Websites may block automated
requests or change their HTML. Respect site terms, robots policies, rate
limits and copyright.
