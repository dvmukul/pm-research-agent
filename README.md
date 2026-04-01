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

## What's in this repo

| Module | What it does |
|---|---|
| `agent.py` | Core research agent — autonomously searches and generates a competitive brief |
| `scorer.py` | Scores a brief across 5 strategic dimensions and outputs a threat level |
| `batch.py` | Researches and scores multiple competitors in one run, outputs a ranked landscape |
| `diff.py` | Compares two briefs over time, surfaces strategic changes and threat trajectory |
| `outputs/slack_output.py` | Pushes briefs and scorecards to a Slack channel via webhook |
| `outputs/notion_output.py` | Creates a Notion database page for each brief with scorecard properties |

---

## How it works

### 1. Research Agent (`agent.py`)

Runs an autonomous multi-step research loop using Claude + web search:

```
User Input (target company/product)
        │
        ▼
┌─────────────────────────────────┐
│        Research Agent Loop      │
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

The agent decides its own search strategy. It doesn't follow a fixed script — it reads intermediate results and determines what gaps remain before synthesizing.

### 2. Scoring Layer (`scorer.py`)

Takes a brief and scores the competitor across five strategic dimensions:

| Dimension | What it measures |
|---|---|
| **Market Overlap** | How directly do they compete for the same customers and budget? |
| **AI Maturity** | How deeply is AI integrated — native or bolted on? |
| **Execution Velocity** | How fast are they shipping meaningful product changes? |
| **Distribution Strength** | Brand, channels, partnerships, existing contracts |
| **Resource Depth** | Funding, headcount — how long can they sustain a fight? |

Output: a composite score (1–10) + overall threat level: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low

### 3. Batch Mode (`batch.py`)

Research and score an entire competitive landscape in one command. Outputs:
- Individual brief files per competitor
- `landscape.md` — a ranked summary table sorted by threat level

### 4. Diff Mode (`diff.py`)

Compare two briefs for the same competitor across time. Surfaces:
- Threat trajectory (↑ Escalating / → Stable / ↓ De-escalating)
- New features and strategic moves
- ICP drift — are they moving toward your customers?
- AI maturity delta
- Strategic implications for a competing PM

### 5. Outputs (Slack + Notion)

Push briefs and scorecards directly to your workspace:
- **Slack:** Formatted Block Kit message to any channel via webhook
- **Notion:** New database page with scorecard properties, filterable by threat level

---

## Quickstart

### Install

```bash
git clone https://github.com/dvmukul/pm-research-agent.git
cd pm-research-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

### Research a single competitor

```bash
python agent.py --target "Salesforce Einstein"
python agent.py --target "Intercom Fin AI" --output briefs/intercom.md
```

### Score a brief

```bash
python scorer.py --brief briefs/intercom.md
python scorer.py --brief briefs/intercom.md --json   # structured JSON output
```

### Research + score in one step

```bash
python agent.py --target "Notion AI" --output briefs/notion.md && \
python scorer.py --brief briefs/notion.md
```

### Run a full competitive landscape

```bash
# Comma-separated
python batch.py --targets "Notion AI, Coda, Confluence AI, ClickUp AI" --output-dir briefs/

# From a file
python batch.py --targets-file competitors.txt --output-dir briefs/ --context "Q2 2025 review"
```

### Diff two briefs over time

```bash
python diff.py --before briefs/notion-jan.md --after briefs/notion-apr.md --target "Notion AI"
python diff.py --before briefs/notion-jan.md --after briefs/notion-apr.md --output diffs/notion-delta.md
```

### Push to Slack

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
python outputs/slack_output.py --brief briefs/notion.md --target "Notion AI"
python outputs/slack_output.py --brief briefs/notion.md --dry-run   # preview without sending
```

### Push to Notion

```bash
export NOTION_API_KEY=secret_xxx
export NOTION_DATABASE_ID=your-database-id
python outputs/notion_output.py --brief briefs/notion.md --target "Notion AI" --category "AI"
```

---

## Example outputs

### Terminal output (batch run)
```
📋 Batch run: 3 competitor(s)
   Targets: Notion AI, Coda, Confluence AI
   Output:  briefs/

════════════════════════════════════════════════════════════
  [1/3] Notion AI
════════════════════════════════════════════════════════════
  🌐 Search [1]: Notion AI features pricing 2025
  🌐 Search [2]: Notion AI vs Microsoft Copilot
  🌐 Search [3]: Notion enterprise announcements 2025
  🎯 Scoring threat level for: Notion AI
     🟠 High threat  |  Composite: 7.4/10

════════════════════════════════════════════════════════════
  [2/3] Coda
...

✅ Batch complete
   3 brief(s) saved to briefs/
   Landscape summary: briefs/landscape.md
```

### Scorecard output
```
## Threat Scorecard: Notion AI

**Overall Threat Level:** 🟠 High
**Composite Score:** 7.4 / 10

| Dimension          | Score  | Visual       | Rationale                                          |
|--------------------|--------|--------------|----------------------------------------------------|
| Market Overlap     | 8/10   | ████████░░   | Direct overlap on knowledge management and docs    |
| AI Maturity        | 7/10   | ███████░░░   | Native AI on structured data is a real moat        |
| Execution Velocity | 8/10   | ████████░░   | Notion Mail + Calendar in one quarter signals pace |
| Distribution       | 7/10   | ███████░░░   | Strong SMB brand but enterprise flank exposed      |
| Resource Depth     | 7/10   | ███████░░░   | $10B valuation, well-capitalized                   |
```

Full example brief: [`sample_output/notion-ai-brief.md`](sample_output/notion-ai-brief.md)

---

## Design decisions worth noting

**Why Claude?** Claude's extended context window and strong instruction-following made it the right choice for a task that requires reading multiple search results and synthesizing them coherently — not just summarizing the top result.

**Why agentic (not a fixed pipeline)?** Fixed pipelines break when the target is unusual or when the first search returns stale results. The agent adapts — if it can't find pricing, it searches differently. If a product was acquired recently, it notices and adjusts the framing.

**Why five scoring dimensions?** They were chosen to map directly to the questions a PM asks in a real competitive review — not generic "strengths/weaknesses." Each dimension is specific enough to score from a brief, and together they produce a threat *profile*, not just a threat number.

**Why a diff mode?** A one-time brief is a snapshot. What matters to a PM is *momentum* — is this competitor accelerating or stalling? The diff mode is what turns this from a research tool into an ongoing intelligence system.

**Why Markdown output?** Briefs need to be shareable. Markdown renders cleanly in Notion, Confluence, GitHub, and Linear — everywhere a PM actually works.

---

## About

Built by [Mukul Dewangan](https://www.linkedin.com/in/mukuldewangan/) — Senior PM specializing in AI and data products. This repo is part of a broader exploration of how agentic AI can augment product management workflows.

If you're building in this space, let's connect.
