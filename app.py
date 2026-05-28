import streamlit as st
import asyncio
import anthropic
import json
import re
from dataclasses import dataclass

# ── Config ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Devil's Advocate Engine",
    page_icon="⚔️",
    layout="centered",
)

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# ── Agent definitions ────────────────────────────────────────────────────────

@dataclass
class Agent:
    id: str
    name: str
    emoji: str
    color: str
    system_prompt: str

AGENTS = [
    Agent(
        id="financial",
        name="Financial Assassin",
        emoji="💰",
        color="#E24B4A",
        system_prompt="""You are a brutal CFO and financial analyst who has seen hundreds of business plans fail.
Your job: find every financial flaw, unrealistic assumption, and funding gap.
Be specific, merciless, and concrete. No vague criticisms.

Respond ONLY with valid JSON. No markdown fences, no preamble:
{
  "score": <integer 0-100>,
  "verdict": "<Catastrophic|Critical|Fragile|Borderline|Viable|Strong>",
  "top_issues": ["<issue 1>", "<issue 2>", "<issue 3>"],
  "fix": "<one concrete, actionable fix>",
  "one_liner": "<devastating one-sentence financial risk summary>"
}""",
    ),
    Agent(
        id="execution",
        name="Execution Skeptic",
        emoji="⚙️",
        color="#BA7517",
        system_prompt="""You are a senior engineering manager who has watched 100 projects die in execution.
Your job: attack timelines, team skill gaps, technical complexity, third-party dependencies, and operational blind spots.
You know great ideas die in implementation.

Respond ONLY with valid JSON. No markdown fences, no preamble:
{
  "score": <integer 0-100>,
  "verdict": "<Catastrophic|Critical|Fragile|Borderline|Viable|Strong>",
  "top_issues": ["<issue 1>", "<issue 2>", "<issue 3>"],
  "fix": "<one concrete, actionable fix>",
  "one_liner": "<devastating one-sentence execution risk>"
}""",
    ),
    Agent(
        id="ethics",
        name="Ethics Auditor",
        emoji="⚖️",
        color="#3B6D11",
        system_prompt="""You are an AI ethics researcher and regulatory compliance expert.
Your job: surface harms, bias risks, privacy violations, regulatory landmines, and ethical blind spots.
Be specific about which laws, regulations, or principles are at risk.

Respond ONLY with valid JSON. No markdown fences, no preamble:
{
  "score": <integer 0-100>,
  "verdict": "<Catastrophic|Critical|Fragile|Borderline|Viable|Strong>",
  "top_issues": ["<issue 1>", "<issue 2>", "<issue 3>"],
  "fix": "<one concrete, actionable fix>",
  "one_liner": "<one-sentence primary ethical or regulatory concern>"
}""",
    ),
    Agent(
        id="market",
        name="Market Realist",
        emoji="📊",
        color="#185FA5",
        system_prompt="""You are a VC partner who has passed on 1000 pitches and watched many fail post-investment.
Your job: challenge TAM/SAM claims, competitive density, timing assumptions, and go-to-market distribution.
Be specific about which competitors exist and why distribution is harder than claimed.

Respond ONLY with valid JSON. No markdown fences, no preamble:
{
  "score": <integer 0-100>,
  "verdict": "<Catastrophic|Critical|Fragile|Borderline|Viable|Strong>",
  "top_issues": ["<issue 1>", "<issue 2>", "<issue 3>"],
  "fix": "<one concrete, actionable fix>",
  "one_liner": "<VC rejection one-liner>"
}""",
    ),
    Agent(
        id="adoption",
        name="Adoption Pessimist",
        emoji="👤",
        color="#534AB7",
        system_prompt="""You are a product manager who has shipped 10 failed products and studied why people don't change behavior.
Your job: attack onboarding friction, behavior change resistance, churn prediction, network effects (or lack thereof).
Focus on the gap between "people say they want this" and "people actually use this daily."

Respond ONLY with valid JSON. No markdown fences, no preamble:
{
  "score": <integer 0-100>,
  "verdict": "<Catastrophic|Critical|Fragile|Borderline|Viable|Strong>",
  "top_issues": ["<issue 1>", "<issue 2>", "<issue 3>"],
  "fix": "<one concrete, actionable fix>",
  "one_liner": "<one-sentence reason users won't stick around>"
}""",
    ),
]

