---
title: fix-outdated-llm-documentation-duckdb
content_type: blog
source_url: https://motherduck.com/blog/fix-outdated-llm-documentation-duckdb
indexed_at: '2025-11-25T19:58:22.546480'
content_hash: ac656ff4ed186fc7
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Teaching Your LLM About DuckDB the Right Way: How to Fix Outdated Documentation

2025/07/15 - 4 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

Most developers are still feeding their AI assistants stale, fragmented documentation. There's a better way.

For instance, if you ask "What's the latest DuckDB version your data has been trained on?" to ChatGPT, Claude, and Gemini, here's what they know:

| AI Assistant | DuckDB Version | Training Data Cutoff |
| --- | --- | --- |
| GPT-4o | 0.10.2 | May 2024 |
| Gemini 2.5 Pro | 1.0.0 | June 2024 |
| Claude Sonnet 4 | 1.1.3 | Late 2024 |

Projects like DuckDB (and MotherDuck) move incredibly fast. Even 3-month-old documentation can be completely outdated, making your workflow painful as you tweak code with methods that no longer exist. Version `0.10` compared to `1.3.2` (current) feels prehistoric.

So how do you ensure your AI gets the latest docs when you need them?

In this blog, we'll explore updating your LLMs through `llms.txt` or Cursor's docs feature—using DuckDB and MotherDuck as examples.

## A new standard for AI: llms.txt

