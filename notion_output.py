"""
Notion Output
-------------
Creates a new page in a Notion database for each competitive brief,
with the full brief content and scorecard properties mapped to
Notion database columns.

This turns your Notion workspace into a living competitive intelligence
database — every brief is a queryable, filterable record.

Setup:
    1. Go to notion.so/my-integrations → New Integration
    2. Copy the "Internal Integration Secret"
    3. Create a Notion database with these properties:
         - Name (title) — auto-created
         - Threat Level (select): Critical, High, Medium, Low
         - Score (number)
         - Category (select): e.g. "AI", "IAM", "Data"
         - Researched Date (date)
    4. Share the database with your integration (open database → ... → Add connections)
    5. Copy the database ID from the URL:
         notion.so/YOUR-WORKSPACE/<DATABASE_ID>?v=...
    6. Set env vars:
         export NOTION_API_KEY=secret_xxx
         export NOTION_DATABASE_ID=your-database-id

Usage (standalone):
    python outputs/notion_output.py --brief briefs/notion-ai.md --target "Notion AI"

Usage (as a module):
    from outputs.notion_output import send_to_notion
    send_to_notion(scorecard=scorecard, brief_text="...", target="Notion AI")
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from scorer import score_brief, Scorecard

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# ── Markdown → Notion Blocks ──────────────────────────────────────────────────

def markdown_to_notion_blocks(markdown: str) -> list[dict]:
    """
    Converts Markdown to Notion block objects.
    Handles: headings (H1–H3), paragraphs, bullet lists, tables, dividers, bold.
    """
    blocks = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Divider
        if line.strip() in ("---", "***", "___"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})

        # H1
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]},
            })

        # H2
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]},
            })

        # H3
        elif line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}]},
            })

        # Bullet list
        elif line.startswith("- ") or line.startswith("* "):
            text = line[2:].strip()
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
            })

        # Table row (skip — Notion table API is complex; render as code block)
        elif line.startswith("|"):
            # Collect full table
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            table_text = "\n".join(table_lines)
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": table_text}}],
                    "language": "plain text",
                },
            })
            continue

        # Non-empty paragraph
        elif line.strip():
            # Strip markdown bold/italic for plain text safety
            text = line.strip().replace("**", "").replace("*", "").replace("`", "")
            # Truncate to Notion's 2000-char block limit
            if len(text) > 2000:
                text = text[:1997] + "..."
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
            })

        i += 1

    # Notion API max 100 blocks per request — chunk if needed
    return blocks[:100]


# ── Notion API Client ─────────────────────────────────────────────────────────

def notion_request(method: str, endpoint: str, api_key: str, data: dict = None) -> dict:
    """Makes a request to the Notion API."""
    url = f"{NOTION_API_BASE}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


# ── Send Function ─────────────────────────────────────────────────────────────

def send_to_notion(
    scorecard: Scorecard,
    brief_text: str,
    api_key: str = None,
    database_id: str = None,
    category: str = "AI",
    verbose: bool = True,
) -> str | None:
    """
    Creates a new Notion page for the competitive brief.
    Returns the created page URL, or None on failure.
    """
    key = api_key or os.environ.get("NOTION_API_KEY")
    db_id = database_id or os.environ.get("NOTION_DATABASE_ID")

    if not key:
        print("❌ NOTION_API_KEY not set. Export it or pass --api-key.")
        return None
    if not db_id:
        print("❌ NOTION_DATABASE_ID not set. Export it or pass --database-id.")
        return None

    # ── Build page properties ─────────────────────────────────────────────────
    properties = {
        "Name": {
            "title": [{"text": {"content": f"Competitive Brief: {scorecard.target}"}}]
        },
        "Threat Level": {
            "select": {"name": scorecard.overall_threat}
        },
        "Score": {
            "number": scorecard.average_score()
        },
        "Category": {
            "select": {"name": category}
        },
        "Researched Date": {
            "date": {"start": datetime.now().strftime("%Y-%m-%d")}
        },
    }

    # ── Build page content ────────────────────────────────────────────────────
    children = markdown_to_notion_blocks(brief_text)

    # Prepend scorecard block
    scorecard_block = {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": (
                            f"Threat Level: {scorecard.overall_threat}  |  "
                            f"Score: {scorecard.average_score()}/10\n"
                            f"{scorecard.threat_summary}\n"
                            f"Top Risk: {scorecard.top_risk}"
                        )
                    },
                }
            ],
            "icon": {"emoji": "🎯"},
            "color": {
                "Critical": "red_background",
                "High": "orange_background",
                "Medium": "yellow_background",
                "Low": "green_background",
            }.get(scorecard.overall_threat, "default"),
        },
    }
    children = [scorecard_block] + children

    payload = {
        "parent": {"database_id": db_id},
        "properties": properties,
        "children": children,
    }

    try:
        page = notion_request("POST", "pages", api_key=key, data=payload)
        page_url = page.get("url", "")

        if verbose:
            print(f"✅ Created Notion page: {scorecard.target}")
            if page_url:
                print(f"   {page_url}")

        return page_url

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"❌ Notion API error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"❌ Failed to create Notion page: {e}")
        return None


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Push a competitive brief to a Notion database"
    )
    parser.add_argument("--brief", required=True, help="Path to brief .md file")
    parser.add_argument("--target", default=None, help="Override target name")
    parser.add_argument("--category", default="AI", help="Category tag (default: AI)")
    parser.add_argument("--api-key", default=None, help="Notion API key (overrides env var)")
    parser.add_argument("--database-id", default=None, help="Notion database ID (overrides env var)")
    args = parser.parse_args()

    brief_path = Path(args.brief)
    if not brief_path.exists():
        print(f"❌ File not found: {brief_path}")
        sys.exit(1)

    target = args.target or brief_path.stem.replace("-", " ").replace("_", " ").title()
    brief_text = brief_path.read_text(encoding="utf-8")

    scorecard = score_brief(target=target, brief_text=brief_text)

    send_to_notion(
        scorecard=scorecard,
        brief_text=brief_text,
        api_key=args.api_key,
        database_id=args.database_id,
        category=args.category,
    )


if __name__ == "__main__":
    main()
