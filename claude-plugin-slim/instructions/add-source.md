# ADD-SOURCE.md

## When to use this instruction
When a user drops URLs or pastes files (blobs of text that appear to be a complete file) into the chat, we ingest them into the filesystem using `kurt map` (full site) and `kurt fetch` (individual URL or text blog) commands, so that they can be used within writing projects.  Run `kurt map --help` or `kurt fetch --help` to examine full options.

## Steps to execute

Select the appropriate `kurt` command to add the source using the following logic.  All operations return the URL (if provided) + file paths (if any) that were created in the filesystem.

- If the URL is user's own site (see `kurt/profile.md`), map the full site using `kurt map url <URL>`, which discovers web content by downloading the sitemap.
- If the URL is a homepage of a competitor or other company, map the full site using `kurt map url <URL>`, and then fetch the homepage using `kurt fetch --urls <urls>`.
- If the URL is an individual page, ingest it directly using `kurt fetch --urls <urls>`.
<!-- This doesn't work atm -->
- If a pasted text file, create a .md file for it in `<project_folder>/sources/descriptive-file-name.md`, and then index it using `kurt fetch --file <<filepath>>`.
<!-- This doesn't work atm -->
- If the URL is a link to a CMS entry, ingest it using `kurt fetch cms`.
