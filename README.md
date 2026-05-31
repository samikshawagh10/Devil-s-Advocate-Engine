# ⚔️ Devil's Advocate Engine

5 adversarial AI agents tear apart your plan and score its survivability across 5 dimensions.
Then let you defend yourself — and re-score.

## Agents

| Agent | Role |
|---|---|
| 💰 Financial Assassin | Burns down unit economics, pricing, runway assumptions |
| ⚙️ Execution Skeptic | Attacks timelines, skill gaps, technical complexity |
| ⚖️ Ethics Auditor | Surfaces harms, bias, privacy risks, regulatory landmines |
| 📊 Market Realist | Challenges TAM claims, competition, timing, distribution |
| 👤 Adoption Pessimist | Questions behavior change, onboarding friction, churn |

## Setup
```bash
# 1. Clone / download this folder
cd devils_advocate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 4. Run the app
streamlit run app.py
```

## How it works

1. You paste a plan (startup idea, product spec, business proposal)
2. 5 agents run **concurrently** via `asyncio.gather()` — no waiting for one to finish before the next
3. Each agent returns a structured JSON: score (0-100), verdict, top 3 issues, fix, one-liner
4. Aggregated into a Survivability Score with per-dimension bars
5. **Defend yourself** — write a rebuttal, agents re-score acknowledging valid points
6. Before/After tab shows your score delta per dimension

## Key code pattern (async fan-out)

```python
async def run_all_agents(plan, defense=None):
    tasks = [call_agent(agent, plan, defense) for agent in AGENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {agent.id: result for agent, result in zip(AGENTS, results)}

# In Streamlit:
results = asyncio.run(run_all_agents(plan))
```

## Hackathon extensions

- **PDF export** — use `reportlab` to export the full analysis
- **Streamed output** — use `client.messages.stream()` to show agents typing live
- **Web search agent** — add a 6th agent that searches for competitors via web_search tool
- **History** — save past analyses to SQLite, track how plans improve over time
- **Multi-plan battle** — compare two versions of a plan head-to-head

<img width="1417" height="710" alt="Screenshot 2026-05-28 at 19 30 11" src="https://github.com/user-attachments/assets/37ca6869-67e2-48d4-b831-d58dcab782df" />
