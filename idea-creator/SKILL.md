---
name: idea-creator
description: Generate and rank research ideas given a broad direction. Use when user says "找idea", "brainstorm ideas", "generate research ideas", "what can we work on", or wants to explore a research area for publishable directions.
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Grep, Glob, WebSearch, WebFetch, Agent, mcp__codex__codex, mcp__codex__codex-reply, mcp__gemini__chat, mcp__gemini__googleSearch
---

# Research Idea Creator

Generate publishable research ideas for: $ARGUMENTS

## Overview

Given a broad research direction from the user, systematically generate, validate, and rank concrete research ideas. This skill composes with `/research-lit`, `/novelty-check`, and `/research-review` to form a complete idea discovery pipeline.

## Workflow

### Phase 1: Landscape Survey (5-10 min)

Map the research area to understand what exists and where the gaps are.

1. **Search recent literature** using WebSearch / `mcp__gemini__googleSearch`:
   - Top venues in the last 2 years (NeurIPS, ICML, ICLR, ACL, EMNLP, etc.)
   - Recent arXiv preprints (last 6 months)
   - Use 5+ different query formulations
   - Read abstracts and introductions of the top 10-15 papers

2. **Build a landscape map**:
   - Group papers by sub-direction / approach
   - Identify what has been tried and what hasn't
   - Note recurring limitations mentioned in "Future Work" sections
   - Flag any open problems explicitly stated by multiple papers

3. **Identify structural gaps**:
   - Methods that work in domain A but haven't been tried in domain B
   - Contradictory findings between papers (opportunity for resolution)
   - Assumptions that everyone makes but nobody has tested
   - Scaling regimes that haven't been explored
   - Diagnostic questions that nobody has asked

### Phase 2: Idea Generation (brainstorm with external LLM)

Use GPT-5.4 via Codex MCP for divergent thinking:

```
mcp__codex__codex:
  model: gpt-5.4
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    You are a senior ML researcher brainstorming research ideas.

    Research direction: [user's direction]

    Here is the current landscape:
    [paste landscape map from Phase 1]

    Key gaps identified:
    [paste gaps from Phase 1]

    Generate 8-12 concrete research ideas. For each idea:
    1. One-sentence summary
    2. Core hypothesis (what you expect to find and why)
    3. Minimum viable experiment (what's the cheapest way to test this?)
    4. Expected contribution type: empirical finding / new method / theoretical result / diagnostic
    5. Risk level: LOW (likely works) / MEDIUM (50-50) / HIGH (speculative)
    6. Estimated effort: days / weeks / months

    Prioritize ideas that are:
    - Testable with moderate compute (8x RTX 3090 or less)
    - Likely to produce a clear positive OR negative result (both are publishable)
    - Not "apply X to Y" unless the application reveals genuinely surprising insights
    - Differentiated from the 10-15 papers above

    Be creative but grounded. A great idea is one where the answer matters regardless of which way it goes.
```

Save the threadId for follow-up.

### Phase 3: First-Pass Filtering

For each generated idea, quickly evaluate:

1. **Feasibility check**: Can we actually run this experiment with available resources?
   - Compute requirements (estimate GPU-hours)
   - Data availability
   - Implementation complexity
   - Skip ideas requiring > 1 week of GPU time or unavailable datasets

2. **Novelty quick-check**: For each idea, do 2-3 targeted searches to see if it's already been done. Full `/novelty-check` comes later for survivors.

3. **Impact estimation**: Would a reviewer care about the result?
   - "So what?" test: if the experiment succeeds, does it change how people think?
   - Is the finding actionable or just interesting?

Eliminate ideas that fail any of these. Typically 8-12 ideas reduce to 4-6.

### Phase 4: Deep Validation (for top ideas)

For each surviving idea, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + GPT-5.4 cross-verification) for each idea

2. **Critical review**: Use GPT-5.4 via `mcp__codex__codex-reply` (same thread):
   ```
   Here are our top ideas after filtering:
   [paste surviving ideas with novelty check results]

   For each, play devil's advocate:
   - What's the strongest objection a reviewer would raise?
   - What's the most likely failure mode?
   - How would you rank these for a top venue submission?
   - Which 2-3 would you actually work on?
   ```

3. **Combine rankings**: Merge your assessment with GPT-5.4's ranking.

### Phase 5: Output — Ranked Idea Report

Write a structured report to `IDEA_REPORT.md` in the project root:

```markdown
# Research Idea Report

**Direction**: [user's research direction]
**Generated**: [date]
**Ideas evaluated**: X generated → Y survived filtering → Z recommended

## Landscape Summary
[3-5 paragraphs on the current state of the field]

## Recommended Ideas (ranked)

### Idea 1: [title]
- **Hypothesis**: [one sentence]
- **Minimum experiment**: [concrete description]
- **Expected outcome**: [what success/failure looks like]
- **Novelty**: X/10 — closest work: [paper]
- **Feasibility**: [compute, data, implementation estimates]
- **Risk**: LOW/MEDIUM/HIGH
- **Contribution type**: empirical / method / theory / diagnostic
- **Reviewer's likely objection**: [strongest counterargument]
- **Why we should do this**: [1-2 sentences]

### Idea 2: [title]
...

## Eliminated Ideas (for reference)
| Idea | Reason eliminated |
|------|-------------------|
| ... | Already done by [paper] |
| ... | Requires > 1 week GPU time |
| ... | Result wouldn't be interesting either way |

## Suggested Execution Order
1. Start with Idea X (lowest risk, fastest to validate)
2. If X works, extend to Idea Y
3. Idea Z is high-risk high-reward — run in parallel if GPUs available

## Next Steps
- [ ] Implement Idea 1 baseline
- [ ] Run pilot experiment
- [ ] If promising, invoke /auto-review-loop for full iteration
```

## Key Rules

- The user provides a DIRECTION, not an idea. Your job is to generate the ideas.
- Quantity first, quality second: brainstorm broadly, then filter ruthlessly.
- A good negative result is just as publishable as a positive one. Prioritize ideas where the answer matters regardless of direction.
- Don't fall in love with any idea before validating it. Be willing to kill ideas.
- Always estimate compute cost. An idea that needs 1000 GPU-hours is not actionable for most researchers.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated ideas in the report — they save future time by documenting dead ends.
- If the user's direction is too broad, ask them to narrow it before proceeding.

## Composing with Other Skills

After this skill produces the ranked report:
```
/idea-creator "direction"     → ranked ideas
/novelty-check "top idea"     → deep novelty verification (already done in Phase 4, but user can re-run)
/research-review "top idea"   → external critical feedback
implement                     → write code
/run-experiment               → deploy to GPU
/auto-review-loop             → iterate until submission-ready
```
