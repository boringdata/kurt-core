---
title: introducing-instant-sql
content_type: blog
source_url: https://motherduck.com/blog/introducing-instant-sql
indexed_at: '2025-11-25T19:56:49.735548'
content_hash: 262cd3d0b508d546
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Instant SQL is here: Speedrun ad-hoc queries as you type

2025/04/23 - 8 min read

BY

[Hamilton Ulmer](https://motherduck.com/authors/hamilton-ulmer/)

Today, we’re releasing **Instant SQL**, a new way to write SQL that updates your result set as you type to expedite query building and debugging – all with zero-latency, no run button required. Instant SQL is now available in [MotherDuck](https://motherduck.com/) and the [DuckDB Local UI](https://duckdb.org/docs/stable/extensions/ui.html).

![Intro GIF](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Finstant_sql_trailer_v1_90035393ab.gif&w=3840&q=75)

We built Instant SQL for a simple reason: writing SQL is still too tedious and slow. Not because of the language itself, but because the way we interact with databases hasn’t evolved much since SQL was created. Writing SQL isn’t just about syntax - It’s about making sense of your data, knowing what to ask, and figuring out how to get there. That process is iterative, and it’s _hard_.

> "Instant SQL will save me the misery of having to try and wrangle SQL in my BI tool where iteration speed can be very slow. This lets me get the data right earlier in the process, with faster feedback than waiting for a chart to render or clearing an analytics cache."
> \-\- Mike McClannahan, CTO, [DashFuel](https://www.getdashfuel.com/)

Despite how much database engines have improved, with things like columnar storage, vectorized execution, and the creation of blazing-fast engines like DuckDB, which can scan billions of rows in seconds, the experience of _building_ a query hasn’t kept up. We still write queries in a text editor, hit a run button, and wait to see what happens.

At MotherDuck, we've been tackling this problem from multiple angles. Last year, we released the [Column Explorer](https://motherduck.com/blog/introducing-column-explorer/), which gives you fast distributions and summary statistics for all the columns in your tables and result sets. We also released [FixIt](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/), an unreasonably effective AI fixer for SQL. MotherDuck users love these tools because they speed up data exploration and query iteration.

Instant SQL isn't just an incremental improvement to SQL tooling: _It's a fundamentally new way to interact with your queries_ \- one where you can see your changes instantly, debug naturally, and actually trust the code that your AI assistant suggests. No more waiting. No more context switching. Just _flow_.

Let's take a closer look at how it works.

## Generate preview results as you type

Everyone knows what it feels like to start a new query from scratch. Draft, run, wait, fix, run again—an exhausting cycle that repeats hundreds of times a day.

Instant SQL gives you result set previews that update as you type. You're no longer running queries—you're exploring your data in real-time, maintaining an analytical flow state where your best thinking happens.

![GIF 1](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGIF_1_15e918df5e.gif&w=3840&q=75)

Whether your query is a simple transformation or a complex aggregation, Instant SQL will let you preview your results in real-time.

![GIF 2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGIF_2_cf6226ce64.gif&w=3840&q=75)

## Inspect and edit CTEs in real-time

CTEs are easy to write, but difficult to debug. How many times a day do you comment out code to figure out what's going on in a CTE? With Instant SQL, you can now click around and instantly visualize any CTE in seconds, rather than spend hours debugging. Even better, changes you make to a CTE are immediately reflected in all dependent select nodes, giving you real-time feedback on how your modifications cascade through the query.

![GIF 3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGIF_3_760907ee77.gif&w=3840&q=75)

## Break apart your complex column expressions

We've all been there; you write a complex column formula for an important business metric, and when you run the query, you get a result set full of `NULLs`. You then have to painstakingly dismantle it piece-by-piece to determine if the issue is your logic or the underlying data.

Instant SQL lets you break apart your column expressions in your _result table_ to pinpoint exactly what's happening. Every edit you make to the query is instantly reflected in how data flows through the expression tree. This makes debugging anything from complex numeric formulas to regular expressions feel effortless.

![GIF 4](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Finstant_sql_decomp_v4_00daad41c8.gif&w=3840&q=75)

## Preview anything DuckDB can query - not just tables

Instant SQL works for more than just DuckDB tables; it works for massive tables in MotherDuck, parquet files in S3, Postgres tables, SQLite, MySQL, Iceberg, Delta – you name it. If DuckDB can query it, you can see a preview of it.

This is, hands down, the _best_ way to quickly explore and model external data.

![GIF 5](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGIF_4_1bcfbe9e71.gif&w=3840&q=75)

## Fast-forward to a useful query before running it

Instant SQL gives you the freedom to test and refine your query logic without the wait. You can quickly experiment with different approaches in real-time. When you're satisfied with what you see in the preview, you can then run the query for your final, materialized results. This approach cuts hours off your SQL workflow, transforming the tedious cycle of write-run-wait into a fluid process of exploration and discovery.

![GIF 6](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Finstant_sql_run_46810b7e29.gif&w=3840&q=75)

## Instantly preview AI-powered edit suggestions

All of these workflow improvements are great for humans, but they're even better when you throw AI features into the mix. Today, we're also releasing a new inline prompt editing feature for MotherDuck users. You can now select a bit of text, hit cmd+k (or ctrl+k for Windows and Linux users), write an instruction in plain language, and get an AI suggestion.

Instant SQL makes this inline edit feature work magically. When you get a suggestion, you immediately see the suggestion applied to the result set. No more flipping a coin and accepting a suggestion that might ruin your hard work.

![GIF 7](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGIF_6_a58587fe64.gif&w=3840&q=75)

### Why hasn't anyone done this before?

As soon as we had a viable prototype of Instant SQL, we began to ask ourselves: _why hasn't anyone done something like this before?_ It seems obvious in hindsight. It turns out that you need a unique set of requirements to make Instant SQL work.

### A way to drastically reduce the latency in running a query

Even if you made your database return results in milliseconds, it won’t be much help if you’re sending your queries to us-east-1. DuckDB’s local-first design, along with principled performance optimizations and friendly SQL, made it possible to use _your computer_ to parse queries, cache dependencies, and rewrite & run them. Combined with MotherDuck’s dual execution architecture, you can effortlessly preview and query massive amounts of data with low latency.

### A way to rewrite queries

Making Instant SQL requires more than just a performant architecture. Even if DuckDB is fast, real-world ad hoc queries may still take longer 100ms to return a result. And of of course, DuckDB can also query remote data sources. We need a way to locally cache samples of certain table references and rewrite our queries to point to those.

A few years ago, DuckDB hid a piece of magic in the JSON extension: a way to get an abstract syntax tree (or AST) from any SELECT statement via a [SQL scalar function](https://duckdb.org/docs/stable/data/json/sql_to_and_from_json.html). This means any toolmaker can build parser-powered features using this important part of DuckDB's database internals - no need to write your own SQL parser from scratch.

### A caching system that accurately models your query

Of course, showing previews as you type requires more than just knowing where you are in the query. We've implemented several sophisticated local caching strategies to ensure results appear instantly. Think of it as a system that anticipates what you might want to see and prepares it ahead of time. The details of these caching techniques are interesting enough to deserve their own blog post. But suffice it to say, once the cache is warm, the results materialize before you can even lift your fingers from the keyboard.

Without this perfect storm of technical capabilities – a fast local SQL engine, parser accessibility, precise cursor-to-AST mapping, and intelligent caching – Instant SQL simply couldn't exist.

### A way to preview any SELECT node in a query

Getting the AST is a big step forward, but we still need a way to take your cursor position in the editor and map it to a _path_ through this AST. Otherwise, we can’t know which part of the query you're interested in previewing. So we built some simple tools that pair DuckDB’s parser with its tokenizer to enrich the parse tree, which we then use to pinpoint the start and end of all nodes, clauses, and select statements. This cursor-to-AST mapping enables us to show you a preview of exactly the `SELECT` statement you're working on, no matter where it appears in a complex query.

## Try Instant SQL

Instant SQL is now available in [MotherDuck](https://motherduck.com/) and the [DuckDB Local UI](https://duckdb.org/docs/stable/extensions/ui.html), in public preview. Give it a try to experience firsthand how fast SQL flies when real-time query results are at your fingertips as you type. Our new, prompt-based Edit feature is also available to MotherDuck users.

What If SQL Queries Returned Results Instantly? - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[What If SQL Queries Returned Results Instantly?](https://www.youtube.com/watch?v=aFDUlyeMBc8)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=aFDUlyeMBc8&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 1:13

•Live

•

We’d love to hear more about how you’re using Instant SQL, and we look forward to hearing your stories and feedback on social media and in [Slack](https://join.slack.com/t/motherduckcommunity/shared_invite/zt-33g6kee8z-SEUE3ylvflpolpYB7AIMgg).

## PS: We’re hiring!

At MotherDuck, we’re building a future where analytics work for everyone - from new UI features like Instant SQL to the platforms and databases that power them. If you’re passionate about building complex, data-intensive interfaces, [we’re hiring](https://motherduck.com/careers/#open-positions), and we’d love to have you join the flock to help us make these features even more magical.

### TABLE OF CONTENTS

[Generate preview results as you type](https://motherduck.com/blog/introducing-instant-sql/#generate-preview-results-as-you-type)

[Inspect and edit CTEs in real-time](https://motherduck.com/blog/introducing-instant-sql/#inspect-and-edit-ctes-in-real-time)

[Break apart your complex column expressions](https://motherduck.com/blog/introducing-instant-sql/#break-apart-your-complex-column-expressions)

[Preview anything DuckDB can query - not just tables](https://motherduck.com/blog/introducing-instant-sql/#preview-anything-duckdb-can-query-not-just-tables)

[Fast-forward to a useful query before running it](https://motherduck.com/blog/introducing-instant-sql/#fast-forward-to-a-useful-query-before-running-it)

[Instantly preview AI-powered edit suggestions](https://motherduck.com/blog/introducing-instant-sql/#instantly-preview-ai-powered-edit-suggestions)

[Try Instant SQL](https://motherduck.com/blog/introducing-instant-sql/#try-instant-sql)

[PS: We’re hiring!](https://motherduck.com/blog/introducing-instant-sql/#ps-were-hiring)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![How MotherDuck Scales DuckDB in the Cloud vertically and horizontally](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_scaling_e2b61d511b.png&w=3840&q=75)](https://motherduck.com/blog/scaling-duckdb-with-ducklings/)

[2025/04/16 - Ryan Boyd](https://motherduck.com/blog/scaling-duckdb-with-ducklings/)

### [How MotherDuck Scales DuckDB in the Cloud vertically and horizontally](https://motherduck.com/blog/scaling-duckdb-with-ducklings)

aka What the duck is a Duckling?

[![Streaming in the Fast Lane: Oracle CDC to MotherDuck Using Estuary](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FEstuary_blog_new_4509d479b7.png&w=3840&q=75)](https://motherduck.com/blog/streaming-oracle-to-motherduck/)

[2025/04/17 - Emily Lucek](https://motherduck.com/blog/streaming-oracle-to-motherduck/)

### [Streaming in the Fast Lane: Oracle CDC to MotherDuck Using Estuary](https://motherduck.com/blog/streaming-oracle-to-motherduck)

Ducks and estuaries go together. So it’s no surprise that MotherDuck, a cloud data warehouse, pairs well with Estuary, a data pipeline platform.

[View all](https://motherduck.com/blog/)

Authorization Response