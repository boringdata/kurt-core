# Create Profile Subskill

**Purpose:** Quick team profile setup (under 2 minutes)
**Output:** `.kurt/profile.md`

---

## Step 1: Welcome + Questions

Show checklist and ask questions immediately:

```
═══════════════════════════════════════════════════════
Welcome to Kurt!
═══════════════════════════════════════════════════════

Here's what we'll do:

- [ ] Gather organization information
- [ ] Set up optional integrations
- [ ] Review your profile

This takes under 2 minutes for the basics.

───────────────────────────────────────────────────────
Let's start with a few questions:
───────────────────────────────────────────────────────

1. What company/organization are you working for?
2. What's your role or team? (e.g., Marketing, DevRel, Product)
3. What's your primary communication/marketing goal?

Answer with numbered responses like:
1. Acme Corp
2. DevRel team
3. Drive developer adoption through educational content

(You can update these anytime by running /update-profile)
```

Wait for user response. Parse numbered answers. If missing any, ask for them.

---

## Step 2: Create Profile

Create `.kurt/profile.md` with organization info and empty sections for content, analytics, rules, and projects.

**Validate:** Check file was created. If failed, ask to retry or exit.

Show: `✓ Profile created: .kurt/profile.md`

---

## Step 3: Optional Integrations

Ask:
```
Would you like to set up any of these now? (optional, can do later via /update-profile)

a) Map content sources (website, docs, blog)
b) Connect analytics (Google Analytics, Plausible)
c) Configure CMS integration (Sanity, Contentful, WordPress)
d) Skip for now

Choose one or more (a,b,c) or d to skip:
```

For each selected:
- **a)** Execute `map-content.md`
- **b)** Execute `setup-analytics.md`
- **c)** Delegate to `kurt:cms-interaction-skill`

If content mapped, ask about extracting foundation rules → Execute `extract-foundation.md`

If any fails, offer: retry, skip, or exit.

---

## Step 4: Success

```
═══════════════════════════════════════════════════════
🎉 Profile Created!
═══════════════════════════════════════════════════════

Your Kurt profile is ready: .kurt/profile.md

{{Show what was completed}}

───────────────────────────────────────────────────────
What's Next?
───────────────────────────────────────────────────────

{{Show missing items + /create-project}}

Remember: Update anytime with /update-profile
```

---

*Use the checklist items with TodoWrite to track progress as you work through steps.*