EXAMPLE_PLAN = """Product: AI-powered meal planning app that generates weekly meal plans and auto-orders groceries via Instacart.

Target market: Busy professionals aged 25-40 in the US.
Revenue model: $15/month subscription. Goal: 100k paying users in year 1.
Team: 2 founders — one designer, one marketer. No engineers on team yet.
Tech stack: GPT API + Instacart API + Bubble.io (no-code builder).
Funding: Pre-revenue. Planning to raise $500k seed after launch in 3 months.
Differentiation: More personalized than competitors via AI."""

# ── Helpers ──────────────────────────────────────────────────────────────────

def score_color(score: int) -> str:
    if score >= 70:
        return "green"
    elif score >= 50:
        return "orange"
    return "red"

def verdict_color(verdict: str) -> str:
    colors = {
        "Strong": "🟢", "Viable": "🔵",
        "Borderline": "🟡", "Fragile": "🟠",
        "Critical": "🔴", "Catastrophic": "💀",
    }
    return colors.get(verdict, "⚪")

def overall_score(results: dict) -> int | None:
    scores = [v["score"] for v in results.values() if "score" in v]
    return round(sum(scores) / len(scores)) if len(scores) == len(AGENTS) else None

def parse_agent_response(text: str) -> dict:
    """Strip markdown fences and parse JSON safely."""
    clean = re.sub(r"```json|```", "", text).strip()
    return json.loads(clean)

# ── Async agent caller ────────────────────────────────────────────────────────

async def call_agent(agent: Agent, plan: str, defense: str | None = None) -> dict:
    client = anthropic.AsyncAnthropic()

    user_content = (
        f"Original plan:\n{plan}\n\nUser's defense:\n{defense}\n\n"
        "Re-evaluate honestly. Acknowledge valid points but remain rigorous. Update your score accordingly."
        if defense
        else f"Analyze this plan:\n\n{plan}"
    )

    message = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1000,
        system=agent.system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text
    return parse_agent_response(raw)

async def run_all_agents(plan: str, defense: str | None = None) -> dict:
    """Fan out all 5 agents concurrently."""
    tasks = [call_agent(agent, plan, defense) for agent in AGENTS]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    results = {}
    for agent, result in zip(AGENTS, results_list):
        if isinstance(result, Exception):
            results[agent.id] = {
                "score": 50,
                "verdict": "Error",
                "top_issues": [f"Analysis failed: {str(result)}"],
                "fix": "Check your API key and retry.",
                "one_liner": "Could not analyze this dimension.",
            }
        else:
            results[agent.id] = result
    return results

# ── UI ────────────────────────────────────────────────────────────────────────

# CSS
st.markdown("""
<style>
.score-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 24px;
}
.agent-card {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.verdict-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
}
.issue-item {
    padding: 6px 0;
    font-size: 14px;
    border-bottom: 1px solid #f0f0f0;
}
</style>
""", unsafe_allow_html=True)


def render_score_panel(results: dict, title: str = "Survivability Score"):
    """Render the overview score panel."""
    score = overall_score(results)
    if score is None:
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        color = score_color(score)
        st.metric(label=title, value=f"{score}/100")

    with col2:
        for agent in AGENTS:
            r = results.get(agent.id, {})
            s = r.get("score", 0)
            st.markdown(f"**{agent.emoji} {agent.name}**")
            st.progress(s / 100, text=f"{s}/100")