Traditional files like `robots.txt` and `sitemap.xml` help **search engines** understand your site structure — but they weren’t built with large language models (LLMs) in mind. That’s where [`llmstxt.org`](https://llmstxt.org/) comes in. It's a growing standard tailored specifically for LLMs, offering content in a format that’s easier for AI to read and reason about.

As LLMs become a more common way developers and users access documentation, clarity and structure are more important than ever. Parsing raw HTML often leads to messy results: cluttered navigation, JavaScript, styling tags — all noise from the perspective of an AI model.

In fact, we may already be at the point where LLMs are consuming developer docs more than humans do. [Andrej Karpathy](https://x.com/karpathy) even called this shift out in a [recent post](https://x.com/karpathy/status/1914494203696177444).

The `llms.txt` spec introduces two files:

1. `/llms.txt` – a lightweight, structured index of your docs, similar in spirit to `sitemap.xml`, but more markdown-friendly.
2. `/llms-full.txt` – a single, comprehensive text dump of all your documentation, ready for ingestion.

In addition, the specification recommends that websites offering content potentially useful to LLMs also provide **a clean Markdown version of each page**. This version should be accessible at the same URL as the original page, with `.md` appended.

By using these, documentation updates become much easier to manage, especially for tools that rely on LLMs to serve answers and insights.

## Where to find llms.txt and llms-full.txt for DuckDB and MotherDuck ?

Typically, if you go to the root of the website `mywebsite.com/llms.txt` or sometimes at significant root like `mywebsite.com/docs/llms.txt` you should find them!

You can also try appending `.md` to any webpage URL to see if the site provides markdown versions.

For DuckDB, you'll find them at :

- [`https://duckdb.org/docs/stable/llms.txt`](https://duckdb.org/docs/stable/llms.txt): Focused on DuckDB’s SQL dialect and features.
- [`https://duckdb.org/docs/stable/llms-full.txt`](https://duckdb.org/docs/stable/llms-full.txt): Full documentation for DuckDB.

You can also append any page with `.md` and get the markdown version for instance : [https://duckdb.org/docs/stable/clients/cpp.md](https://duckdb.org/docs/stable/clients/cpp.md)

For MotherDuck, you'll find them at :

- [https://motherduck.com/docs/llms.txt](https://motherduck.com/docs/llms.txt)
- [https://motherduck.com/docs/llms-full.txt](https://motherduck.com/docs/llms-full.txt)

You can also append any docs page with `.md` to get the markdown version, but to make it even easier, we have a drop down menu with the llms.txt and also a `Copy as Markdown` on each of our page.

![img1](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_07_15_at_9_58_12_AM_d12356a8e4.png&w=3840&q=75)

## Feeding your LLMs with Cursor docs

The llms.txt and markdown files we discussed work great when you copy and paste them into any LLM chatbox. However, if you're using Cursor, there's an even better, automated way to avoid copy-pasting every time.

In Cursor, under `Settings > Cursor Settings > Features > Docs`, you can add documentation sources to be used as context in your prompts. These sources are crawled and indexed. They can be documentation websites, API docs, or even raw GitHub code.

When you add a custom documentation URL, you give it a name (an alias for your prompts), and Cursor crawls and indexes it for you. Once these are added, you can reference them in your prompt using `@docs <my alias name>`.

![im2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F2ffe2aa5_6742_4b8b_89ae_cea358322a95_1084x306_e14b1dcdfb.png&w=3840&q=75)

Now next time you want to ask something around DuckDB or MotherDuck, just use `@` and select the documentation.

## Going further with MCP

Keeping your AI assistants updated with fresh documentation doesn't have to be a manual chore. Whether you're using [`llms.txt`](https://llmstxt.org/) files for quick copy-paste workflows or Cursor's automated docs feature for seamless integration, these approaches ensure your AI has access to the latest information when you need it most.

As more projects adopt the `llms.txt` standard and tools like [MCP](https://modelcontextprotocol.io/) emerge, the gap between rapidly evolving codebases and AI knowledge will continue to shrink. Your future self (and your code) will thank you for making this investment in better AI-assisted development.

If you want your AI to actually run DuckDB/MotherDuck queries (not just understand the docs), MotherDuck has an official [DuckDB MCP server](https://motherduck.com/blog/faster-data-pipelines-with-mcp-duckdb-ai/) that lets your AI execute queries directly against your data.

In the meantime, take care of your LLMs, and keep prompting.

### TABLE OF CONTENTS

[A new standard for AI: llms.txt](https://motherduck.com/blog/fix-outdated-llm-documentation-duckdb/#a-new-standard-for-ai-llmstxt)

[Where to find llms.txt and llms-full.txt for DuckDB and MotherDuck ?](https://motherduck.com/blog/fix-outdated-llm-documentation-duckdb/#where-to-find-llmstxt-and-llms-fulltxt-for-duckdb-and-motherduck)

[Feeding your LLMs with Cursor docs](https://motherduck.com/blog/fix-outdated-llm-documentation-duckdb/#feeding-your-llms-with-cursor-docs)

[Going further with MCP](https://motherduck.com/blog/fix-outdated-llm-documentation-duckdb/#going-further-with-mcp)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Small Data SF Returns November 4-5, 2025: First Speakers Announced](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsmall_data_sf_2025_961a26b2f1.png&w=3840&q=75)](https://motherduck.com/blog/announcing-small-data-sf-2025/)

[2025/07/17 - Ryan Boyd](https://motherduck.com/blog/announcing-small-data-sf-2025/)

### [Small Data SF Returns November 4-5, 2025: First Speakers Announced](https://motherduck.com/blog/announcing-small-data-sf-2025)

Conference with two days of practical innovation on data and AI: workshops and talks from industry leaders, including Benn Stancil, Joe Reis, Adi Polak, George Fraser, Jordan Tigani, Holden Karau, Ravin Kumar, Sam Alexander and more!

[![Introducing Mega and Giga Ducklings: Scaling Up, Way Up](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_sizes_social_cards_3c29d6c212.png&w=3840&q=75)](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/)

[2025/07/17 - Ryan Boyd](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/)

### [Introducing Mega and Giga Ducklings: Scaling Up, Way Up](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale)

New MotherDuck instance sizes allow data warehousing users more flexibility for complex queries and transformations. Need more compute to scale up? Megas and Gigas will help!

[View all](https://motherduck.com/blog/)

Authorization Response