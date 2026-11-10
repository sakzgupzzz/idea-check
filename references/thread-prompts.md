# Prompt templates

This file is the single source for every prompt the skill and the API
runner use. The text inside each fenced block is used as written. The
runner (`api/idea_check.py`) looks blocks up by their `##` heading, so do
not rename a heading without updating `SECTIONS` there; the tests in
`tests/` fail if the two fall out of step.

Placeholders, substituted before a prompt is sent:

- `{IDEA}`: the restated one-paragraph version of the user's idea.
- `{TYPE}`: the entity type (software product, hardware product, service,
  research direction, content).
- `{NOTES_DIR}`: the scratchpad notes directory for this run (skill only).
- `{FILENAME}`: the thread's notes filename, given under each thread
  heading (skill only).
- `{LABEL_DEFINITIONS}`: the "Label definitions" block.
- `{NOTES}`: the four research notes, in the order given under each reader
  heading. In the skill this is the four notes file paths, one per line.
  The API runner inlines the notes themselves.

A research prompt is three blocks joined by blank lines: the thread
template, then the shared block, then one output instruction (the skill
one in Claude Code, the API one in the runner). Launch the four research
threads in parallel in one message. Do not omit or trim the shared block.

## Shared block

```
Assume prior art exists and hunt for it. Your job is to find who occupies
this space, not to confirm it is empty. Report who occupies this space,
bluntly.

Where you find nothing, write "found nothing, which is not the same as
absent" and list what you did not check.

Every factual claim needs a source URL.

Exclude AI-generated listicles, "best tools" roundup pages, programmatic
pricing sites, and syndicated market-sizing sellers from all factual
claims. Name the sources you discarded, with a one-phrase reason each.
Roughly a third of search results in this domain are vendors writing SEO
about each other. Report that volume as a finding of its own, but do not
cite any of it.

Distinguish vendor claims from independent evidence in every finding. Label
each finding "vendor claim" or "independent" and say what the independent
evidence is (a user review, a filing, a repo, a paper, press coverage that
is not a rewritten press release).

Use web search and fetch. Prefer primary sources: the product's own pricing
page for pricing, the GitHub repo page for stars and last commit, Google
Patents or USPTO for patents, arXiv or a journal for papers, Crunchbase or
press for shutdowns and acquisitions.
```

## Output instruction: skill

```
Write your full findings to {NOTES_DIR}/{FILENAME}.md in markdown, with a
"Findings", "Found nothing" (if any), "Discarded sources", and "Not checked"
section. Then reply with a summary under 200 words.
```

## Output instruction: API

```
Reply with your full findings in markdown, with a "Findings", "Found
nothing" (if any), "Discarded sources", and "Not checked" section. Do not
shorten them into a summary; your reply is the only record of this research.
```

## Thread 1: prior art

FILENAME: `prior-art`

```
Research who already ships something matching this idea: {IDEA}

Entity type: {TYPE}

Cover: commercial products with pricing where published; GitHub repos with
stars, license and last commit date; academic work; patents. Search at least
three phrasings of the idea, including the words a buyer would use and the
words an engineer would use, because those often return different products.

For each occupant found, state how close it is to the idea on a rough scale
(same thing, overlapping, adjacent) and, specifically, what it does NOT
cover. The gaps in existing products are more useful than the list of
products.
```

## Thread 2: adjacent incumbents

FILENAME: `incumbents`

```
Research which established product categories already solve this as a
feature, and who would absorb it if it worked: {IDEA}

Entity type: {TYPE}

Do not look for direct competitors; another thread covers those. Look for
the larger platform or category that would bundle this. For each, find
whether they have already shipped something adjacent, and whether their
public roadmap, changelog, or recent releases point at it. Check the obvious
suite vendors for this user segment and the platforms the target user
already lives in.

Products in this space more often die to an incumbent adding the feature
from above than to a startup competing head on, so name the most likely
absorber explicitly and say how far along they already are.
```

## Thread 3: graveyard and economics

FILENAME: `graveyard-economics`

```
Be adversarial toward the business case for this idea: {IDEA}

Entity type: {TYPE}

Part one, the graveyard. What has already been tried in this space and
failed. Shutdowns, acquisitions at low value, pivots away from the idea,
layoffs, and decline in adjacent public companies. Search for category terms
plus "shut down", "sunset", "acquired", "post-mortem", "pivot", and check
Product Hunt and Hacker News launch posts from past years for products that
no longer resolve. For each, say why it failed if the reason is on record,
and whether that reason still holds.

Part two, the economics. Who is the buyer, what do they actually pay, and
can that segment pay at all. Find real contract values, published pricing,
or disclosed revenue, not market-sizing reports. Assess whether the segment
that wants this is the same segment that can afford it; these are often
different, and that gap kills products.

The question is whether this is a viable business, not whether it is
technically possible.
```

## Thread 4: commodity floor

FILENAME: `commodity-floor`

```
Research how much of this idea is already available free or bundled: {IDEA}

Entity type: {TYPE}

Cover: what a competent frontier model with web search already does unaided
(describe what you would get from pasting the idea's core task into a
current frontier model); open source projects that cover part of it, with
stars and last commit; features inside subscriptions the target user
probably already pays for (office suites, cloud consoles, IDEs, CRMs,
whatever fits the segment).

Be concrete about the fraction. If free tooling does most of it, say what
percentage and what the remaining delta is. The remaining delta is the only
thing that could be sold.
```

