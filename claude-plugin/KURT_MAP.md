# Kurt Agent Architecture Map

A comprehensive map of Kurt's agent scenarios, features, and dependencies in a single graph.

## Complete System Map

**Diagram:** [kurt-architecture.mmd](kurt-architecture.mmd)

## Node Legend

### Entry Points
- **user-prompt-submit-hook**: Git pre-commit style hook that checks project state
- **/create-profile**: Complete organizational onboarding
- **/update-profile**: Update existing profile selectively
- **/create-project**: Create new project from scratch
- **/resume-project**: Resume existing project
- **/clone-project**: Clone template or existing project

### Skills
- **onboarding-skill**: Team setup, content mapping, analytics, foundation rules
- **project-management-skill**: Orchestrates project lifecycle (sources → targets → rules)
- **intelligence-skill**: Analytics (top/bottom/trending), research (AI/Reddit), content intelligence (audit/compare)
- **cms-interaction-skill**: CMS configuration and ad-hoc operations (Sanity, Contentful, WordPress)
- **content-writing-skill**: Draft, outline, edit operations with lineage tracking
- **writing-rules-skill**: Extract and manage style/structure/persona/publisher rules
- **feedback-skill**: Rate content, view trends, identify patterns → recommend rule updates

### Kurt Core CLI
- **kurt content**: List, get-metadata, fetch, map, index, cluster operations
- **kurt cms**: Onboard, search, fetch, publish, types operations
- **kurt research**: AI-powered search (Perplexity), list, get results

### Data/Config
- **kurt.sqlite**: Content metadata, analytics, feedback, classifications
- **.kurt/profile.md**: Team profile with organizational context
- **.kurt/cms-config.json**: CMS platform credentials and mappings
- **.kurt/rules/**: Style, structure, persona, publisher rule files
- **projects/*/project.md**: Project manifest (sources, targets, rules, progress)
- **sources/**: Organizational knowledge base (web + CMS content)
- **projects/*/drafts/**: Work in progress content

### Templates
- **weekly-tutorial**: Recurring tutorial publication
- **product-launch**: Multi-format product launch campaign
- **tutorial-refresh**: Analytics-driven tutorial updates
- **documentation-audit**: Comprehensive traffic audit
- **gap-analysis**: Identify missing content vs competitor
- **competitive-analysis**: Quality benchmark against competitor

## Relationship Types

- **Solid Arrow** (→): Direct invocation or dependency
- **Dotted Arrow** (-.-): Optional, conditional, or recommendation
- **Bidirectional**: Read and write relationship

## Color Guide

- 🔵 **Light Blue**: Onboarding/profile operations
- 🟡 **Yellow**: Project management operations
- 🟢 **Green**: Intelligence/analytics operations
- 🟣 **Purple**: CMS operations
- 🟠 **Orange**: Content writing operations
- 🔴 **Red**: Feedback operations
- 🌸 **Pink**: Rule extraction/management
- 📦 **Tan**: Data storage (SQLite, files)

## Quick Scenario Paths

### First-Time Setup
`/create-profile` → onboarding-skill → kurt content (map/fetch) → writing-rules-skill → .kurt/profile.md + rules/

### Create Content Project
`/create-project` → project-management-skill → kurt content → intelligence-skill → writing-rules-skill → content-writing-skill → projects/*/

### Audit Content
`/clone-project documentation-audit` → intelligence-skill (audit-traffic, identify-affected) → project.md → content-writing-skill

### Competitive Analysis
`/clone-project competitive-analysis` → intelligence-skill (compare-gaps, compare-quality) → project.md

### CMS Integration
`cms-interaction-skill onboard` → kurt cms → .kurt/cms-config.json → project-management-skill (gather-sources)

### Quality Improvement
content-writing-skill → feedback-skill (rate) → feedback-skill (patterns) → writing-rules-skill (update)