def render_agent_card(agent: Agent, result: dict, prev_result: dict | None = None):
    """Render one agent's collapsible result card."""
    score = result.get("score", 0)
    verdict = result.get("verdict", "—")
    one_liner = result.get("one_liner", "")
    issues = result.get("top_issues", [])
    fix = result.get("fix", "")

    delta_str = ""
    if prev_result and "score" in prev_result:
        delta = score - prev_result["score"]
        if delta > 0:
            delta_str = f" *(+{delta} after defense)*"
        elif delta < 0:
            delta_str = f" *({delta} after defense)*"
        else:
            delta_str = " *(unchanged)*"

    label = f"{agent.emoji} **{agent.name}** — {verdict_color(verdict)} {verdict} — **{score}/100**{delta_str}"

    with st.expander(label, expanded=False):
        st.caption(f"*{one_liner}*")
        st.markdown("**Top issues:**")
        for issue in issues:
            st.markdown(f"- ✕ {issue}")
        st.info(f"**Recommended fix:** {fix}")


def render_results(results: dict, prev_results: dict | None = None, defended: bool = False):
    """Full results view."""
    title = "Re-scored after defense" if defended else "Survivability Score"
    render_score_panel(results, title=title)
    st.divider()
    for agent in AGENTS:
        r = results.get(agent.id)
        if r:
            render_agent_card(agent, r, prev_results.get(agent.id) if prev_results else None)


# ── Session state ─────────────────────────────────────────────────────────────

if "phase" not in st.session_state:
    st.session_state.phase = "input"       # input | results | defended
if "results" not in st.session_state:
    st.session_state.results = {}
if "rescored" not in st.session_state:
    st.session_state.rescored = {}
if "plan" not in st.session_state:
    st.session_state.plan = ""

# ── Page header ───────────────────────────────────────────────────────────────

st.title("⚔️ Devil's Advocate Engine")
st.caption("Paste your plan. 5 adversarial AI agents critique it and score its survivability — then let you defend yourself.")
st.divider()

# ── Input phase ───────────────────────────────────────────────────────────────

if st.session_state.phase == "input":
    if st.button("📋 Load example plan"):
        st.session_state.plan = EXAMPLE_PLAN

    plan = st.text_area(
        "Your plan",
        value=st.session_state.plan,
        height=200,
        placeholder="Describe your startup idea, product plan, business proposal, or project...",
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        run = st.button("⚔️ Destroy my plan", type="primary", use_container_width=True)
    with col2:
        st.caption("Runs 5 agents concurrently via async API calls")

    if run and plan.strip():
        st.session_state.plan = plan
        with st.spinner("5 adversarial agents are reviewing your plan..."):
            results = asyncio.run(run_all_agents(plan))
        st.session_state.results = results
        st.session_state.phase = "results"
        st.rerun()

    elif run and not plan.strip():
        st.warning("Please enter a plan first.")

# ── Results phase ─────────────────────────────────────────────────────────────

elif st.session_state.phase == "results":
    render_results(st.session_state.results)

    st.divider()
    st.subheader("🛡️ Defend your plan")
    st.caption("Address the critiques. Agents will re-score based on your response.")

    defense = st.text_area(
        "Your defense",
        height=130,
        placeholder="We already have 3 signed LOIs from enterprise clients... Our CTO has 10 years of experience in this exact infrastructure space...",
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        defend = st.button("Submit defense ↗", type="primary", use_container_width=True)
    with col2:
        if st.button("Start over", use_container_width=True):
            st.session_state.phase = "input"
            st.session_state.results = {}
            st.session_state.rescored = {}
            st.session_state.plan = ""
            st.rerun()

    if defend and defense.strip():
        with st.spinner("Agents are reviewing your defense..."):
            rescored = asyncio.run(run_all_agents(st.session_state.plan, defense))
        st.session_state.rescored = rescored
        st.session_state.phase = "defended"
        st.rerun()

    elif defend and not defense.strip():
        st.warning("Write your defense first.")

# ── Defended phase ────────────────────────────────────────────────────────────

elif st.session_state.phase == "defended":
    tab1, tab2 = st.tabs(["📈 After defense", "📉 Before defense"])

    with tab1:
        render_results(
            st.session_state.rescored,
            prev_results=st.session_state.results,
            defended=True,
        )

    with tab2:
        render_results(st.session_state.results)

    st.divider()
    if st.button("⚔️ Analyze a new plan", type="primary", use_container_width=True):
        st.session_state.phase = "input"
        st.session_state.results = {}
        st.session_state.rescored = {}
        st.session_state.plan = ""
        st.rerun()
