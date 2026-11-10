"""idea-check via the Claude API.

Runs the same procedure as the Claude Code skill without Claude Code:
four parallel research threads (prior art, adjacent incumbents, graveyard
and economics, commodity floor) using Claude's server-side web search and
web fetch, then three independent landscape reads, then one synthesis.

Every prompt is read from ../references/thread-prompts.md, which the skill
reads too, so the two cannot drift apart.

Usage:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...        # or `ant auth login`
    python idea_check.py "an app that ..."
    python idea_check.py --idea-file idea.txt --type "hardware product"
    python idea_check.py --resume ../checks/notes/2026-11-09-an-app-that

Outputs:
    <out>/<run>.html                    the report page, metadata in its first lines
    <out>/notes/<run>/                  each thread's notes and each read
    stdout                              a summary of at most 150 words

<run> is YYYY-MM-DD-<slug>, with -2, -3 ... appended if that name is taken.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPTS_FILE = HERE.parent / "references" / "thread-prompts.md"
TEMPLATE_FILE = HERE.parent / "references" / "report-template.html"

# (notes filename, heading in thread-prompts.md)
THREADS = [
    ("prior-art", "Thread 1: prior art"),
    ("incumbents", "Thread 2: adjacent incumbents"),
    ("graveyard-economics", "Thread 3: graveyard and economics"),
    ("commodity-floor", "Thread 4: commodity floor"),
]
READERS = ["Reader 1", "Reader 2", "Reader 3"]

# Every heading in thread-prompts.md that must carry a fenced block.
SECTIONS = [
    "Shared block",
    "Output instruction: skill",
    "Output instruction: API",
    *(title for _, title in THREADS),
    "Label definitions",
    *READERS,
    "Synthesis rules",
    "Report format",
    "Conversation summary",
]

LABELS = ("Open", "Crowded", "Saturated")
ENTITY_TYPES = ("software product", "hardware product", "service",
                "research direction", "content")

RESEARCH_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 25},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 40,
     "max_content_tokens": 20000},
]

READER_MAX_TOKENS = 4000
MAX_PAUSE_RESUMES = 10
SUMMARY_MARK = "=== SUMMARY ==="
PLACEHOLDER = re.compile(r"\{([A-Z_]+)\}")

# Words too common in idea descriptions to signal that two ideas overlap.
STOPWORDS = frozenset("""
    about also app apps based build builds building built company companies
    could customers data does from have help helps idea into just like make
    makes more most only other people platform product products service
    services software startup startups that their them then they this tool
    tools turns used user users uses using want what when where which will
    with would your
""".split())


class PromptError(Exception):
    """thread-prompts.md is missing something the runner needs."""


class StageFailed(Exception):
    """One or more requests in a stage failed; the rest were saved."""

    def __init__(self, errors: dict[str, Exception]):
        self.errors = errors
        super().__init__("; ".join(f"{k}: {e}" for k, e in errors.items()))


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

def load_prompts(path: Path = PROMPTS_FILE) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (blocks, orders) from thread-prompts.md.

    blocks maps each `## heading` to the text of its first fenced block.
    orders maps each reader heading to its "Notes order:" list.
    """
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## +(.+?)[ \t]*$", text, flags=re.M)
    blocks: dict[str, str] = {}
    orders: dict[str, list[str]] = {}
    for heading, body in zip(parts[1::2], parts[2::2]):
        fence = re.search(r"^```[^\n]*\n(.*?)\n```[ \t]*$", body, flags=re.S | re.M)
        if fence:
            blocks[heading] = fence.group(1)
        order = re.search(r"^Notes order:[ \t]*(.+)$", body, flags=re.M)
        if order:
            orders[heading] = [k.strip(" `.") for k in order.group(1).split(",")]

    missing = [s for s in SECTIONS if s not in blocks]
    if missing:
        raise PromptError(f"{path} has no fenced block under: {', '.join(missing)}")
    keys = sorted(k for k, _ in THREADS)
    for reader in READERS:
        if sorted(orders.get(reader, [])) != keys:
            raise PromptError(
                f"{path}: '{reader}' needs a 'Notes order:' line naming each of "
                f"{', '.join(keys)} exactly once"
            )
    return blocks, orders


