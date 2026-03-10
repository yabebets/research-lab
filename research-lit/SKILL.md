---
name: research-lit
description: Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", "what does this paper say", or needs to understand academic papers.
argument-hint: [paper-topic-or-url]
allowed-tools: Bash(*), Read, WebSearch, WebFetch, Write, Agent
---

# Research Literature Review

Research topic: $ARGUMENTS

## Workflow

### Step 1: Search
- Use WebSearch to find recent papers on the topic
- Check arXiv, Semantic Scholar, Google Scholar
- Focus on papers from last 2 years unless studying foundational work

### Step 2: Analyze Each Paper
For each relevant paper, extract:
- **Problem**: What gap does it address?
- **Method**: Core technical contribution (1-2 sentences)
- **Results**: Key numbers/claims
- **Relevance**: How does it relate to our work?

### Step 3: Synthesize
- Group papers by approach/theme
- Identify consensus vs disagreements in the field
- Find gaps that our work could fill

### Step 4: Output
Present as a structured literature table:

```
| Paper | Venue | Method | Key Result | Relevance to Us |
|-------|-------|--------|------------|-----------------|
```

Plus a narrative summary of the landscape (3-5 paragraphs).

### Step 5: Save (if requested)
- Save paper PDFs to `literature/` or `papers/`
- Update related work notes in project memory

## Key Rules
- Always include paper citations (authors, year, venue)
- Distinguish between peer-reviewed and preprints
- Be honest about limitations of each paper
- Note if a paper directly competes with or supports our approach
