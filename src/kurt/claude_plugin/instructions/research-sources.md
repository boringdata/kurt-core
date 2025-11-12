# RESEARCH-SOURCES.md

## When to use this instruction
Deep source analysis using LLM-powered extraction during writing or project planning.

Use this instruction when:
- Need to extract specific information from sources (claims, entities, takeaways)
- Performing competitive analysis from competitor documentation
- Assessing content gaps during project planning
- User explicitly asks for deep analysis of source materials

**Decision: Quick read vs. deep extraction**
- "What does this doc say about X?" → Just read the file directly
- "Extract all claims about X from these docs" → Use extraction (this instruction)
- "What topics are we missing?" → Use gap analysis (this instruction)

---

## Available Commands

### Extract Claims
Pull verifiable factual claims with evidence and confidence levels.

```bash
kurt content extract claims <doc-id> --focus-area "performance"
```

Use for: Fact-checking, building citations, competitive claims analysis

### Extract Entities
Identify and categorize named entities (products, technologies, concepts).

```bash
kurt content extract entities <doc-id> --types "product_feature,technology"
```

Use for: Understanding key concepts, building glossaries, identifying technologies

### Extract Takeaways
Summarize key points and main insights.

```bash
kurt content extract takeaways <doc-id> --max 5
```

Use for: Summarizing long documents, identifying main points

### Extract Competitive Info
Extract competitive differentiation points.

```bash
kurt content extract competitive <doc-id> \
  --our-product "Our Platform" \
  --their-product "Competitor X"
```

Use for: Building competitive comparisons, migration guides

### Batch Extraction
Extract from multiple documents at once.

```bash
# Extract claims from 5 competitor docs
kurt content extract claims <doc-id-1> <doc-id-2> <doc-id-3> \
  --focus-area "performance"
```

---

## Gap Analysis (During Planning)

### Identify Content Gaps
Find missing or shallow topics in content collection.

```bash
kurt content gaps analyze \
  --topics "authentication,webhooks,rate-limiting" \
  --audience "developers"
```

Returns: List of gaps (missing, shallow, outdated, inconsistent, fragmented) with priority

### Analyze Topic Coverage
Score coverage depth for specific topics (1-10 scale).

```bash
kurt content gaps coverage \
  --topics "API authentication,webhooks,rate limiting"
```

Returns: Coverage scores with covered/missing aspects and recommendations

### Generate Content Suggestions
Get specific, actionable content ideas to address gaps.

```bash
kurt content gaps suggest \
  --topics "webhooks,auth" \
  --max 5
```

Returns: Suggested content titles with descriptions and rationale

---

## Cost Considerations

**Extraction and gap analysis use LLM calls** - Be intentional about when to use:
- Extract during writing when you actually need the data (not upfront)
- Use gap analysis during planning, not repeatedly
- Consider reading files directly for simple questions

**When to extract vs. read**:
- Extract: Need structured data, multiple sources, fact-checking, citations
- Read: General understanding, checking relevance, quick context
