# 🤖 PM Research Agent

> An agentic AI workflow that autonomously researches a company or product and generates a structured competitive brief — the kind a PM would spend 3–4 hours assembling manually, done in under 2 minutes.

---

## Why I built this

Competitive research is one of the highest-leverage activities a PM can do — and one of the most time-consuming to do well. A proper competitive brief requires:

- Tracking down recent pricing changes
- Reading through product announcements and release notes
- Synthesizing customer reviews and analyst takes
- Framing it all in terms of *strategic implications*, not just feature lists

I built this agent to automate the research and synthesis layer, so I can spend my time on the part that actually requires product judgment: deciding what it *means* for roadmap, positioning, and customer conversations.

This is also a working prototype of a broader pattern I care about: **agentic workflows that augment PM decision-making**, not just generate text.

---

## How it works

The agent runs an autonomous multi-step research loop using Claude + web search:

```
User Input (target company/product)
        │
        ▼
┌─────────────────────────────────┐
│        Research Agent Loop      │
│                                 │
│  1. Decide what to search for   │
│  2. Run web search              │
│  3. Evaluate results            │
│  4. Decide: search more or stop │
│  5. Repeat up to 10x            │
└─────────────────────────────────┘
        │
        ▼
Structured Competitive Brief (Markdown)
```

The key design decision: **the agent decides its own search strategy**. It doesn't follow a fixed script — it reads intermediate results and determines what gaps remain before synthesizing. This is the difference between a pipeline and an agent.

---

## Output structure

Every brief covers:

1. Company / Product Overview
2. Core Value Proposition
3. Target Customer & ICP
4. Key Features & Differentiators
5. Pricing & Packaging
6. Competitive Landscape
7. Recent Moves (last 6–12 months)
8. Strengths & Weaknesses
9. Strategic Implications for a competing PM

See a full example: [`sample_output/notion-ai-brief.md`](sample_output/notion-ai-brief.md)

---

## Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/dvmukul/pm-research-agent.git
cd pm-research-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY=your_key_here
```

Get a key at [console.anthropic.com](https://console.anthropic.com)

### 4. Run the agent

```bash
# Print brief to terminal
python agent.py --target "Salesforce Einstein"

# Save to a markdown file
python agent.py --target "Intercom Fin AI" --output brief.md

# Quiet mode (no progress output)
python agent.py --target "HubSpot AI" --quiet
```

---

## Example output

```
🔍 PM Research Agent starting...

   Target: Notion AI
   Model:  claude-opus-4-5
   Max searches: 10

────────────────────────────────────────────────────────────
  🌐 Search [1]: Notion AI features pricing 2025
  🌐 Search [2]: Notion AI vs Microsoft Copilot competitive comparison
  🌐 Search [3]: Notion AI enterprise announcements 2024 2025
  🌐 Search [4]: Notion Mail product launch
  🌐 Search [5]: Notion customer reviews G2 Capterra weaknesses
────────────────────────────────────────────────────────────
✅ Research complete (5 iterations)

# Competitive Brief: Notion AI
...
```

---

## Design decisions worth noting

**Why Claude?** Claude's extended context window and strong instruction-following made it the right choice for a task that requires reading multiple search results and synthesizing them coherently — not just summarizing the top result.

**Why agentic (not a fixed pipeline)?** Fixed pipelines break when the target is unusual or when the first search returns stale results. The agent adapts — if it can't find pricing, it searches differently. If a product was acquired recently, it notices and adjusts the framing.

**Why Markdown output?** Briefs need to be shareable. Markdown renders cleanly in Notion, Confluence, GitHub, and Linear — everywhere a PM actually works.

---

## What's next

- [ ] Batch mode — research a list of competitors in one run
- [ ] Diff mode — compare two briefs to surface what changed over time
- [ ] Slack/Notion output — push the brief directly to a workspace
- [ ] Scoring layer — auto-rate competitor threat level based on brief content

---

## About

Built by [Mukul Dewangan](https://www.linkedin.com/in/mukuldewangan/) — Senior PM specializing in AI and data products. This repo is part of a broader exploration of how agentic AI can augment product management workflows.

If you're building in this space, let's connect.
