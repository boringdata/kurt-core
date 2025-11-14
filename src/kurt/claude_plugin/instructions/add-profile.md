# ADD-PROFILE.md

## When to use this instruction
To populate a user's <writer_profile> (`kurt/profile.md`), which is used as context when writing.

## Steps to execute
1. If the user has an existing <writer_profile> file that they'd like to modify, load it.  Ask what they'd like to modify, make necessary modifications and end this workflow.
2. If the user doesn't have an existing <writer_profile>, make a copy of the `kurt/templates/profile-template.md` file (the <profile_template>) at `kurt/profile.md`.  
3. **IMPORTANT: Read the profile template FIRST before asking any questions.** Ask them to provide ONLY the information needed to complete the placeholders in the <profile_template> - do not ask for additional information beyond what's in the template.
4. Ask for further information if they fail to provide any items, or clarification if anything is unclear.
5. Populate the user's <writer_profile> with the user's responses.
6. For any homepage URLs provided ({{COMPANY_WEBSITE}}, {{DOCS_URL}}, {{BLOG_URL}}):

   **User's own sites** (company website, docs, blog) are reference materials:
   - Map inline (need to know what content exists), but don't fetch yet
   ```bash
   kurt content map url {url}
   ```
   - Tell user: "Mapped {count} pages from {url} for future reference."

   **Important**: These are reference materials - mapped but not fetched. Content will be fetched on-demand when writing projects need specific sections.

6.5. (Optional) Ask if the user uses a CMS for their content:

     "Do you use a CMS like Sanity, Contentful, or WordPress for managing content?"

     - If yes: "I can help set up the integration now, or we can do it later when you need it. Would you like to configure it now?"
       - If configure now: Run `kurt integrations cms onboard --platform {platform}` to guide them through setup
       - If later: "No problem! When you share CMS content later, I'll guide you through setup."

     - If no: Skip this step

     NOTE: Do NOT store CMS info in the profile. CMS configuration status is tracked in kurt.config automatically.
7. Tell the user that they can modify it anytime from that location, or by asking in the chat.
