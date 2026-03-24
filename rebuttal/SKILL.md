---
name: rebuttal
description: "Workflow 4: Submission rebuttal pipeline. Parses external reviews, enforces coverage and grounding, drafts a safe text-only rebuttal under venue limits, and manages follow-up rounds. Use when user says \"rebuttal\", \"reply to reviewers\", \"ICML rebuttal\", \"OpenReview response\", or wants to answer external reviews safely."
argument-hint: [paper-path-or-review-bundle]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# Workflow 4: Rebuttal

Prepare and maintain a grounded, venue-compliant rebuttal for: **$ARGUMENTS**

## Scope

This skill is optimized for:
- ICML-style **text-only rebuttal**
- strict **character limits**
- **multiple reviewers**
- **follow-up rounds** after the initial rebuttal
- safe drafting with **no fabrication**, **no overpromise**, and **full issue coverage**

This skill does **not**:
- run new experiments automatically
- generate new theorem claims automatically
- edit or upload a revised PDF
- submit to OpenReview / CMT / HotCRP

If the user already has new results, derivations, or approved commitments, the skill can incorporate them as **user-confirmed evidence**.

## Lifecycle Position

```text
Workflow 1:   idea-discovery
Workflow 1.5: experiment-bridge
Workflow 2:   auto-review-loop (pre-submission)
Workflow 3:   paper-writing
Workflow 4:   rebuttal (post-submission external reviews)
```

## Constants

- **VENUE = `ICML`** — Default venue. Override if needed.
- **RESPONSE_MODE = `TEXT_ONLY`** — v1 default.
- **REVIEWER_MODEL = `gpt-5.4`** — Used via Codex MCP for internal stress-testing.
- **MAX_INTERNAL_DRAFT_ROUNDS = 2** — draft → lint → revise.
- **MAX_STRESS_TEST_ROUNDS = 1** — One Codex MCP critique round.
- **MAX_FOLLOWUP_ROUNDS = 3** — per reviewer thread.
- **REBUTTAL_DIR = `rebuttal/`**

> Override: `/rebuttal "paper/" — venue: NeurIPS, character limit: 5000`

## Required Inputs

1. **Paper source** — PDF, LaTeX directory, or narrative summary
2. **Raw reviews** — pasted text, markdown, or PDF with reviewer IDs
3. **Venue rules** — venue name, character/word limit, text-only or revised PDF allowed
4. **Current stage** — initial rebuttal or follow-up round

If venue rules or limit are missing, **stop and ask** before drafting.

## Safety Model

Three hard gates — if any fails, do NOT finalize:

1. **Provenance gate** — every factual statement maps to: `paper`, `review`, `user_confirmed_result`, `user_confirmed_derivation`, or `future_work`. No source = blocked.
2. **Commitment gate** — every promise maps to: `already_done`, `approved_for_rebuttal`, or `future_work_only`. Not approved = blocked.
3. **Coverage gate** — every reviewer concern ends in: `answered`, `deferred_intentionally`, or `needs_user_input`. No issue disappears.

## Workflow

### Phase 0: Resume or Initialize

1. If `rebuttal/REBUTTAL_STATE.md` exists → resume from recorded phase
2. Otherwise → create `rebuttal/`, initialize all output documents
3. Load paper, reviews, venue rules, any user-confirmed evidence

### Phase 1: Validate Inputs and Normalize Reviews

1. Validate venue rules are explicit
2. Normalize all reviewer text into `rebuttal/REVIEWS_RAW.md` (verbatim)
3. Record metadata in `rebuttal/REBUTTAL_STATE.md`
4. If ambiguous, pause and ask

### Phase 2: Atomize and Classify Reviewer Concerns

Create `rebuttal/ISSUE_BOARD.md`.

For each atomic concern:
- `issue_id` (e.g., R1-C2)
- `reviewer`, `round`, `raw_anchor` (short quote)
- `issue_type`: assumptions / theorem_rigor / novelty / empirical_support / baseline_comparison / complexity / practical_significance / clarity / reproducibility / other
- `severity`: critical / major / minor
- `reviewer_stance`: positive / swing / negative / unknown
- `response_mode`: direct_clarification / grounded_evidence / nearest_work_delta / assumption_hierarchy / narrow_concession / future_work_boundary
- `status`: open / answered / deferred / needs_user_input

