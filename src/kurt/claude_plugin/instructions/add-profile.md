# ADD-PROFILE.md

## When to use this instruction
To populate a user's <writer_profile> (`kurt/profile.md`), which is used as context when writing.

## Steps to execute
1. If the user has an existing <writer_profile> file that they'd like to modify, load it.  Ask what they'd like to modify, make necessary modifications and end this workflow.
2. If the user doesn't have an existing <writer_profile>, make a copy of the `kurt/templates/profile-template.md` file (the <profile_template>) at `kurt/profile.md`.  Ask them to provide the information needed to complete the <profile_template>.
3. Ask for further information if they fail to provide any items, or clarification if anything is unclear.
4. Populate the user's <writer_profile> with the user's responses.
5. For any homepage URLs provided ({{COMPANY_WEBSITE}}, {{DOCS_URL}}, {{BLOG_URL}}) by the user, add them as sources following the instructions in `instructions/add-source.md`.
6. Tell the user that they can modify it anytime from that location, or by asking in the chat.
