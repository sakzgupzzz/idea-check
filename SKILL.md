---
name: idea-check
description: Validate a product or startup idea end to end and return a research-backed landscape report covering prior art, adjacent incumbents, the graveyard of failed attempts, buyer economics, and the commodity floor. Use this whenever the user asks whether an idea already exists, whether an idea is taken, whether an idea will work, whether anyone has built something, or asks for competitive, prior-art, or market landscape research on something they are thinking of building. Trigger even if they phrase it casually ("has anyone done X", "is this a thing", "am I crazy or is there a market for X") and even if they only describe the idea without asking a question.
---

# idea-check

Research an idea end to end and return a landscape report. Do not return a
verdict on whether the idea will work. Return evidence, and the conditions
under which the idea survives.

## Before launching

Restate the idea in one paragraph as you understood it, and tell the user
you are starting research. Do not wait for confirmation; the restatement
goes in the report too, so the user can catch a misread either way. Ask one
question first only if the ambiguity changes which market you would research
(for example "AI for lawyers" could mean contract review or litigation
discovery, and those have different incumbents and graveyards).

Pick the entity type: software product, hardware product, service, research
direction, or content. This changes which sources matter. Software leans on
package registries and GitHub; hardware leans on patents; services lean on
local market and labor data; research leans on papers and preprints.

Then check prior runs. List `checks/` in the skill directory and read the
metadata of any file whose subject looks related: the comment on the first
lines of an `.html` report, or the YAML front matter of an older `.md` one. If a previous check
covers overlapping ground, say so up front and name the file, then decide
with the user whether to run fresh research or extend the earlier report.
Repeating a check you already ran is the most common waste in this workflow.
(`examples/` holds published sample reports, not the user's own checks; do
not match against it.)

Create a notes directory in the scratchpad for this run. Each thread writes
its findings there so the synthesis works from files, not from memory of
four long subagent replies.

## The four threads

Launch all four as parallel subagents in a single message, using the Agent
tool with the general-purpose type. Each thread needs web search and fetch.
The decomposition is fixed. Do not substitute your own, merge threads, or
add a fifth.

Every prompt this skill sends is in `references/thread-prompts.md`. Read
that file now and use its fenced blocks as written. A research prompt is
the thread's template, then the "Shared block", then "Output instruction:
skill", with the idea, entity type, notes directory and filename
substituted. The summaries below say what each thread is for; they are not
the prompts.

### 1. Prior art
Who already ships this. Commercial products with pricing where published,
GitHub repos with stars, license and last commit date, academic work,
patents. For each occupant, state how close it is to the idea and what it
does not cover. The gaps are more useful than the list.

### 2. Adjacent incumbents
Which established categories already solve this as a feature, and who would
absorb it if it worked. This matters more than direct competitors. Products
in this space more often die to an incumbent bundling the feature from above
than to a startup competing head on. Name the most likely absorber. Once the
absorber is named, the thread audits its GitHub orgs and changelog
directly, because platform vendors name feature-level tools in their own
vocabulary, not the idea's.

### 3. Graveyard and economics
What has already been tried here and failed: shutdowns, acquisitions at low
value, pivots, layoffs, decline in adjacent public companies. Then who the
buyer is, what they actually pay, and whether that segment can pay at all.
Be adversarial toward the business case. A thread briefed to find
competitors will never find the graveyard, which is why this is separate.

### 4. Commodity floor
How much of this is already free or bundled: frontier model capabilities,
open source, features inside subscriptions the user already has. If a
competent model with web search does 80 percent of it for free, say so and
name the remaining delta, because the delta is the only thing sellable.

## Mandatory subagent instructions

Every thread prompt must include the "Shared block" from
`references/thread-prompts.md` verbatim. Do not trim, paraphrase or reorder
it when assembling a prompt. It tells each thread to assume prior art
exists and hunt for it, to write "found nothing, which is not the same as
absent" and list what it did not check, to give a source URL for every
claim, to exclude and name SEO-grade sources, and to separate vendor claims
from independent evidence.

Its first line is the highest-value line in this skill. Framing a research
task toward confirmation rather than falsification shifts conclusions by 34
to 66 percentage points in published measurements. That makes the framing a
correctness requirement, not a tone preference. A thread told to check
whether a space is empty will report it empty.

