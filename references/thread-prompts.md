# Subagent prompt templates

Four research templates and one reader template. Launch the four research
threads in parallel in one message. Substitute `{IDEA}` with the restated
one-paragraph version of the user's idea, `{TYPE}` with the entity type
(software product, hardware product, service, research direction, content),
and `{NOTES_DIR}` with the scratchpad notes directory for this run.

Every research template ends with the shared block. Do not omit or trim it.

## Shared block, appended to all four research threads

```
Assume prior art exists and hunt for it. Your job is to find who occupies
this space, not to confirm it is empty. Report who occupies this space,
bluntly.

Where you find nothing, write "found nothing, which is not the same as
absent" and list what you did not check.

Every factual claim needs a source URL.

Exclude AI-generated listicles, "best tools 2026" roundup pages,
programmatic pricing sites, and syndicated market-sizing sellers from all
factual claims. Name the sources you discarded, with a one-phrase reason
each. Roughly a third of search results in this domain are vendors writing
SEO about each other. Report that volume as a finding of its own, but do not
cite any of it.

Distinguish vendor claims from independent evidence in every finding. Label
each finding "vendor claim" or "independent" and say what the independent
evidence is (a user review, a filing, a repo, a paper, press coverage that
is not a rewritten press release).

Use web search and fetch. Prefer primary sources: the product's own pricing
page for pricing, the GitHub repo page for stars and last commit, Google
Patents or USPTO for patents, arXiv or a journal for papers, Crunchbase or
press for shutdowns and acquisitions.

Write your full findings to {NOTES_DIR}/{FILENAME}.md in markdown, with a
"Findings", "Found nothing" (if any), "Discarded sources", and "Not checked"
section. Then reply with a summary under 200 words.
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

## Reader template: independent landscape read

Launch three of these in parallel after the four research threads finish.
Give each reader only the four notes files and this prompt. Do not give it
the other readers' output or any draft of the synthesis.

```
Read these four research notes files and nothing else:
{NOTES_DIR}/prior-art.md
{NOTES_DIR}/incumbents.md
{NOTES_DIR}/graveyard-economics.md
{NOTES_DIR}/commodity-floor.md

They describe the landscape around this idea: {IDEA}

Label the landscape with exactly one of these:
- Open: no occupant covers the core of the idea; the commodity floor leaves
  a real delta; the graveyard is empty or failed for reasons that no longer
  hold.
- Crowded: several occupants cover most of it; a wedge exists but incumbents
  are close; the economics are plausible for a narrowed segment.
- Saturated: direct occupants with published pricing, an incumbent already
  bundling it, or a graveyard showing the segment cannot pay.

Reply with the label on the first line, then at most three sentences giving
the evidence that decided it. Do not hedge between labels.
```

## Synthesis notes

Write the report from the notes files, not from the subagent summaries.
Report all three reader labels verbatim, with their reasoning. If they
disagree, say which evidence each reader weighted and leave the
disagreement visible. Do not add a critic pass.
