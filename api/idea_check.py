"""idea-check via the Claude API.

Runs the same procedure as the Claude Code skill without Claude Code:
four parallel research threads (prior art, adjacent incumbents, graveyard
and economics, commodity floor) using Claude's server-side web search and
web fetch, then three independent landscape reads, then one synthesis.

The thread prompts are read from ../references/thread-prompts.md so the API
runner and the skill never drift apart.

Usage:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...        # or `ant auth login`
    python idea_check.py "an app that ..." --type "software product"
    python idea_check.py --idea-file idea.txt --out ../checks

Outputs:
    <out>/YYYY-MM-DD-<slug>.md          the report, with YAML front matter
    <out>/notes/<slug>/<thread>.md      each thread's full notes
    stdout                              a summary of at most 150 words
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPTS_FILE = HERE.parent / "references" / "thread-prompts.md"

THREADS = [
    ("prior-art", "Thread 1: prior art"),
    ("incumbents", "Thread 2: adjacent incumbents"),
    ("graveyard-economics", "Thread 3: graveyard and economics"),
    ("commodity-floor", "Thread 4: commodity floor"),
]

LABELS = ("Open", "Crowded", "Saturated")

RESEARCH_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 25},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 40,
     "max_content_tokens": 20000},
]

SYNTHESIS_INSTRUCTIONS = """You are writing the final idea-check landscape report from four research
notes files and three independent landscape reads. Do not research further.

Rules:
- Do not output a will-work or won't-work verdict. Report evidence and the
  conditions under which the idea survives.
- Report the three landscape reads verbatim with their reasoning. If they
  disagree, show the disagreement; do not average or pick a winner.
- Do not add a critic or debate pass.
- Mark vendor claims as such. Keep "found nothing, which is not the same as
  absent" wherever a thread said it, with what was not checked.
- Under 1,200 words. Prose by default, a table only where comparison is
  genuinely needed. No em dashes anywhere.

Output exactly this structure.

First, YAML front matter:
---
idea: <one-line statement of the idea>
slug: <kebab-case-name>
date: <date given below>
label: <Open | Crowded | Saturated; the most common read, or Split if all differ>
label_reads: [<read1>, <read2>, <read3>]
top_occupants: [<name1>, <name2>, <name3>]
---

Then a level-one heading with a short name for the report, then these
level-two sections in this order:
1. The idea, as understood
2. Who is already there
3. The graveyard
4. The economics
5. The commodity floor
6. Landscape label
7. What would have to be true
8. Sources, and sources discarded