def fill(template: str, **values: str) -> str:
    """Substitute {PLACEHOLDER}s in one pass; refuse to leave any behind.

    One pass means a value that itself contains "{TYPE}" (an idea can say
    anything) is not substituted a second time.
    """
    unknown = sorted(set(PLACEHOLDER.findall(template)) - values.keys())
    if unknown:
        raise PromptError(f"no value for placeholder(s): {', '.join(unknown)}")
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def thread_prompt(blocks: dict[str, str], title: str, idea: str, entity_type: str) -> str:
    return "\n\n".join([
        fill(blocks[title], IDEA=idea, TYPE=entity_type),
        fill(blocks["Shared block"]),
        fill(blocks["Output instruction: API"]),
    ])


def reader_prompt(blocks: dict[str, str], orders: dict[str, list[str]],
                  reader: str, idea: str, notes: dict[str, str]) -> str:
    bundle = "\n\n".join(
        f'<notes thread="{key}">\n{notes[key]}\n</notes>' for key in orders[reader]
    )
    return fill(blocks[reader], IDEA=idea, NOTES=bundle,
                LABEL_DEFINITIONS=blocks["Label definitions"])


def synthesis_system(blocks: dict[str, str]) -> str:
    return "\n\n".join([
        "You are writing the final idea-check landscape report from four "
        "research notes and three independent landscape reads, all given in "
        "the user message.",
        fill(blocks["Synthesis rules"]),
        "Output exactly this structure and nothing before it: the metadata "
        "block between two lines containing only ---, then the nine sections "
        "as raw HTML with no code fence around them.",
        fill(blocks["Report format"]),
        f"After the report, a line containing only:\n{SUMMARY_MARK}\n"
        "Then a summary for the terminal:",
        fill(blocks["Conversation summary"]),
    ])


# --------------------------------------------------------------------------
# Labels and front matter
# --------------------------------------------------------------------------

def parse_label(read: str) -> str:
    """The label on the read's first non-empty line, tolerant of markdown
    and prefixes ("**Saturated**", "Label: Saturated")."""
    first = next((ln for ln in read.splitlines() if ln.strip()), "")
    found = [l for l in LABELS if re.search(rf"\b{l}\b", first, flags=re.I)]
    return found[0] if len(found) == 1 else "Unlabelled"


def overall_label(labels: list[str]) -> str:
    """The label at least two reads agree on, else Split."""
    counts = Counter(l for l in labels if l in LABELS)
    if counts:
        label, n = counts.most_common(1)[0]
        if n >= 2:
            return label
    return "Split"


def parse_fields(block: str) -> dict[str, str]:
    pairs = (line.split(":", 1) for line in block.splitlines() if ":" in line)
    return {k.strip(): v.strip() for k, v in pairs}


def _unfence(text: str) -> str:
    """Drop a code fence the model wrapped around its output, if any."""
    return re.sub(r"^```[a-z]*\n(.*)\n```$", r"\1", text.strip(), flags=re.S)


def parse_synthesis(text: str) -> tuple[dict[str, str], str, str]:
    """Split the synthesis reply into (metadata fields, sections HTML, summary)."""
    report, _, summary = text.partition(SUMMARY_MARK)
    report = _unfence(report)
    fields: dict[str, str] = {}
    m = re.match(r"---\n(.*?)\n---\n?", report, flags=re.S)
    if m:
        fields = parse_fields(m.group(1))
        report = report[m.end():]
    sections = _unfence(report)
    # The page is opened locally and may be published; it never needs script.
    sections = re.sub(r"<script\b.*?</script>", "", sections, flags=re.S | re.I)
    return fields, sections.strip(), summary.strip()


def scale_html(labels: list[str]) -> str:
    """The three stops of the header scale, each read marked on its stop."""
    items = []
    for label in LABELS:
        marks = "".join(f"<i>{i + 1}</i>" for i, l in enumerate(labels) if l == label)
        chosen = " chosen" if marks else ""
        items.append(
            f'      <li class="stop stop-{label.lower()}{chosen}">'
            f'<span class="marks">{marks}</span><span class="bar"></span>'
            f'<span class="stop-name">{label}</span></li>'
        )
    return "\n".join(items)


