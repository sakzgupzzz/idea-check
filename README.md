# idea-check

A Claude Code skill that takes a product or startup idea in plain English
and returns a research-backed landscape report. It tells you who already
occupies the space, what has died there, who would pay, and what is already
free. It deliberately does not tell you whether the idea will work.

## Usage

**In Claude Code.** Clone it into your skills folder:

```
git clone https://github.com/sakzgupzzz/idea-check.git ~/.claude/skills/idea-check
```

That installs it for every project; clone into `.claude/skills/idea-check`
inside a project to install it for that project only. Then ask Claude
something like "does this already exist: a tool that ..." or "is anyone
doing X" or "run a prior-art check on this idea". The skill restates the
idea, launches four research subagents in parallel, then synthesizes a
report under 1,500 words, roast included.

**Via the Claude API.** The `api/` folder has a standalone Python runner
that does the same four threads, three reads and synthesis through the
Messages API with server-side web search, for people who do not use Claude
Code:

```
pip install -r api/requirements.txt
python api/idea_check.py "an app that ..."
```

Both paths take every prompt, the label definitions and the report format
from `references/thread-prompts.md`, and nothing restates them, so they
stay in sync. See `api/README.md` for options and cost.

## The four threads

The decomposition is fixed. Each thread is a separate subagent with a
separate brief, because a single researcher told to "look into this idea"
reliably finds competitors and nothing else.

1. **Prior art.** Who already ships this: commercial products with pricing,
   GitHub repos with stars and license and last commit, papers, patents.
   The brief asks for what each occupant does not cover, because gaps are
   more actionable than a list.
2. **Adjacent incumbents.** Which established categories already solve this
   as a feature, and who would absorb it if it worked. This is separate
   from prior art because it matters more. Products in this space more
   often die to an incumbent bundling the feature from above than to a
   head-on competitor.
3. **Graveyard and economics.** What has already been tried and failed, and
   whether the people who want this can pay for it. This thread is briefed
   to be adversarial toward the business case. A thread briefed to find
   competitors will never find the graveyard, and a thread briefed to find
   the graveyard will not think about pricing, so both live in the most
   skeptical brief.
4. **Commodity floor.** How much of this a frontier model, open source, or
   an existing subscription already does for free. The remaining delta is
   the only thing that could ever be sold.

Every thread carries the same shared block: assume prior art exists and
hunt for it; write "found nothing, which is not the same as absent" when
coming up empty and list what was not checked; cite a URL for every claim;
exclude listicles, "best tools" roundups, programmatic pricing sites, and
market-sizing sellers; and label each finding as a vendor claim or
independent evidence.

The first of those is the highest-value instruction in the skill. In
published measurements, framing a research task toward confirmation rather
than falsification shifts conclusions by 34 to 66 percentage points. That
makes the framing a correctness issue, not a tone choice.

## Why the verdict is not a verdict

The report ends with a landscape label (Open, Crowded, or Saturated) and a
"what would have to be true" section instead of a will-work or won't-work
call. Three reasons.

**Single-pass verdicts are unstable.** Benchmarked novelty judgments swing
from 93.5 to 40.9 percent accuracy on prompt rewording alone. A confident
yes or no from one pass is mostly a function of how the question was
phrased. So the skill runs the label three times in independent subagents
that see only the research notes, and reports all three. The three readers
are asked the same question in different words and are given the notes in
a different order, so a label that all three reach did not hinge on the
phrasing; three copies of one prompt would only differ by chance. Disagreement is
shown, not averaged, because the disagreement is the most informative line
in the report. A cheap three-call vote also outperformed purpose-built
single-pass tools costing twelve times more.

**Debate layers make it worse.** It is tempting to add a critic or red-team
agent over the synthesis. Published results show multi-agent debate
underperforms a single strong pass and degrades accuracy in most tested
configurations, so the skill forbids it.

**The research cannot see whether you can win.** It can see whether the
space is occupied. Whether you specifically beat the occupants depends on
distribution, team, and timing, none of which a web search returns. The
honest output is the set of conditions under which the idea survives, and
what evidence would settle each one, so you can go test them.

## The roast

After the measured part, the report has one section that is not measured
at all. "The roast" spends up to 300 words explaining why the idea is
fucking stupid. It takes the least charitable reading the evidence allows,
goes after every weak point, and is not allowed to hedge, find a silver
lining, or end on a consolation. It is
there because the strongest case against an idea is worth hearing once at
full volume, and because it is more fun to read than a table.

It does not break the no-verdict rule, for two reasons. It is labelled as
one-sided in its first line, and it is only allowed to use what the
research found: the dead company that tried this, the incumbent giving it
away, the buyer who cannot pay. A roast with nothing real behind it is
just noise. It is written in the same synthesis pass as the rest, not by a
separate critic agent, and it targets the idea, not you. The two reports
in `examples/` predate this section and do not have one.

## Output

The report is a styled HTML page, not a markdown file. It is written to
`checks/YYYY-MM-DD-<slug>.html` inside the skill folder from
`references/report-template.html`, which holds the CSS and a header that
shows the label on a three-stop scale with each independent read marked on
it. In a session that can publish artifacts, the skill publishes the page
and gives you the link; artifacts are private until you share them.
Without that tool, the saved file opens in any browser. The conversation
gets a summary of at most 150 words, the link and the file path.

The first lines of each page carry a metadata comment (idea, title, slug,
date, label, the three label reads, top occupants) so later runs can find
a report without reading the body.

`checks/` is git-ignored. The idea you are checking is usually private, and
the skill folder is a git clone, so reports stay out of version control
unless you move one out deliberately. A second check of the same idea on
the same day gets a `-2` suffix instead of replacing the first.

Before launching research, the skill lists `checks/` and reads the
metadata of anything related. If an earlier check overlaps, it says so and
asks whether to extend it or run fresh, because repeating a check you have
already run is the most common waste in this workflow.

## Files

- `SKILL.md`: the skill, loaded when it triggers.
- `references/thread-prompts.md`: the single source for the four research
  prompts, the shared block, the label definitions, the three reader
  prompts, the synthesis rules and the report format. Read by both the
  skill and the API runner.
- `references/report-template.html`: the report page, with its CSS, light
  and dark themes, and the slots the skill and the runner fill.
- `api/`: the Claude API runner (`idea_check.py`), its README and
  requirements.
- `checks/`: one report page per idea you check. Created on first run and
  git-ignored.
- `examples/`: two sample reports from 2026-11-03, an AI entertainment
  startup and a robotics lab startup, both researched at category level.
  They are in the older markdown format, from before the HTML page and
  the roast.
- `tests/`: offline tests for the runner and the prompt file. Run them
  with `python -m unittest discover -s tests`; they also run in CI.
- `LICENSE`: MIT.

## Known limits

Absence of evidence is weak here; small competitors and dead companies are
both poorly indexed. Enterprise pricing is usually sales-gated. Roughly a
third of search results in any software category are vendors writing SEO
about each other, which is why the discarded-sources list is part of the
report.