Then a line containing only:
=== SUMMARY ===
Then at most 150 words for the terminal: the label and whether the three
reads agreed, the two or three closest occupants, and the single most
decisive finding.
"""


def load_prompts() -> dict[str, str]:
    """Pull the fenced prompt templates out of thread-prompts.md, in order."""
    text = PROMPTS_FILE.read_text(encoding="utf-8")
    fences = re.findall(r"```\n(.*?)\n```", text, flags=re.S)
    if len(fences) != 6:
        sys.exit(
            f"expected 6 fenced blocks in {PROMPTS_FILE} (shared, four threads, "
            f"reader), found {len(fences)}"
        )
    shared, t1, t2, t3, t4, reader = fences
    # The skill version tells each thread to save a notes file; here the
    # runner writes the file, so swap that line for a reply instruction.
    shared = re.sub(
        r"Save your notes to \{NOTES_DIR\}/\{FILENAME\}\.md",
        "Reply with your full findings in markdown, with a \"Findings\", "
        "\"Found nothing\" (if any), \"Discarded sources\", and \"Not checked\" "
        "section. Do not add a separate summary.",
        shared,
    )
    return {
        "shared": shared,
        "prior-art": t1,
        "incumbents": t2,
        "graveyard-economics": t3,
        "commodity-floor": t4,
        "reader": reader,
    }


def fill(template: str, **values: str) -> str:
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", v)
    return out


def slugify(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "idea"


def text_of(message) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


def run_turns(client, *, model: str, effort: str, system: str | None,
              user_content, tools=None, max_tokens: int = 64000) -> str:
    """One streamed request, resumed on pause_turn until the model ends."""
    messages = [{"role": "user", "content": user_content}]
    while True:
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            output_config={"effort": effort},
            messages=messages,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        with client.beta.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()
        if message.stop_reason == "pause_turn":
            # Server-side tool loop hit its iteration cap; resend to resume.
            messages.append({"role": "assistant", "content": message.content})
            continue
        if message.stop_reason == "refusal":
            cat = message.stop_details.category if message.stop_details else None
            raise RuntimeError(f"request refused (category={cat})")
        if message.stop_reason == "max_tokens":
            raise RuntimeError("output truncated at max_tokens; raise --max-tokens")
        return text_of(message)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("idea", nargs="?", help="the idea in plain English")
    ap.add_argument("--idea-file", type=Path, help="read the idea from a file")
    ap.add_argument("--type", default="software product",
                    help="entity type: software product, hardware product, "
                         "service, research direction, content")
    ap.add_argument("--model", default="claude-opus-5-5",
                    help="model for research threads and synthesis")
    ap.add_argument("--reader-model", default=None,
                    help="model for the three landscape reads (default: --model)")
    ap.add_argument("--out", type=Path, default=HERE.parent / "checks",
                    help="directory for the report and notes")
    ap.add_argument("--max-tokens", type=int, default=64000)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the assembled prompts and exit without calling the API")
    args = ap.parse_args()

    if args.idea_file:
        idea = args.idea_file.read_text(encoding="utf-8").strip()
    elif args.idea:
        idea = args.idea.strip()
    else:
        ap.error("give the idea as an argument or with --idea-file")

    prompts = load_prompts()
    today = dt.date.today().isoformat()
    slug = slugify(idea)
    notes_dir = args.out / "notes" / slug
    reader_model = args.reader_model or args.model

    thread_prompts = {
        key: fill(prompts[key], IDEA=idea, TYPE=args.type) + "\n\n" + prompts["shared"]
        for key, _ in THREADS
    }

    if args.dry_run:
        for key, title in THREADS:
            print(f"===== {title} ({args.model}) =====\n{thread_prompts[key]}\n")
        print(f"===== reader x3 ({reader_model}) =====\n{prompts['reader']}\n")
        print(f"===== synthesis ({args.model}) =====\n{SYNTHESIS_INSTRUCTIONS}")
        print(f"report would be written to {args.out / f'{today}-{slug}.md'}")
        return 0

    import anthropic  # imported here so --dry-run works without the SDK

    client = anthropic.Anthropic()
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: four research threads in parallel.
    print(f"[1/3] running four research threads on {args.model} ...", file=sys.stderr)

    def research(key: str) -> tuple[str, str]:
        text = run_turns(
            client, model=args.model, effort="high", system=None,
            user_content=thread_prompts[key], tools=RESEARCH_TOOLS,
            max_tokens=args.max_tokens,
        )
        (notes_dir / f"{key}.md").write_text(text, encoding="utf-8")
        print(f"      {key}: {len(text.split())} words", file=sys.stderr)
        return key, text

    with ThreadPoolExecutor(max_workers=4) as pool:
        notes = dict(pool.map(research, [k for k, _ in THREADS]))

    notes_bundle = "\n\n".join(
        f"<notes thread=\"{key}\">\n{notes[key]}\n</notes>" for key, _ in THREADS
    )

    # Stage 2: three independent reads. Each sees only the notes and the
    # reader prompt; none sees another read or any draft of the synthesis.
    print(f"[2/3] three independent landscape reads on {reader_model} ...", file=sys.stderr)
    reader_prompt = re.sub(
        r"Read these four research notes files and nothing else:\n(?:\{NOTES_DIR\}/[^\n]+\n)+",
        "Read the four research notes below and nothing else.\n",
        prompts["reader"],
    )
    reader_prompt = fill(reader_prompt, IDEA=idea)

    def read_once(i: int) -> str:
        return run_turns(
            client, model=reader_model, effort="low", system=None,
            user_content=f"{reader_prompt}\n\n{notes_bundle}",
            max_tokens=2000,
        ).strip()

    with ThreadPoolExecutor(max_workers=3) as pool:
        reads = list(pool.map(read_once, range(3)))
    labels = [next((l for l in LABELS if r.lower().startswith(l.lower())), "Unlabelled")
              for r in reads]
    print(f"      reads: {labels}", file=sys.stderr)

    # Stage 3: one synthesis. No critic pass.
    print(f"[3/3] synthesis on {args.model} ...", file=sys.stderr)
    reads_block = "\n\n".join(f"<read n=\"{i + 1}\">\n{r}\n</read>" for i, r in enumerate(reads))
    synthesis = run_turns(
        client, model=args.model, effort="high", system=SYNTHESIS_INSTRUCTIONS,
        user_content=(
            f"Idea: {idea}\nEntity type: {args.type}\nDate: {today}\nSlug: {slug}\n\n"
            f"{notes_bundle}\n\n{reads_block}"
        ),
        max_tokens=args.max_tokens,
    )

    report, _, summary = synthesis.partition("=== SUMMARY ===")
    report = report.strip() + "\n"
    report_path = args.out / f"{today}-{slug}.md"
    report_path.write_text(report, encoding="utf-8")

    print(summary.strip() or "(no summary section returned)")
    print(f"\nReport: {report_path}\nNotes:  {notes_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
