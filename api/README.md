# idea-check via the Claude API

The same procedure as the Claude Code skill, for people who do not run
Claude Code: four parallel research threads using Claude's server-side web
search and web fetch, three independent landscape reads, one synthesis.

The prompts are read from `../references/thread-prompts.md` at run time, so
editing that file changes both the skill and this runner.

## Setup

```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or run `ant auth login`
```

## Run

```
python idea_check.py "a tool that turns meeting recordings into Jira tickets"
python idea_check.py --idea-file idea.txt --type "hardware product"
python idea_check.py "..." --reader-model claude-sonnet-5-5   # cheaper reads
python idea_check.py "..." --dry-run                           # print prompts, no API calls
```

Entity types: software product, hardware product, service, research
direction, content.

## What it does

1. Launches the four research threads at once, each a single streamed
   request with `web_search_20260209` and `web_fetch_20260209` enabled and
   the mandatory shared block appended. Server-side tool loops that hit
   their iteration cap (`pause_turn`) are resumed automatically.
2. Sends the four notes to three independent readers in parallel. Each
   reader sees only the notes and the label definitions, never another
   reader's answer or a draft of the report.
3. Runs one synthesis pass that writes the report with YAML front matter,
   then prints a summary of at most 150 words. There is no critic or
   debate pass, by design (see the top-level README).

Outputs go to `--out` (default `../checks`): the report at
`YYYY-MM-DD-<slug>.md` and each thread's notes under `notes/<slug>/`.

## Model and cost

Defaults to `claude-opus-5-5` for every stage, with `effort: high` on the
research threads and synthesis and `effort: low` on the readers. Server-side
refusal fallbacks are enabled (`fallbacks: "default"`) so a safety decline
on one stage is re-run on the fallback model inside the same call. A full
run makes eight requests, four of them long and search-heavy; expect it to
take several minutes and to cost a few dollars at Opus rates. Pass
`--reader-model claude-sonnet-5-5` to make the three reads cheaper.

## Known limits

Web fetch only opens URLs that already appear in the conversation, so the
threads fetch pages that search surfaced. Each thread is capped at 25
searches and 40 fetches (`RESEARCH_TOOLS` in the script); raise them for a
deeper run. The threads cannot write files, so their "Not checked" lists are
the only record of what the budget cut off.