### Phase 3: Build Strategy Plan

Create `rebuttal/STRATEGY_PLAN.md`.

1. Identify 2-4 **global themes** resolving shared concerns
2. Choose **response mode** per issue
3. Build **character budget** (10-15% opener, 75-80% per-reviewer, 5-10% closing)
4. Identify **blocked claims** (ungrounded or unapproved)
5. If unresolved blockers → pause and present to user

### Phase 4: Draft Initial Rebuttal

Create `rebuttal/REBUTTAL_DRAFT_v1.md`.

Structure:
1. **Short opener** — thank reviewers + 2-4 global resolutions
2. **Per-reviewer numbered responses** — answer → evidence → implication
3. **Short closing** — resolved / remaining / acceptance case

Default reply pattern per issue:
- Sentence 1: direct answer
- Sentence 2-4: grounded evidence
- Last sentence: implication for the paper

Heuristics from 5 successful rebuttals:
- Evidence > assertion
- Global narrative first, per-reviewer detail second
- Concrete numbers for counter-intuitive points
- Name closest prior work + exact delta for novelty disputes
- Concede narrowly when reviewer is right
- For theory: separate core vs technical assumptions
- Answer friendly reviewers too

Hard rules:
- NEVER invent experiments, numbers, derivations, citations, or links
- NEVER promise what user hasn't approved
- If no strong evidence exists, say less not more

Also generate `rebuttal/PASTE_READY.txt` (plain text, exact character count).

### Phase 5: Safety Validation

Run all lints:
1. **Coverage** — every issue maps to draft anchor
2. **Provenance** — every factual sentence has source
3. **Commitment** — promises are approved
4. **Tone** — flag aggressive/submissive/evasive phrases
5. **Consistency** — no contradictions across reviewer replies
6. **Limit** — exact character count, compress if over (redundancy → friendly → opener → wording, never drop critical answers)

### Phase 6: Codex MCP Stress Test

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    Stress-test this rebuttal draft:
    [raw reviews + issue board + draft + venue rules]

    1. Unanswered or weakly answered concerns?
    2. Unsupported factual statements?
    3. Risky or unapproved promises?
    4. Tone problems?
    5. Paragraph most likely to backfire with meta-reviewer?
    6. Minimal grounded fixes only. Do NOT invent evidence.

    Verdict: safe to submit / needs revision
```

Save full response to `rebuttal/MCP_STRESS_TEST.md`. If hard safety blocker → revise before finalizing.

### Phase 7: Finalize

1. Produce `rebuttal/REBUTTAL_DRAFT_final.md`
2. Produce `rebuttal/PASTE_READY.txt` with exact character count
3. Update `rebuttal/REBUTTAL_STATE.md`
4. Present to user with count + remaining risks + lines needing manual approval

### Phase 8: Follow-Up Rounds

When new reviewer comments arrive:

1. Append verbatim to `rebuttal/FOLLOWUP_LOG.md`
2. Link to existing issues or create new ones
3. Draft **delta reply only** (not full rewrite)
4. Re-run safety lints
5. Use Codex MCP reply for continuity if useful
6. Rules: escalate technically not rhetorically; concede if reviewer is correct; stop arguing if reviewer is immovable and no new evidence exists

## Key Rules

- **Large file handling**: If Write fails, retry with Bash heredoc silently.
- **Never fabricate.** No invented evidence, numbers, derivations, citations, or links.
- **Never overpromise.** Only promise what user explicitly approved.
- **Full coverage.** Every reviewer concern tracked and accounted for.
- **Preserve raw records.** Reviews and MCP outputs stored verbatim.
- **Global + per-reviewer structure.** Shared concerns in opener.
- **Answer friendly reviewers too.** Reinforce supportive framing.
- **Meta-reviewer closing.** Summarize resolved/remaining/why accept.
- **Evidence > rhetoric.** Derivations and numbers over prose.
- **Concede selectively.** Narrow honest concessions > broad denials.
- **Don't waste space on unwinnable arguments.** Answer once, move on.
- **Respect the limit.** Character budget is a hard constraint.
- **Resume cleanly.** Continue from REBUTTAL_STATE.md on rerun.
- **Anti-hallucination citations.** Any reference added must go through DBLP → CrossRef → [VERIFY].
