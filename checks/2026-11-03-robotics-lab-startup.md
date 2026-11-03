---
idea: A venture-backed robotics lab building general-purpose robot learning plus the teleop data, simulation, evaluation and shared-lab infrastructure around it, used in-house or sold to other robotics companies
slug: robotics-lab-startup
date: 2026-11-03
label: Saturated
label_reads: [Saturated, Saturated, Saturated]
top_occupants: [Physical Intelligence, NVIDIA Isaac GR00T, Scale AI]
---

# Robotics lab startup: landscape check

## The idea, as understood

A startup organized as a research lab, in the mold of Physical Intelligence or Skild, that trains general-purpose robot policies (vision-language-action models, humanoid or mobile manipulation) and builds the infrastructure around them: teleoperation data collection, simulation, policy evaluation, and physical lab space, used in-house and possibly sold to other robotics companies. Researched as a category, since the request named no specific wedge.

## Who is already there

Every sub-segment has a funded occupant, and the bundle itself is already being assembled by corporate parents.

| Layer | Occupant | Evidence |
|---|---|---|
| Robot foundation model lab | Physical Intelligence ($600M at $5.6B, reported talks at $11B+), Skild AI (reported $1.4B at $14B+), Generalist ($400M), Figure ($1B+ at $39B) | Bloomberg, trade press, company releases |
| Open model and sim stack | NVIDIA GR00T N1.7 (open weights), Isaac Sim and Lab (free for internal R&D), Lab-Arena eval, Isaac Teleop | NVIDIA pages, GitHub |
| Open training framework | Hugging Face LeRobot (28.7k stars), openpi (14.5k stars, Apache-2.0) | GitHub API |
| Teleop data as a service | Scale AI (claims 100k+ hours, customers PI, Generalist, Dyna), XDOF ($70M raise, ~$50M ARR per TechCrunch), Mecka, Sensei, Ropedia | Scale page (vendor), TechCrunch (independent) |
| Humanoid hardware | Unitree G1 at $13.5K list, 5,500+ humanoids shipped in 2025, 60% gross margin, IPO filed; 1X NEO $20,000 or $499/mo | Unitree pricing page, Caixin, 1X order page |
| Shared lab space | MassRobotics (nonprofit), Circuit Launch ($275 to $1,200+/mo) | Vendor pages |

The model labs are the same thing. XDOF is closest to the "sell infrastructure to other labs" half. No single company bundles model, humanoid, data business and shared lab; the likely reason is that the buyers of robot data are the labs themselves, so a seller would supply its own competitors. Pricing for PI, Skild, Generalist, XDOF and Scale is unpublished.

Google DeepMind and Hyundai are assembling the lab-plus-body-plus-facility bundle at corporate scale. NVIDIA gives the infrastructure layer away to sell GPUs. AWS RoboMaker, the one cloud attempt to sell robotics infrastructure, shut down in September 2025.

## The graveyard

The pattern across fifteen years is consistent, and every entry is independently sourced.

- **Everyday Robots** (Alphabet, closed 2023): the exact shape of this idea, shut after about seven years with no product. An ex-employee told Wired the team "couldn't decide if they were aiming for an advanced research project or a commercially viable product."
- **Vicarious** ($250M raised): acquihired by Intrinsic, undisclosed sum. Intrinsic then lost its independence inside Google in 2026 with no disclosed revenue.
- **Covariant** ($222M raised): ended as an Amazon reverse acquihire, reportedly below its last valuation. Its one buyer also builds its own robots.
- **Kindred**: teleop plus learning, absorbed by Ocado, a customer that builds its own robots.
- **OpenAI robotics**: disbanded in 2021 over data scarcity, restarted as a model supplier to Figure, 1X and PI.
- **Public comparables**: Sarcos pivoted to software and still loses about $32M a year per its 10-K. Berkshire Grey went from a $2.2B SPAC to a $375M take-private.

No independent robot-learning lab with a disclosed, recurring, arm's-length model or data license to a non-competing OEM was found.

## The economics

