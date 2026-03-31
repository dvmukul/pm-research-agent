"""
PM Research Agent
-----------------
An agentic workflow that autonomously researches a company or product
and generates a structured competitive brief — the kind a PM would
spend 3–4 hours assembling manually.

Usage:
    python agent.py --target "Notion AI"
    python agent.py --target "Salesforce Einstein" --output brief.md
"""

import anthropic
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

MODEL = "claude-opus-4-5"
MAX_TOKENS = 4096

BRIEF_SECTIONS = [
    "Company / Product Overview",
    "Core Value Proposition",
    "Target Customer & ICP",
    "Key Features & Differentiators",
    "Pricing & Packaging",
    "Competitive Landscape",
    "Recent Moves (last 6–12 months)",
    "Strengths & Weaknesses",
    "Strategic Implications for a competing PM",
]

# ── Agent System Prompt ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert product intelligence analyst with 10+ years of B2B SaaS experience.

Your job is to autonomously research a company or product and produce a structured competitive brief 
that a Senior Product Manager would use to inform strategy, roadmap decisions, and positioning.

You have access to a web search tool. Use it aggressively and intelligently:
- Run multiple targeted searches to triangulate information
- Search for recent news, pricing pages, product announcements, customer reviews, and analyst coverage
- Don't stop at the first result — dig deeper if something is unclear or potentially outdated
- Think like a PM: what would actually matter for a competitive review?

Your output must be a clean, structured Markdown brief covering these sections:
{sections}

Be specific. Use real numbers, dates, and named features where available. 
Flag anything that is inferred or uncertain with "(unconfirmed)".
A vague brief is useless to a PM — precision is the standard.
""".format(sections="\n".join(f"{i+1}. {s}" for i, s in enumerate(BRIEF_SECTIONS)))

# ── Agent Loop ────────────────────────────────────────────────────────────────

def run_research_agent(target: str, verbose: bool = True) -> str:
    """
    Runs the agentic research loop with web search tool use.
    The agent autonomously decides what to search and when to stop.
    """
    client = anthropic.Anthropic()

    tools = [
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 10,  # Agent can run up to 10 searches autonomously
        }
    ]

    messages = [
        {
            "role": "user",
            "content": (
                f"Research target: **{target}**\n\n"
                f"Today's date: {datetime.now().strftime('%B %d, %Y')}\n\n"
                "Run as many searches as you need to build a complete picture. "
                "Then produce the full competitive brief in Markdown format."
            ),
        }
    ]

    if verbose:
        print(f"\n🔍 PM Research Agent starting...\n")
        print(f"   Target: {target}")
        print(f"   Model:  {MODEL}")
        print(f"   Max searches: 10\n")
        print("─" * 60)

    iteration = 0

    # Agentic loop — keeps running until the model stops using tools
    while True:
        iteration += 1

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Show what the agent is doing in real time
        if verbose:
            for block in response.content:
                if block.type == "tool_use" and block.name == "web_search":
                    query = block.input.get("query", "")
                    print(f"  🌐 Search [{iteration}]: {query}")

        # Check stop condition
        if response.stop_reason == "end_turn":
            if verbose:
                print("\n─" * 60)
                print(f"✅ Research complete ({iteration} iteration(s))\n")
            break

        if response.stop_reason == "tool_use":
            # Append assistant's response (with tool calls) to history
            messages.append({"role": "assistant", "content": response.content})

            # Build tool results
            tool_results = []
            for block in response.content:
                if block.type == "tool_result":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                    })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            continue

        # Fallback: unexpected stop reason
        break

    # Extract the final text output
    brief = ""
    for block in response.content:
        if hasattr(block, "text"):
            brief += block.text

    return brief


# ── Output Formatting ─────────────────────────────────────────────────────────

def format_brief(target: str, brief: str) -> str:
    """Wraps the brief with a header and metadata block."""
    header = f"""# Competitive Brief: {target}

> **Generated by PM Research Agent** | {datetime.now().strftime("%B %d, %Y")}  
> *Autonomous research using Claude + web search. Flag unconfirmed items before sharing.*

---

"""
    return header + brief


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PM Research Agent — autonomously generate competitive briefs"
    )
    parser.add_argument(
        "--target",
        required=True,
        help='Company or product to research (e.g. "Notion AI", "Salesforce Einstein")',
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional: save brief to a markdown file (e.g. brief.md)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output, print only the final brief",
    )
    args = parser.parse_args()

    try:
        raw_brief = run_research_agent(
            target=args.target,
            verbose=not args.quiet,
        )
    except anthropic.AuthenticationError:
        print("\n❌ Error: ANTHROPIC_API_KEY is missing or invalid.")
        print("   Set it with: export ANTHROPIC_API_KEY=your_key_here\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        sys.exit(1)

    final_brief = format_brief(args.target, raw_brief)

    # Always print to stdout
    print(final_brief)

    # Optionally save to file
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(final_brief, encoding="utf-8")
        print(f"\n💾 Brief saved to: {output_path.resolve()}\n")


if __name__ == "__main__":
    main()
