# idea-check via the Claude API

The same procedure as the Claude Code skill, for people who do not run
Claude Code: four parallel research threads using Claude's server-side web
search and web fetch, three independent landscape reads, one synthesis.

Every prompt, the label definitions and the report format are read from
`../references/thread-prompts.md` at run time, so editing that file changes
both the skill and this runner. The runner refuses to start if a block it
needs is missing, and refuses to send a prompt with an unfilled
placeholder.

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
python idea_check.py "..." --fresh                             # run despite a related earlier check
python idea_check.py --resume ../checks/notes/<run>            # finish an interrupted run
```

Entity types: software product, hardware product, service, research
direction, content. Leave `--type` off and the runner picks one with a
short extra request before the research starts.

## What it does

1. Looks in `--out` for earlier reports whose idea shares several
   significant words with this one. If it finds any it lists them and
   stops, so you can read them first; `--fresh` skips this. The match is a
   plain word overlap on the reports' front matter, so it can miss a
   related check that was worded differently.
2. Launches the four research threads at once, each a single streamed
   request with `web_search_20260209` and `web_fetch_20260209` enabled and
   the mandatory shared block appended. Server-side tool loops that hit
   their iteration cap (`pause_turn`) are resumed automatically, up to ten
   times per request.
3. Sends the four notes to three independent readers in parallel. Each
   reader sees only the notes and the label definitions, never another
   reader's answer or a draft of the report. The three readers get
   differently worded prompts and the notes in a different order.
4. Runs one synthesis pass that writes the nine report sections as HTML,
   then prints a summary of at most 150 words. There is no critic or
   debate pass, by design (see the top-level README). The runner drops the
   sections into `../references/report-template.html`, draws the label
   scale, and sets `slug`, `date`, `label` and `label_reads` in the page's
   metadata itself, from the reads it parsed, so those fields do not
   depend on the model copying them correctly.

The result is one self-contained `.html` page that opens in any browser.
The runner cannot publish artifacts; that step belongs to the Claude Code
skill.

Outputs go to `--out` (default `../checks`): the report at `<run>.html`, and
under `notes/<run>/` each thread's notes, each read, and a `run.json` with
the idea and type. `<run>` is `YYYY-MM-DD-<slug>`, with `-2`, `-3` and so
on appended when that name is taken, so a rerun never overwrites an
earlier report.

## When a request fails

A stage waits for all of its requests before reporting a failure, and
everything that finished is already on disk. The error message ends with
the exact `--resume` command. Resuming reuses the saved notes and reads
and only re-sends what is missing, so one refused or dropped thread does
not cost you the other three.

## Model and cost

Defaults to `claude-opus-5-5` for every stage, with `effort: high` on the
research threads and synthesis and `effort: low` on the readers. Server-side
refusal fallbacks are enabled (`fallbacks: "default"`) so a safety decline
on one stage is re-run on the fallback model inside the same call. A full
run makes eight requests (nine when the type is inferred), four of them
long and search-heavy; expect it to
take several minutes and to cost a few dollars at Opus rates. Pass
`--reader-model claude-sonnet-5-5` to make the three reads cheaper.

## Known limits

Web fetch only opens URLs that already appear in the conversation, so the
threads fetch pages that search surfaced. Each thread is capped at 25
searches and 40 fetches (`RESEARCH_TOOLS` in the script); raise them for a
deeper run. The threads cannot write files, so their "Not checked" lists are
the only record of what the budget cut off.
