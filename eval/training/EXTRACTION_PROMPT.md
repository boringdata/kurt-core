# Document Extraction Prompt

You are extracting structured knowledge from technical documentation for a knowledge graph.

## Input
- Document content (markdown)
- Existing entities (if any)

## Output Format (JSON)

```json
{
  "metadata": {
    "content_type": "TUTORIAL",
    "has_code_examples": true,
    "has_step_by_step_procedures": true,
    "has_narrative_structure": false
  },
  "entities": [...],
  "relationships": [...],
  "claims": [...]
}
```

---

## 1. METADATA

**content_type** - One of:
- `REFERENCE` - API docs, reference material
- `TUTORIAL` - Step-by-step learning
- `GUIDE` - Conceptual explanations
- `BLOG` - Blog posts, articles
- `PRODUCT_PAGE` - Product marketing
- `LANDING_PAGE` - Overview/landing pages
- `OTHER` - Doesn't fit above

**Flags:**
- `has_code_examples` - Contains code snippets
- `has_step_by_step_procedures` - Numbered/ordered instructions
- `has_narrative_structure` - Story-like flow

---

## 2. ENTITIES

Extract 5-15 named concepts with distinct identity.

**Entity Types:**
| Type | Description | Examples |
|------|-------------|----------|
| `Product` | Named software products | Tailwind CSS, Vite, Stripe |
| `Feature` | Capabilities, methods, functionalities | utility classes, webhooks, hot reload |
| `Technology` | Languages, frameworks, protocols | JavaScript, npm, CSS, HTTP |
| `Topic` | Abstract concepts | responsive design, authentication |
| `Company` | Organizations | Vercel, Stripe Inc |
| `Integration` | Product connections | Tailwind + Vite |

**Entity Schema:**
```json
{
  "name": "Tailwind CSS",
  "entity_type": "Product",
  "description": "A utility-first CSS framework for rapid UI development",
  "aliases": ["Tailwind", "TailwindCSS"],
  "confidence": 0.95,
  "quote": "Tailwind CSS works by scanning all of your HTML files"
}
```

**Rules:**
- Extract proper nouns as Products/Companies/Technologies
- Extract capabilities/methods as Features
- `quote`: Exact text (50-150 chars) where entity appears
- `confidence`: 0.7-1.0 based on prominence in doc

---

## 3. RELATIONSHIPS

Extract 5-10 connections between entities.

**Relationship Types:**
| Type | Meaning | Example |
|------|---------|---------|
| `part_of` | Component of | "Vite plugin" part_of "Vite" |
| `integrates_with` | Works together | "Tailwind" integrates_with "Vite" |
| `enables` | Makes possible | "npm" enables "package installation" |
| `depends_on` | Requires | "Tailwind" depends_on "Node.js" |
| `uses` | Utilizes | "Tailwind" uses "PostCSS" |
| `provides` | Offers | "Vite" provides "hot reload" |
| `is_a` | Type of | "Tailwind" is_a "CSS framework" |

**Relationship Schema:**
```json
{
  "source_entity": "Tailwind CSS",
  "target_entity": "Vite",
  "relationship_type": "integrates_with",
  "context": "Installing Tailwind CSS as a Vite plugin",
  "confidence": 0.9
}
```

**Rules:**
- `source_entity` and `target_entity` MUST match entity names exactly
- `context`: Short snippet showing the relationship

---

## 4. CLAIMS

Extract 10-20 factual statements from the document.

**Claim Types:**
| Type | Description | Example |
|------|-------------|---------|
| `capability` | What something can do | "Tailwind scans HTML files for class names" |
| `instruction` | How to do something | "Install tailwindcss via npm" |
| `definition` | What something is | "Tailwind is a utility-first CSS framework" |
| `feature` | Specific feature | "Supports hot module replacement" |
| `requirement` | What is needed | "Requires Node.js 16+" |
| `integration` | How things work together | "Works with Laravel, SvelteKit, React Router" |
| `performance` | Speed/efficiency | "Fast, with zero-runtime" |

**Claim Schema:**
```json
{
  "statement": "Tailwind CSS generates styles by scanning HTML files for class names",
  "claim_type": "capability",
  "entity_indices": [0, 2],
  "source_quote": "Tailwind CSS works by scanning all of your HTML files, JavaScript components, and any other templates for class names, generating the corresponding styles",
  "confidence": 0.95
}
```

**Rules:**
- `entity_indices`: 0-based indices into YOUR entities array
- `source_quote`: EXACT quote from document (50-500 chars)
- Be comprehensive - extract all factual claims

---

## Example Output

For a Tailwind CSS installation doc:

```json
{
  "metadata": {
    "content_type": "TUTORIAL",
    "has_code_examples": true,
    "has_step_by_step_procedures": true,
    "has_narrative_structure": false
  },
  "entities": [
    {
      "name": "Tailwind CSS",
      "entity_type": "Product",
      "description": "A utility-first CSS framework that scans HTML for class names and generates styles",
      "aliases": ["Tailwind"],
      "confidence": 0.95,
      "quote": "Tailwind CSS works by scanning all of your HTML files"
    },
    {
      "name": "Vite",
      "entity_type": "Technology",
      "description": "A modern frontend build tool with fast hot module replacement",
      "aliases": [],
      "confidence": 0.9,
      "quote": "Installing Tailwind CSS as a Vite plugin"
    },
    {
      "name": "@tailwindcss/vite",
      "entity_type": "Integration",
      "description": "Vite plugin for integrating Tailwind CSS",
      "aliases": ["tailwindcss/vite plugin"],
      "confidence": 0.85,
      "quote": "Install tailwindcss and @tailwindcss/vite via npm"
    }
  ],
  "relationships": [
    {
      "source_entity": "Tailwind CSS",
      "target_entity": "Vite",
      "relationship_type": "integrates_with",
      "context": "Installing Tailwind CSS as a Vite plugin is the most seamless way",
      "confidence": 0.9
    },
    {
      "source_entity": "@tailwindcss/vite",
      "target_entity": "Vite",
      "relationship_type": "part_of",
      "context": "Add the @tailwindcss/vite plugin to your Vite configuration",
      "confidence": 0.85
    }
  ],
  "claims": [
    {
      "statement": "Tailwind CSS generates styles by scanning HTML files for class names",
      "claim_type": "capability",
      "entity_indices": [0],
      "source_quote": "Tailwind CSS works by scanning all of your HTML files, JavaScript components, and any other templates for class names, generating the corresponding styles",
      "confidence": 0.95
    },
    {
      "statement": "Tailwind CSS has zero runtime overhead",
      "claim_type": "performance",
      "entity_indices": [0],
      "source_quote": "It's fast, flexible, and reliable — with zero-runtime",
      "confidence": 0.9
    },
    {
      "statement": "Install Tailwind CSS and the Vite plugin using npm",
      "claim_type": "instruction",
      "entity_indices": [0, 1, 2],
      "source_quote": "npm install tailwindcss @tailwindcss/vite",
      "confidence": 0.95
    }
  ]
}
```