def render_report(template: str, fields: dict[str, str], sections: str, *,
                  slug: str, date: str, labels: list[str]) -> str:
    """Fill report-template.html. The runner supplies slug, date, label and
    label_reads itself, so the lookup key never depends on the model
    copying them correctly."""
    idea = fields.get("idea", "")
    title = fields.get("title") or slug.replace("-", " ").capitalize()
    label = overall_label(labels)
    meta = {
        "idea": idea,
        "title": title,
        "slug": slug,
        "date": date,
        "label": label,
        "label_reads": "[" + ", ".join(labels) + "]",
        "top_occupants": fields.get("top_occupants", "[]"),
    }
    # "--" would end the HTML comment the metadata sits in.
    meta_text = "\n".join(k + ": " + re.sub(r"-{2,}", "-", v) for k, v in meta.items())
    return fill(template, META=meta_text, TITLE=html.escape(title),
                IDEA=html.escape(idea), DATE=date, LABEL=label,
                SCALE=scale_html(labels), SECTIONS=sections)


def read_front_matter(path: Path) -> dict[str, str]:
    """Metadata of a saved report: the leading comment of an .html report,
    or the YAML front matter of an older .md one."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = re.match(r"\s*(?:---\n(.*?)\n---|<!--idea-check\n(.*?)\n-->)", text, flags=re.S)
    if not m:
        return {}
    return parse_fields(m.group(1) or m.group(2))


# --------------------------------------------------------------------------
# Runs on disk
# --------------------------------------------------------------------------

def slugify(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "idea"


def new_run_name(out: Path, today: str, slug: str) -> str:
    """YYYY-MM-DD-slug, suffixed so an earlier run is never overwritten."""
    base = name = f"{today}-{slug}"
    n = 2
    while (out / f"{name}.html").exists() or (out / f"{name}.md").exists() \
            or (out / "notes" / name).exists():
        name = f"{base}-{n}"
        n += 1
    return name


def significant_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", text.lower()) if w not in STOPWORDS}


def related_checks(out: Path, idea: str, min_shared: int = 3) -> list[tuple[Path, dict[str, str]]]:
    """Earlier reports in `out` whose idea shares several significant words
    with this one. A crude match on purpose: it only has to prompt a look."""
    words = significant_words(idea)
    hits = []
    for path in sorted([*out.glob("*.html"), *out.glob("*.md")]):
        fm = read_front_matter(path)
        if not fm:
            continue
        theirs = significant_words(fm.get("idea", "") + " " + fm.get("slug", ""))
        if len(words & theirs) >= min_shared:
            hits.append((path, fm))
    return hits


def cached(path: Path, produce, resume: bool) -> str:
    """Return the saved text if resuming and present, else produce and save."""
    if resume and path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            log(f"      {path.stem}: reused from {path}")
            return text
    text = produce()
    path.write_text(text, encoding="utf-8")
    return text


def run_all(jobs: dict) -> dict[str, str]:
    """Run every job in parallel. Let all finish (so finished work is saved)
    before reporting any failure."""
    results: dict[str, str] = {}
    errors: dict[str, Exception] = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {key: pool.submit(job) for key, job in jobs.items()}
        for key, future in futures.items():
            try:
                results[key] = future.result()
            except Exception as e:  # noqa: BLE001 - reported to the user below
                errors[key] = e
    if errors:
        raise StageFailed(errors)
    return results


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def text_of(message) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


def run_turns(client, *, what: str, model: str, effort: str, system: str | None,
              user_content, tools=None, max_tokens: int = 64000,
              truncation_hint: str = "raise --max-tokens") -> str:
    """One streamed request, resumed on pause_turn until the model ends."""
    messages = [{"role": "user", "content": user_content}]
    for _ in range(MAX_PAUSE_RESUMES + 1):
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
            raise RuntimeError(f"{what}: request refused (category={cat})")
        if message.stop_reason == "max_tokens":
            raise RuntimeError(
                f"{what}: output truncated at max_tokens={max_tokens}; {truncation_hint}"
            )
        return text_of(message)
    raise RuntimeError(f"{what}: still paused after {MAX_PAUSE_RESUMES} resumes; giving up")


def infer_type(client, model: str, idea: str) -> str:
    reply = run_turns(
        client, what="entity type", model=model, effort="low", system=None,
        user_content=(
            f"Classify this idea as exactly one of: {', '.join(ENTITY_TYPES)}.\n"
            f"Reply with the type and nothing else.\n\nIdea: {idea}"
        ),
        max_tokens=READER_MAX_TOKENS,
        truncation_hint="pass --type to skip this step",
    ).lower()
    for t in ENTITY_TYPES:
        if t in reply:
            return t
    log(f"      could not infer an entity type from {reply!r}; using 'software product'")
    return "software product"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("idea", nargs="?", help="the idea in plain English")
    ap.add_argument("--idea-file", type=Path, help="read the idea from a file")
    ap.add_argument("--type", default=None,
                    help=f"entity type: {', '.join(ENTITY_TYPES)} "
                         "(default: inferred from the idea)")
    ap.add_argument("--model", default="claude-opus-5-5",
                    help="model for research threads and synthesis")
    ap.add_argument("--reader-model", default=None,
                    help="model for the three landscape reads (default: --model)")
    ap.add_argument("--out", type=Path, default=HERE.parent / "checks",
                    help="directory for the report and notes")
    ap.add_argument("--max-tokens", type=int, default=64000,
                    help="output cap for each research thread and the synthesis")
    ap.add_argument("--fresh", action="store_true",
                    help="run even if an earlier report in --out looks related")
    ap.add_argument("--resume", type=Path, metavar="NOTES_DIR",
                    help="finish an interrupted run, reusing the notes and reads "
                         "already saved in its notes directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the prompts exactly as they would be sent, "
                         "then exit without calling the API")
    args = ap.parse_args(argv)

    try:
        blocks, orders = load_prompts()
        template = TEMPLATE_FILE.read_text(encoding="utf-8")
    except (PromptError, OSError) as e:
        log(f"error: {e}")
        return 2

    if args.resume:
        if args.idea or args.idea_file:
            ap.error("--resume takes the idea from the saved run; do not pass one")
        notes_dir = args.resume.resolve()
        try:
            run = json.loads((notes_dir / "run.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            ap.error(f"cannot resume from {notes_dir}: {e}")
        idea, entity_type = run["idea"], run["type"]
        today, slug, name = run["date"], run["slug"], run["name"]
        out = notes_dir.parent.parent
    else:
        if args.idea_file:
            idea = args.idea_file.read_text(encoding="utf-8").strip()
        elif args.idea:
            idea = args.idea.strip()
        else:
            ap.error("give the idea as an argument or with --idea-file")
        entity_type = args.type
        today = dt.date.today().isoformat()
        slug = slugify(idea)
        out = args.out
        name = new_run_name(out, today, slug)
        notes_dir = out / "notes" / name

    reader_model = args.reader_model or args.model
    report_path = out / f"{name}.html"

    if args.dry_run:
        shown_type = entity_type or "<inferred from the idea at run time>"
        placeholder_notes = {k: f"<notes from the {k} thread>" for k, _ in THREADS}
        for _, title in THREADS:
            print(f"===== {title} ({args.model}) =====\n"
                  f"{thread_prompt(blocks, title, idea, shown_type)}\n")
        for reader in READERS:
            print(f"===== {reader} ({reader_model}) =====\n"
                  f"{reader_prompt(blocks, orders, reader, idea, placeholder_notes)}\n")
        print(f"===== synthesis system prompt ({args.model}) =====\n"
              f"{synthesis_system(blocks)}\n")
        print(f"report would be written to {report_path}")
        return 0

    if not args.resume and not args.fresh:
        related = related_checks(out, idea)
        if related:
            log("An earlier check looks related to this idea:")
            for path, fm in related:
                log(f"  {path}\n    {fm.get('date', '?')}  {fm.get('label', '?')}  "
                    f"{fm.get('idea', '')}")
            log("Read it first. To run new research anyway, add --fresh.")
            return 3

    import anthropic  # imported here so --dry-run works without the SDK

    client = anthropic.Anthropic()
    resume = bool(args.resume)

    try:
        if entity_type is None:
            log(f"[0/3] inferring the entity type on {reader_model} ...")
            entity_type = infer_type(client, reader_model, idea)
            log(f"      type: {entity_type}")

        notes_dir.mkdir(parents=True, exist_ok=True)
        (notes_dir / "run.json").write_text(json.dumps({
            "idea": idea, "type": entity_type, "date": today,
            "slug": slug, "name": name,
        }, indent=2), encoding="utf-8")

        # Stage 1: four research threads in parallel.
        log(f"[1/3] running four research threads on {args.model} ...")

        def research(key: str, title: str) -> str:
            def produce() -> str:
                text = run_turns(
                    client, what=key, model=args.model, effort="high", system=None,
                    user_content=thread_prompt(blocks, title, idea, entity_type),
                    tools=RESEARCH_TOOLS, max_tokens=args.max_tokens,
                )
                log(f"      {key}: {len(text.split())} words")
                return text
            return cached(notes_dir / f"{key}.md", produce, resume)

        notes = run_all({key: (lambda k=key, t=title: research(k, t))
                         for key, title in THREADS})

        # Stage 2: three independent reads. Each sees only the notes and its
        # own prompt; none sees another read or any draft of the synthesis.
        log(f"[2/3] three independent landscape reads on {reader_model} ...")

        def read_once(reader: str) -> str:
            def produce() -> str:
                return run_turns(
                    client, what=reader, model=reader_model, effort="low", system=None,
                    user_content=reader_prompt(blocks, orders, reader, idea, notes),
                    max_tokens=READER_MAX_TOKENS,
                    truncation_hint="raise READER_MAX_TOKENS in idea_check.py",
                ).strip()
            return cached(notes_dir / f"{slugify(reader)}.md", produce, resume)

        reads_by_reader = run_all({r: (lambda r=r: read_once(r)) for r in READERS})
        reads = [reads_by_reader[r] for r in READERS]
        labels = [parse_label(r) for r in reads]
        log(f"      reads: {labels}")
        if "Unlabelled" in labels:
            log("      warning: a read did not open with a label; see the "
                f"reader-*.md files in {notes_dir}")

        # Stage 3: one synthesis. No critic pass.
        log(f"[3/3] synthesis on {args.model} ...")
        notes_bundle = "\n\n".join(
            f'<notes thread="{key}">\n{notes[key]}\n</notes>' for key, _ in THREADS
        )
        reads_block = "\n\n".join(
            f'<read n="{i + 1}">\n{r}\n</read>' for i, r in enumerate(reads)
        )
        synthesis = run_turns(
            client, what="synthesis", model=args.model, effort="high",
            system=synthesis_system(blocks),
            user_content=(
                f"Idea: {idea}\nEntity type: {entity_type}\nDate: {today}\n"
                f"Slug: {slug}\n\n{notes_bundle}\n\n{reads_block}"
            ),
            max_tokens=args.max_tokens,
        )
    except (StageFailed, RuntimeError, anthropic.APIError) as e:
        if isinstance(e, StageFailed):
            for key, err in e.errors.items():
                log(f"error: {key}: {err}")
        else:
            log(f"error: {e}")
        if (notes_dir / "run.json").exists():
            log("Finished work is saved. To pick up where this stopped:\n"
                f'  python {Path(__file__).name} --resume "{notes_dir}"')
        return 1

    fields, sections, summary = parse_synthesis(synthesis)
    try:
        report = render_report(template, fields, sections,
                               slug=slug, date=today, labels=labels)
    except PromptError as e:
        log(f"error: {TEMPLATE_FILE.name}: {e}")
        return 2
    report_path.write_text(report, encoding="utf-8")

    print(summary or "(no summary section returned)")
    print(f"\nReport: {report_path}\nNotes:  {notes_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
