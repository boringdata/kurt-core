---
title: introducing-fixit-ai-sql-error-fixer
content_type: product_page
source_url: https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer
indexed_at: '2025-11-25T19:57:34.063551'
content_hash: ba4120853f926245
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Introducing FixIt: an unreasonably effective AI error fixer for SQL

2024/01/03 - 9 min read

BY

[Till Döhmen](https://motherduck.com/authors/till-d%C3%B6hmen/)
,
[Hamilton Ulmer](https://motherduck.com/authors/hamilton-ulmer/)

Today we’re releasing FixIt, MotherDuck’s first AI-powered UI feature. FixIt helps you resolve common SQL errors by offering fixes in-line. You can try it out starting now in our [web app](https://app.motherduck.com/). See it in action:

Your browser does not support the video tag.

Why did we focus on fixing errors? If you’re anything like us, your workflow for writing analytical SQL probably looks something like this:

1. write the first version of your query
2. run the query
3. If you receive an error, you locate the error in your SQL figure out what went wrong
4. If you don’t know how to fix it, go to the documentation, or look at your available tables and columns
5. then attempt to fix your query and go back to step 2

FixIt collapses all those tedious error-fixing steps into one. It’s like watching a SQL expert speed-run all your fixes for you. See it in action here:

## How does it work?

FixIt uses a large language model (LLM) to generate suggestions; it feeds the error, the query, and additional context into an LLM to generate a new line that fixes the query. Here’s how it works in the UI:

1. When you encounter a query error in the MotherDuck UI, FixIt generates a simple inline suggestion, which you can accept, reject, or simply ignore
2. Accepting a FixIt suggestion applies the fix and re-runs the query
3. You can cancel the suggestion, or ignore it entirely and fix your query yourself

Much like our [other AI features](https://motherduck.com/docs/key-tasks/writing-sql-with-ai/), FixIt is powered by a new function, `fix_single_line`, available to all MotherDuck customers and users of our extension. This table function is a great option for customers and partners building their own editor-driven interfaces on top of DuckDB.

For MotherDuck UI users, we think FixIt is special for three reasons:

- It fits within your existing querying workflow
- It’s pretty _fast_ at generating suggestions
- The suggestions it gives you are easy to visually inspect

## FixIt is a powerful yet non-intrusive improvement to your existing workflow

We’ve all seen incredibly impressive demos of LLMs writing SQL from scratch. FixIt, by contrast, takes a more humble approach. Rather than attempt to fix every possible error in your query in one go, FixIt will only fix whatever line it thinks will resolve your SQL error.

We think this unreasonable simplicity also makes it unreasonably effective. In truth, the most common SQL errors tend to have simple, one-line fixes. Even if the error requires multiple fixes across several lines, FixIt will still suggest fixes one line at a time, often iterating itself into a functional query. These assumptions enable FixIt to effortlessly correct many common SQL errors like:

- Parsing strings into timestamps
- Writing regular expressions and JSON parsing functions
- Misspelling table and column names
- Adding GROUP BY ALL or fixing existing GROUP BY statements

To complement FixIt’s simplicity, we designed it to be as non-intrusive as possible. If you type anywhere in the editor while a fix is either being generated or shown, we remove the suggestion. So you can ignore the feature entirely if it isn’t helping. Additionally, if you find that the suggestions are far off-base, you can turn off the feature in the MotherDuck UI under the settings panel.

Of course, FixIt does not do well in cases where your query is _fundamentally wrong_, and the SQL you’ve written doesn’t give it enough clues to iteratively fix its way to a solution. FixIt is a feature designed for people that more-or-less know enough SQL to make a mostly-coherent query. Think of it as “lane assist” on a car. You still need your hands on the wheel.

## FixIt is fast

Because FixIt excels at simple one-line fixes, it only needs to generate one line of SQL at a time. This tends to be pretty fast! When a suggestion shows up quickly, it is more likely to match your natural working tempo. And when it matches your tempo, it is more likely to be integrated into your workflow.

We only figured this out after first prototyping the _wrong_ approach – completely regenerating a new query from scratch – which resulted in three problems:

1. Since the LLM has to rewrite the query token-by-token, you end up waiting too long just to receive a simple fix – around 5-10 seconds for toy queries.
2. The latency increases linearly with the size of the query, making this approach impractical for real-world work, where queries are hundreds of lines long.
3. The LLM might also get most of the query right, but occasionally take creative liberties with the formatting or semantics of the rest of the query, making it hard to display only the relevant changes.

It felt like watching a human manually rewrite a new version of your query start-to-finish while trying to keep the 95% of the old query that was working. Impressive to see in isolation, but not a great user experience in practice.

We then tried the next-obvious approach – generating _only_ the line number and the fixed line for the given error. In our tests, we found that this reduced the total query time down to _1-3 sec_ for most cases and gave the LLM fewer opportunities to unhelpfully steer the unbroken parts of a query into a worse direction.

A latency difference of 1-3 seconds vs. 10-20 seconds is _[profound](https://www.thinkwithgoogle.com/consumer-insights/consumer-trends/mobile-site-load-time-statistics/)_. Aside from dealing with errors, waiting for analytical queries to finish is one of the most cognitively costly parts of ad hoc data work. DuckDB already drastically reduces this cost when queries are correct; we want FixIt to also feel just as effortless when queries have errors.

## It's easy to verify the fix, making it more trustworthy

FixIt’s simplicity gives it another big advantage – it is a lot easier for users to validate changes to a single line compared to a completely rewritten query.

No matter what role an LLM has in generating and editing a query, people still need to understand how their query works. By providing small suggestions, users are much more likely to both comprehend and accept them. We think of it like we do Github pull requests; a smaller, easy-to-follow change is much easier to verify by the reviewer.

## How we built FixIt

Given that we went from ideation to release in a month, we decided to try using traditional prompt engineering to reduce the technical risk and focus on the user experience. There’s simply no faster way to prototype than to use OpenAI’s GPT-4 with its powerful [prompting](https://platform.openai.com/docs/guides/prompt-engineering) capabilities. We were happy to discover that our approach was quite simple, highly effective, and low-latency enough to be an actual product feature.

But of course we _did_ spend a lot of time iterating on the prompt itself. Here are some high-level insights:

- **Prepend line numbers to each line**. LLMs are notoriously bad at counting. When putting the query into the prompt, we found that prepending a line number made it much easier for the LLM to correctly return the line number of the fix.
- **Adapt the prompt for certain error types**. By creating different pathways for certain error types, we can provide more control over error-specific prompts, such as nudging the model to use DuckDB's GROUP BY ALL function when a GROUP BY is missing.
- **Add the schema to context**. Having access to the relevant database schema made it more reliable at recommending catalog and binder error fixes.
- **Test, dogfood, and iterate on prompt.** We tested the prompt on around 3,000 queries, dropping random characters to see how it’d respond. We also dogfooded extensively to figure out where the prompt succeeded and where it failed. Dogfooding was easily the most effective way for us to improve the output.
- **Post-process the output.** Because we’re generating highly-structured output, using [OpenAI’s function calling API](https://platform.openai.com/docs/guides/function-calling), it’s easy to make changes to the result. The easiest and most impactful change we make is simply getting the whitespace correct. This makes it much easier for people to review a given suggestion.

We evaluated the fixing quality with different OpenAI models on our test corpus with randomly corrupted queries. While GPT-3.5 is the lowest-cost option, it also provided noticeably lower-quality results than GPT-4.

Evaluating different OpenAI models:

| **Model** | **Version** | **Fix Success Rate\*** | **Median Response Time per Fix\*** |
| --- | --- | --- | --- |
| GPT-3.5-turbo | 1106 | 62 % | 0.75s |
| GPT-4 | 1106-preview (turbo) | 78 % | 1.67s |
| GPT-4 | 0613 | 85 % | 1.74s |

\\* Fix Success Rate: Percentage of randomly corrupted queries that execute successfully after the suggested fix. A set of approx. 3000, mostly human-written, queries is corrupted by dropping a sequence of 1-4 characters from a random position in the query string. We filter out queries that do not result in any parser, binder or execution error.

\\* Median Response Time: Using Azure OpenAI Service Endpoints

In the future, we aim to improve both inference time and quality while reducing cost per fix:

- **Fixing Regions for Large Queries**: Utilizing DuckDB's parser internals can help extract error character positions. This allows us to identify whether a specific subquery or CTE is affected, reducing the need to pass the entire query and only targeting the affected part. This would undoubtedly save tokens and enhance focus.
- **Filter Schema Information**: Currently, schema information comprises a large part of the context size and therefore the cost per request. Moving forward, we plan to develop heuristics to identify which parts of the schema are relevant for correction.
- **Smaller Models for Certain Error Types**: By creating different pathways for certain error types, we can direct simpler fix requests to smaller and less expensive models.
- **Open Models**: The efficiency of open models is continually improving. For instance, the recently published [Mixtral-8x7B](https://mistral.ai/news/mixtral-of-experts/) model achieves GPT-3.5-level quality at lower inference times. Coupled with solutions like [jsonformer](https://github.com/1rgs/jsonformer) and [open model inference endpoints](https://twitter.com/anyscalecompute/status/1734628112980430947) for structured JSON output, we have all the essential elements for switching to an open-model stack, making us less dependent on a single cloud-based inference service.
- **Fine Tuning**: Error fixing should be a well suited task for fine-tuning, potentially enabling us to use even smaller models with lower inference times. Generating large amounts of synthetic training data seems straight-forward (dropped characters, flipped function arguments, dropped group by’s, etc.)
- **Heuristics:** We don't always _have_ to rely on LLMs to rectify errors. Some simpler problems can be resolved more reliably and quickly using heuristics.

## Can We Fix It? Yes We Can!

We think FixIt strikes a nice balance between being actually useful for everyday SQL work, and fairly novel low-latency experience. [Try it out](https://app.motherduck.com/) and give us feedback - on [Slack](https://slack.motherduck.com/) or via [email](mailto:support@motherduck.com)!

### TABLE OF CONTENTS

[How does it work?](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/#how-does-it-work)

[FixIt is a powerful yet non-intrusive improvement to your existing workflow](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/#fixit-is-a-powerful-yet-non-intrusive-improvement-to-your-existing-workflow)

[FixIt is fast](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/#fixit-is-fast)

[It's easy to verify the fix, making it more trustworthy](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/#its-easy-to-verify-the-fix-making-it-more-trustworthy)

[How we built FixIt](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/#how-we-built-fixit)

[Can We Fix It? Yes We Can!](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/#can-we-fix-it-yes-we-can)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![The Future of BI: Exploring the Impact of BI-as-Code Tools with DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_bi_as_code_blog_88b8acbf7f.png&w=3840&q=75)](https://motherduck.com/blog/the-future-of-bi-bi-as-code-duckdb-impact/)

[2023/12/07 - Mehdi Ouazza](https://motherduck.com/blog/the-future-of-bi-bi-as-code-duckdb-impact/)

### [The Future of BI: Exploring the Impact of BI-as-Code Tools with DuckDB](https://motherduck.com/blog/the-future-of-bi-bi-as-code-duckdb-impact)

The Future of BI: Exploring the Impact of BI-as-Code Tools with DuckDB

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response