"""
Scorer
------
Takes a competitive brief and scores the competitor across five
strategic dimensions, then outputs a structured threat scorecard.

This is the evaluation layer — the part that turns a research brief
into a decision-making signal for a PM.

Usage (standalone):
    python scorer.py --brief briefs/notion-ai.md
    python scorer.py --brief briefs/notion-ai.md --json

Usage (as a module):
    from scorer import score_brief
    scorecard = score_brief(target="Notion AI", brief_text="...")
"""

import anthropic
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

THREAT_LEVELS = ["Critical", "High", "Medium", "Low"]

# ── Scoring Dimensions ────────────────────────────────────────────────────────
#
# These five dimensions were chosen deliberately:
# - They map to the questions a PM actually asks in a competitive review
# - They're specific enough to score from a brief, not vague enough to game
# - Together they produce a threat profile, not just a threat score

SCORING_DIMENSIONS = {
    "market_overlap": {
        "label": "Market Overlap",
        "description": "How much do they compete for the same customers, use cases, and budget?",
        "why": "High overlap = direct threat to win rates and retention",
    },
    "ai_maturity": {
        "label": "AI Maturity",
        "description": "How deeply is AI integrated into their core product, not just bolted on?",
        "why": "AI-native competitors compound advantages faster than traditional ones",
    },
    "execution_velocity": {
        "label": "Execution Velocity",
        "description": "How fast are they shipping? Frequency of meaningful product updates?",
        "why": "A slow competitor with great positioning is less dangerous than a fast one",
    },
    "distribution_strength": {
        "label": "Distribution Strength",
        "description": "How strong is their go-to-market: brand, channels, partnerships, contracts?",
        "why": "Distribution moats outlast product moats in B2B SaaS",
    },
    "resource_depth": {
        "label": "Resource Depth",
        "description": "Funding, headcount, enterprise contracts — how long can they sustain a fight?",
        "why": "Determines their capacity to out-invest and out-wait you",
    },
}

# ── Scoring Prompt ────────────────────────────────────────────────────────────

SCORER_SYSTEM = """You are a strategic product intelligence analyst. Your job is to read a competitive brief 
and score the competitor across five dimensions from the perspective of a Senior PM at a competing B2B SaaS company.

Scoring rules:
- Score each dimension 1–10 (1 = negligible threat, 10 = existential threat)
- Be calibrated: a score of 8+ should be rare and justified
- Base scores strictly on evidence in the brief — do not invent information
- If the brief lacks evidence for a dimension, score it 5 and flag it as "inferred"

You must respond with ONLY valid JSON in exactly this structure — no preamble, no markdown, no explanation:
{
  "target": "<product name>",
  "scores": {
    "market_overlap": { "score": <1-10>, "rationale": "<1-2 sentences>", "inferred": <true|false> },
    "ai_maturity": { "score": <1-10>, "rationale": "<1-2 sentences>", "inferred": <true|false> },
    "execution_velocity": { "score": <1-10>, "rationale": "<1-2 sentences>", "inferred": <true|false> },
    "distribution_strength": { "score": <1-10>, "rationale": "<1-2 sentences>", "inferred": <true|false> },
    "resource_depth": { "score": <1-10>, "rationale": "<1-2 sentences>", "inferred": <true|false> }
  },
  "overall_threat": "<Critical|High|Medium|Low>",
  "threat_summary": "<2-3 sentence strategic summary a PM would read first>",
  "top_risk": "<The single most important thing to watch>",
  "blind_spots": "<What this brief likely missed or underweighted>"
}"""


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    score: int
    rationale: str
    inferred: bool


