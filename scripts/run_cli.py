"""CLI runner for testing the portfolio analyzer graph interactively."""

import asyncio
import json
import os
import sys
import uuid

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

load_dotenv()

from portfolio_analyzer.graph import build_portfolio_graph


def print_header():
    print("\n" + "=" * 60)
    print("  📊 Portfolio Analyzer — Interactive CLI")
    print("  Type 'quit' to exit, 'load <path>' to load a CSV")
    print("=" * 60 + "\n")


def load_csv_file(path: str) -> str:
    """Load CSV content from a file path."""
    path = path.strip().strip("'\"")
    if not os.path.exists(path):
        print(f"  ❌ File not found: {path}")
        return ""
    with open(path, "r") as f:
        return f.read()


async def run_cli():
    """Run the interactive CLI."""
    print_header()

    graph = build_portfolio_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    portfolio_loaded = False

    while True:
        try:
            user_input = input("\n💬 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\nGoodbye! 👋")
            break

        # Handle CSV loading
        has_csv = False
        if user_input.lower().startswith("load "):
            csv_path = user_input[5:].strip()
            csv_content = load_csv_file(csv_path)
            if not csv_content:
                continue
            user_input = csv_content
            has_csv = True

        # Build input state
        input_state = {
            "messages": [HumanMessage(content=user_input)],
            "has_csv": has_csv,
        }

        print("\n⏳ Analyzing...\n")

        try:
            # Invoke the graph
            result = await graph.ainvoke(input_state, config=config)

            # Print the AI response
            messages = result.get("messages", [])
            if messages:
                last_ai = messages[-1]
                if hasattr(last_ai, "content"):
                    print(f"🤖 Analyst:\n{last_ai.content}")

            # Print dashboard signals (if any)
            signals = result.get("dashboard_signals")
            if signals:
                print(f"\n📊 Dashboard Signals ({len(signals)}):")
                for s in signals:
                    alert = f" [{s.get('alert_level', '')}]" if s.get("alert_level") else ""
                    print(f"  • {s['signal_type']}: {s['title']}{alert}")

            # Print follow-up suggestions
            suggestions = result.get("suggested_questions")
            if suggestions:
                print("\n💡 Suggested follow-ups:")
                for i, q in enumerate(suggestions, 1):
                    print(f"  {i}. {q}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Entry point."""
    # Check for required env vars
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not set. Create a .env file (see .env.example)")
        sys.exit(1)

    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