The hard prices belong to incumbents. Unitree sells humanoids at $13.5K with a 60% gross margin and no model budget to recover. Agility's illustrative robots-as-a-service price is about $8,500 a month against a $125K bill of materials, which by the S-4's own assumptions needs roughly two full shifts of uptime to reach labor parity. The one buyer on record, GXO's CEO, said on the Q2 2026 call that 45 humanoid pilots have produced no ROI. Figure's BMW "fleet" was one robot off-shift per BMW's own spokesperson.

On data, Figure plans to spend about $1B in a year on human data capture, so a startup selling data competes with the in-house collection of its own largest buyers. Teleop wage rates and vendor rate cards were not reachable. The segment that wants this (model labs) builds in-house; the segment that could pay for deployed robots reports no return yet.

## The commodity floor

Roughly 80 to 90 percent of the stack is free. Policies: openpi, GR00T N1.7 and about fifteen VLAs inside LeRobot. Data: Open X-Embodiment, DROID, AgiBot World (1M trajectories). Simulation: MuJoCo, Genesis, Isaac Sim free for internal commercial R&D. Hardware: SO-101 arm at a $230 bill of materials.

The sellable delta is embodiment-matched proprietary data, a model that beats open baselines on real tasks, and third-party real-robot evaluation as a service. The first two are what the funded labs spend billions on. For the third the threads found nothing, which is not the same as absent; only academic RoboArena and an XDOF add-on surfaced, and Scale's eval offering was not checked.

## Landscape label

Three independent reads, each from the four notes files only:

- **Read 1: Saturated.** Direct occupants at nine and ten figures, infrastructure bundled free by NVIDIA and Hugging Face, graveyard shows the segment cannot pay.
- **Read 2: Saturated.** Same, adding that the only unoccupied slivers (priced eval-as-a-service, a robot-learning shared lab) are academic or nonprofit today.
- **Read 3: Saturated.** Same, adding that no arm's-length recurring license to a non-competing OEM was found.

No disagreement.

## What would have to be true

1. **A buyer exists who is not also a competitor.** Settled by one signed, recurring, disclosed model or data contract with an OEM that has no in-house learning team. None found in fifteen years of comparables.
2. **Deployed robots return money to someone.** Settled by a 3PL or automaker disclosing ROI on a humanoid fleet. GXO's statement points the other way as of August 2026.
3. **Proprietary data beats open data by enough to pay for collection.** Settled by a head-to-head on a customer task against GR00T N1.7 or pi0.5 fine-tuned on open data.
4. **Eval-as-a-service is a real business.** The one sliver nobody has priced. Settled by three labs paying for blind real-robot evaluation. Cheap to test with letters of intent.
5. **The lab stays independent long enough to matter.** Every comparable was absorbed or shut; the pattern falsifies this unless there is revenue from day one.

Limits: all four threads exhausted the search budget, several vendor pages were rate-limited, and Chinese state training facilities and Agility, Tesla and Apptronik contracts were not checked.

## Sources, and sources discarded

Cited: pi.website; Bloomberg Law (PI round); SiliconANGLE (Skild, Generalist); figure.ai; GitHub API for lerobot, openpi, Isaac-GR00T, Genesis, SO-ARM100; nvidia.com Isaac GR00T; deepmind.google; scale.com/robotics; techcrunch.com (XDOF, Intrinsic); fortune.com (Mecka, Figure/BMW); unitree.com/g1; caixinglobal.com; 1x.tech; circuitlaunch.com; massrobotics.org; therobotreport.com (Everyday Robots, RoboMaker, Atlas); geekwire.com (Covariant); venturebeat.com; sec.gov Palladyne 10-K; spacinsider.com; dynamo.vc (Agility S-4); beri.net (GXO call); Isaac Sim license FAQ; arXiv 2410.24164, 2503.14734, 2310.08864, 2403.12945, 2506.18123. Full URLs are in the four notes files.

Discarded, roughly a third to 45 percent of about 500 result links: programmatic funding trackers (dealroom mirrors, defillama, getlatka, seedtable), AI-rewritten aggregators (pulse.bot, getcoai, hyper.ai, runtimewire), vendor listicles (labellerr), Wikipedia mirrors, syndicated rewrites of Wired and Business Insider stories, pricing sites (usagepricing, thepricer), and blogs restating Figure and Agility claims.