@dataclass
class Scorecard:
    target: str
    scores: dict[str, DimensionScore]
    overall_threat: str
    threat_summary: str
    top_risk: str
    blind_spots: str

    def average_score(self) -> float:
        return round(sum(d.score for d in self.scores.values()) / len(self.scores), 1)

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "overall_threat": self.overall_threat,
            "average_score": self.average_score(),
            "scores": {
                k: {"score": v.score, "rationale": v.rationale, "inferred": v.inferred}
                for k, v in self.scores.items()
            },
            "threat_summary": self.threat_summary,
            "top_risk": self.top_risk,
            "blind_spots": self.blind_spots,
        }

    def to_markdown(self) -> str:
        """Renders the scorecard as a clean Markdown block for embedding in briefs."""

        threat_emoji = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🟢",
        }.get(self.overall_threat, "⚪")

        score_bar = lambda s: "█" * s + "░" * (10 - s)

        lines = [
            f"## Threat Scorecard: {self.target}",
            "",
            f"**Overall Threat Level:** {threat_emoji} {self.overall_threat}  ",
            f"**Composite Score:** {self.average_score()} / 10",
            "",
            "---",
            "",
            "### Dimension Scores",
            "",
            "| Dimension | Score | Visual | Rationale |",
            "|---|---|---|---|",
        ]

        for key, dim in self.scores.items():
            meta = SCORING_DIMENSIONS[key]
            inferred_flag = " *(inferred)*" if dim.inferred else ""
            lines.append(
                f"| **{meta['label']}** | {dim.score}/10 | `{score_bar(dim.score)}` "
                f"| {dim.rationale}{inferred_flag} |"
            )

        lines += [
            "",
            "---",
            "",
            "### Strategic Read",
            "",
            f"**Summary:** {self.threat_summary}",
            "",
            f"**Top risk to watch:** {self.top_risk}",
            "",
            f"**Likely blind spots in this brief:** {self.blind_spots}",
        ]

        return "\n".join(lines)


# ── Core Scoring Function ─────────────────────────────────────────────────────

def score_brief(target: str, brief_text: str, verbose: bool = True) -> Scorecard:
    """
    Scores a competitive brief across five strategic dimensions.
    Returns a structured Scorecard object.
    """
    client = anthropic.Anthropic()

    if verbose:
        print(f"\n🎯 Scoring threat level for: {target}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SCORER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Target: {target}\n\n"
                    f"Brief:\n\n{brief_text}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if model wraps in them despite instructions
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])

    data = json.loads(raw)

    scores = {
        key: DimensionScore(
            score=data["scores"][key]["score"],
            rationale=data["scores"][key]["rationale"],
            inferred=data["scores"][key].get("inferred", False),
        )
        for key in SCORING_DIMENSIONS
    }

    scorecard = Scorecard(
        target=data["target"],
        scores=scores,
        overall_threat=data["overall_threat"],
        threat_summary=data["threat_summary"],
        top_risk=data["top_risk"],
        blind_spots=data["blind_spots"],
    )

    if verbose:
        threat_emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(
            scorecard.overall_threat, "⚪"
        )
        print(f"   {threat_emoji} {scorecard.overall_threat} threat  |  Composite: {scorecard.average_score()}/10\n")

    return scorecard


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Score a competitive brief for threat level and strategic dimensions"
    )
    parser.add_argument("--brief", required=True, help="Path to a brief .md file")
    parser.add_argument("--target", default=None, help="Override target name (inferred from filename if omitted)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON instead of Markdown")
    args = parser.parse_args()

    brief_path = Path(args.brief)
    if not brief_path.exists():
        print(f"❌ File not found: {brief_path}")
        sys.exit(1)

    brief_text = brief_path.read_text(encoding="utf-8")
    target = args.target or brief_path.stem.replace("-", " ").replace("_", " ").title()

    try:
        scorecard = score_brief(target=target, brief_text=brief_text)
    except anthropic.AuthenticationError:
        print("\n❌ Error: ANTHROPIC_API_KEY is missing or invalid.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n❌ Failed to parse scorer response as JSON: {e}")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(scorecard.to_dict(), indent=2))
    else:
        print(scorecard.to_markdown())


if __name__ == "__main__":
    main()