## Label definitions

```
- Open: no occupant covers the core of the idea; the commodity floor leaves
  a real delta; the graveyard is empty or failed for reasons that no longer
  hold.
- Crowded: several occupants cover most of it; a wedge exists but incumbents
  are close; the economics are plausible for a narrowed segment.
- Saturated: direct occupants with published pricing, an incumbent already
  bundling it, or a graveyard showing the segment cannot pay.
```

## Readers

Launch the three readers in parallel after the four research threads
finish. Give each reader only its own prompt and the four notes. Do not
give it the other readers' output or any draft of the synthesis.

The three readers ask the same question in different words and see the
notes in a different order. That is deliberate: a label that survives all
three did not depend on phrasing or on which thread was read first, and a
label that does not survive is exactly the instability the report should
show. Keep the wording differences; do not collapse them into one template.

## Reader 1

Notes order: prior-art, incumbents, graveyard-economics, commodity-floor

```
Read these four research notes and nothing else:
{NOTES}

They describe the landscape around this idea: {IDEA}

Label the landscape with exactly one of these:
{LABEL_DEFINITIONS}

Reply with the label alone on the first line, then at most three sentences
giving the evidence that decided it. Do not hedge between labels.
```

## Reader 2

Notes order: commodity-floor, graveyard-economics, incumbents, prior-art

```
Someone is considering building this: {IDEA}

Four researchers looked into the space around it. Their notes follow. Use
only what is in them.
{NOTES}

Decide how occupied this space is. Choose exactly one label:
{LABEL_DEFINITIONS}

Put the label alone on the first line. Then, in at most three sentences,
name the evidence that settled it. Commit to one label; do not hedge.
```

## Reader 3

Notes order: graveyard-economics, prior-art, commodity-floor, incumbents

```
Below are four sets of research notes on one idea. Base your answer only on
them.
{NOTES}

The idea: {IDEA}

Which of these three labels fits the landscape the notes describe? Pick
exactly one:
{LABEL_DEFINITIONS}

First line: the label and nothing else. After it, at most three sentences
on the evidence that decided it. Do not split the difference between labels.
```

## Synthesis rules

```
Write the report from the full research notes, not from any shorter summary
of them. Do not research further.

Do not output a will-work or won't-work verdict. Report evidence, and the
conditions under which the idea survives. The one exception is the section
called "The roast", which is deliberately one-sided and is labelled as
such; keep its tone out of every other section.

Report all three reader labels verbatim, with their reasoning. If they
disagree, say which evidence each reader weighted and leave the
disagreement visible. Do not average, and do not pick a winner.

Do not add a critic, red-team or debate pass.

Mark vendor claims as such. Keep "found nothing, which is not the same as
absent" wherever a thread said it, with what was not checked.
```

## Report format

```
Begin with YAML front matter, so later runs can match against the report
without reading the body:

---
idea: <one-line statement of the idea>
slug: <kebab-case-name>
date: <YYYY-MM-DD>
label: <Open | Crowded | Saturated | Split>
label_reads: [<read1>, <read2>, <read3>]
top_occupants: [<name1>, <name2>, <name3>]
---

Set label to the read that appears at least twice, or to Split if none
does. The front matter is a lookup key; the body is where any disagreement
is shown.

Then a level-one heading with a short name for the report, then these
level-two sections, in this order:

1. The idea, as understood. One paragraph. The user checks this first.
2. Who is already there. Named, with URLs, pricing where published, and how
   close each is to the idea. Mark vendor claims as such.
3. The graveyard. What failed and why.
4. The economics. Who pays, how much, and whether the segment can pay.
5. The commodity floor. What is already free or bundled.
6. Landscape label. All three reads, with any disagreement shown.
7. What would have to be true. The specific conditions under which the idea
   survives, and for each, what evidence would settle it. Mark any
   condition the research already falsified.
8. The roast. Open with this line in italics: "One-sided on purpose. This
   is the case against, at full volume, not the verdict." Then explain why
   this idea is fucking stupid, in at most 300 words. Be goddamn critical.
   Take the least charitable reading the evidence allows and commit to it.
   Go after every weak point the research exposed, not just the biggest
   one, and say plainly how each one kills the idea. No hedging, no "to be
   fair", no "that said", no compliment sandwich, no silver lining, and no
   consolation at the end; the last sentence should be the harshest. Swear
   freely. Be funny, but if you have to choose between funny and brutal,
   choose brutal. Every punch must land on something the research actually
   found: the dead company that already tried exactly this, the incumbent
   giving it away free, the buyer who cannot pay, the 80 percent a chatbot
   already does. Use the real names and numbers from the notes; a specific
   insult beats a generic one. Roast the idea, never the person who had
   it. If the landscape reads came back Open, roast it anyway with whatever
   the graveyard, economics and commodity floor turned up.
9. Sources, and sources discarded. Every cited URL, then the discarded
   sources from all four threads with a one-phrase reason each.

Keep the body under 1,500 words. Prose by default; a table only where
comparison is genuinely needed (for example several occupants with
pricing). No em dashes anywhere.
```

## Conversation summary

```
At most 150 words: the landscape label and whether the three reads agreed,
the two or three closest occupants, and the single most decisive finding.
End with the single harshest line from the roast, quoted.
```
