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

The first of those is the highest-value instruction in the skill. In a
study of LLM data-analysis agents, switching the analyst's persona from
the most skeptical to the most confirmation-seeking moved the share of
analyses that supported the hypothesis by 34 to 66 percentage points
across datasets [1]. That makes the framing a correctness issue, not a
tone choice.

## Why the verdict is not a verdict

The report ends with a landscape label (Open, Crowded, or Saturated) and a
"what would have to be true" section instead of a will-work or won't-work
call. Three reasons.

**Single-pass verdicts are unstable.** In a benchmark of LLM novelty
judges, deleting one sentence from the prompt took one model's pairwise
accuracy from 93.5 to 40.9 percent on the same pairs [2]. A confident yes
or no from one pass depends heavily on how the question was phrased. So the skill runs the label three times in independent subagents
that see only the research notes, and reports all three. The three readers
are asked the same question in different words and are given the notes in
a different order, so a label that all three reach did not hinge on the
phrasing; three copies of one prompt would only differ by chance. Disagreement is
shown, not averaged, because the disagreement is the most informative line
in the report. In the same benchmark, the cheapest prompted setup, three
calls per decision, outscored two purpose-built novelty tools that cost
about 12 and 32 times more [2].

**Debate layers make it worse.** It is tempting to add a critic or red-team
agent over the synthesis. In one evaluation, no multi-agent debate method
beat plain chain-of-thought in more than 20 percent of 36 model and
benchmark pairings [3], and another found debate can leave answers worse
than a single agent's [4]. So the skill forbids it.

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
gets a summary of at most 150 words, the link and the file path. The page
uses fonts already on your machine and loads nothing from other sites, so
opening a report about a private idea contacts nobody.

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
- `examples/`: sample reports from 2026-11-03, researched at category
  level. `2026-11-03-robotics-lab-startup.html` shows what the skill
  produces now: open it in a browser. It was converted from the markdown
  report beside it, with the roast written at conversion. The two `.md`
  files are the older format, from before the HTML page and the roast.
- `tests/`: offline tests for the runner and the prompt file. Run them
  with `python -m unittest discover -s tests`; they also run in CI.
- `LICENSE`: MIT.

## Sources

Each figure above was checked against the paper itself. They come from
single studies with specific setups, so read them as support for the
design, not as general laws.

1. Bertran, Fogliato and Wu (2026), "Many AI Analysts, One Dataset:
   Navigating the Agentic Data Science Multiverse".
   https://arxiv.org/abs/2602.18710 . The 34 to 66 point range is the gap
   in support rate between the most skeptical and most
   confirmation-seeking analyst personas, across three datasets.
2. Sternlicht, Shahid, Jansen, Weld, Siangliulue and Hope (2026), "Old
   Ideas, Novel Problems: The Instability of LLM-Based Novelty
   Evaluation". https://arxiv.org/abs/2610.02022 . 93.5 and 40.9 are one
   judge's pairwise accuracy under two prompts (Figure 4b, human versus
   generated pairs); the dropped sentence told the judge that reviewers
   had found one idea novel, so the prompts differ in information as well
   as wording. The cost multiples are computed from the paper's Table 5;
   the paper itself says "up to 32×".
3. Zhang et al. (2025), "Stop Overvaluing Multi-Agent Debate".
   https://arxiv.org/abs/2502.08788 . The baselines are chain-of-thought
   and self-consistency on the same model.
4. Wynn, Satija and Hadfield (2025), "Talk Isn't Always Cheap:
   Understanding Failure Modes in Multi-Agent Debate".
   https://arxiv.org/abs/2509.05396 .

## Known limits

Absence of evidence is weak here; small competitors and dead companies are
both poorly indexed. Enterprise pricing is usually sales-gated. Roughly a
third of search results in any software category are vendors writing SEO
about each other, which is why the discarded-sources list is part of the
report.