The "found nothing" phrase exists because absence of evidence is weak here.
Small competitors and dead companies are both poorly indexed. Listing what
was not checked lets the reader judge how much the silence means.

## Synthesis

When all four threads return, read their notes files. Then do two things.

### Three independent landscape reads

Label the landscape Open, Crowded, or Saturated. Produce that label three
times independently, and keep the reads actually independent: launch three
parallel subagents, one each from the "Reader 1", "Reader 2" and "Reader
3" templates in `references/thread-prompts.md`, with the "Label
definitions" block substituted in and the four notes file paths listed in
the order that reader's heading gives. Each reader gets one label and at
most three sentences of reasoning. Do not give them each other's output or
your own draft. Do not produce the label yourself in your own context and
then "re-derive" it, because a second read in the same context is anchored
on the first.

The three templates word the question differently and order the notes
differently, on purpose. Three copies of one prompt differ only by
sampling noise; three phrasings test whether the label depends on how it
was asked, which is the failure this step exists to expose. Use all three
as written.

Report all three labels and show any disagreement. Do not average, and do
not pick a winner by majority in the prose; let the reader see the split.
Benchmarked novelty verdicts swing from 93.5 to 40.9 percent accuracy on
prompt rewording alone, and a three-call vote outperformed purpose-built
single-pass tools costing twelve times more. Disagreement between the reads
is the single most informative line in the report.

### No critic layer

Do not add a critic, red-team, or debate agent over the synthesis. Published
results show multi-agent debate underperforms a single strong pass and
degrades accuracy in most configurations tested. One careful synthesis from
the notes files beats a committee. Follow the "Synthesis rules" block in
`references/thread-prompts.md`.

## Output

The report is an HTML page, not a markdown file. It is saved, published
when the session can publish, and summarised in the conversation.

### 1. The report page, always

Write the full report to `checks/YYYY-MM-DD-<slug>.html` in the skill
directory, where `<slug>` is a short kebab-case name for the idea. Create
`checks/` if it does not exist, and if that name is already taken today,
append `-2`, `-3` and so on rather than overwrite the earlier report.
`checks/` is git-ignored, because an idea being checked is usually private;
leave it that way.

Build the page from `references/report-template.html`, which carries all
the CSS and the header. Fill its slots as the "Report page" section of
`references/thread-prompts.md` describes, and write the content to the
"Report format" block exactly: a metadata block (idea, title, slug, date,
label, the three label reads, top occupants) that later runs match against
without reading the body, then nine HTML sections in a fixed order, under
1,500 words, no em dashes. Do not write a `.md` report, and do not add or
change CSS; every report should look like the same publication.

Section 8 is the roast: up to 300 words on why the idea is stupid. Be
properly critical: least charitable reading, every weak point, no hedging,
no silver lining, profanity welcome. Write it yourself during
synthesis; it is not a critic agent and does not change any other section.
It is the one place the report takes a side, it says so in its first line,
and every jab in it must rest on a finding from the notes. Aim it at the
idea, not at the user.

### 2. The published artifact, whenever the session can publish

If the session has a tool for publishing an artifact or page, publish the
`.html` file with it as soon as it is written and give the user the link.
This is how the report is meant to be read. The template is already in
the form an artifact page takes, so publish the file as it is. Use the
report's `title` as the page title. Published artifacts are private until
the user shares them, so publish without asking.

If no such tool exists, do not fail the run and do not fall back to
markdown. The saved `.html` file is the report; tell the user it opens in
any browser.

### 3. The conversation summary, always

Print the summary described in the "Conversation summary" block of
`references/thread-prompts.md`, then the artifact link if there is one and
the path to the saved file. Nobody reads 1,500 words in a terminal.

## Known limits

State these in the report when they apply.

- Absence of evidence is weak evidence here. Small competitors and dead
  companies are both poorly indexed.
- Pricing for enterprise tools is usually sales-gated and unavailable.
- Volume of search results is not evidence of market size; much of it is
  vendors writing about each other.
- The report says whether a space is occupied. It does not say whether this
  user can win, which depends on information the research cannot see.
- Feature-level tools from platform vendors are named in the vendor's
  vocabulary and are missed by idea-keyword search. The absorber audit
  reduces this but does not remove it.
