---
title: sql-llm-prompt-function-gpt-models
content_type: blog
source_url: https://motherduck.com/blog/sql-llm-prompt-function-gpt-models
indexed_at: '2025-11-25T19:57:45.377497'
content_hash: 8c7ff7c662878e52
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Introducing the prompt() Function: Use the Power of LLMs with SQL!

2024/10/17 - 6 min read

BY

[Till Döhmen](https://motherduck.com/authors/till-d%C3%B6hmen/)

In recent years, the costs associated with running large language models (LLMs) [have fallen significantly](https://x.com/AndrewYNg/status/1829190549842321758), making advanced natural language processing techniques more accessible than ever before. The emergence of small language models (SLMs) like [gpt-4o-mini](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/) has led to another order of magnitude in cost reductions for very capable language models.

This democratization of AI has reached a stage where integrating small language models (SLMs) like OpenAI’s gpt-4o-mini directly into a scalar SQL function has become practicable from both cost and performance perspectives.

Therefore we’re thrilled to announce the **prompt()** function, which is now available in Preview on MotherDuck. This new SQL function simplifies using LLMs and SLMs with text to generate, summarize, and extract structured data without the need of separate infrastructure.

It's as simple as calling:

```sql
Copy code

SELECT prompt('summarize my text: ' || my_text) as summary FROM my_table;
```

## Prompt Function Overview

The **prompt()** currently supports OpenAI's gpt-4o-mini and gpt-4o models to provide some flexibility in terms of cost-effectiveness and performance.

In our preview release, we allow gpt-4o-mini-based prompts to be applied to all rows in a table, which unlocks use cases like bulk [text summarization](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt/#summarization) and [structured data extraction](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt/#structured-data-extraction). Furthermore, we allow single-row and constant inputs with gpt-4o to enable high-quality responses for example in [retrieval augmented generation (RAG)](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt/#retrieval-augmented-generation-rag) use cases.

The optionally named **(model:=)**, parameter determines which model to use for inference, e.g.:

```sql
Copy code

SELECT prompt('Write a poem about ducks', ‘gpt-4o’) AS response;
```

The prompt function also supports returning structured output, using the **struct** and **struct\_descr** parameters. More on that [later in the post](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/#struct_output).

Future updates may include additional models to expand functionality and meet diverse user needs.

### Use Case: Text Summarization

The **prompt()** function is a straightforward and intuitive scalar function.

For instance, if reading plain raw comments on Hacker News sounds boring to you, you could have them summarized into a [Haiku](https://en.wikipedia.org/wiki/Haiku). The following query is using our [Hacker News example dataset](https://motherduck.com/docs/getting-started/sample-data-queries/hacker-news/) :

```sql
Copy code

SELECT by, text, timestamp,
       prompt('summarize the comment in a Haiku: ' || text) AS summary
FROM sample_data.hn.hacker_news limit 20
```

![query results](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_10_18_at_08_45_16_2f2e75f8c5.png&w=3840&q=75)

Note that we’re applying the prompt function to 100 rows and the processing time is about **2.8s**. We run up to 256 requests to the model provider concurrently which significantly speeds up the processing compared to calling the model in an unparallelized Python loop.

The runtime scales linearly from here - expect 10k rows to take between 5-10 minutes in processing time and to consume ~10 compute units. This might appear slow relative to other SQL functions, however looping over the same data in Python without concurrency would take about 5 hours instead.

### Use Case: Unstructured to Structured Data Conversion

The prompt() function can also generate structured outputs, using the `struct` and `struct_descr` parameters. This enables users to specify a struct of typed return values for the output, facilitating the integration of LLM-generated data into analytical workflows. The adherence to the provided struct schema is guaranteed - as we leverage [OpenAI’s structured model outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/) which use constrained decoding to constrain the model’s output to only valid tokens.

Below is an example that leverages this functionality to extract structured information, like topic, sentiment and a list of mentioned technologies from each comment in our sample of the hacker\_news table. The result is stored as `STRUCT` type, which makes it easy to access each individual field in SQL.

```sql
Copy code

SELECT by, text, timestamp,
prompt(text,
  struct:={topic: 'VARCHAR', sentiment: 'INTEGER', technologies: 'VARCHAR[]'},
  struct_descr:={topic: 'topic of the comment, single word',
                 sentiment: 'sentiment of the post on a scale from 1 (neg) to 5 (pos)',
                 technologies: 'technologies mentioned in the comment'}) as my_output
FROM hn.hacker_news
LIMIT 100
```

![query results](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_second_108fe97a0a.png&w=3840&q=75)

In this query, the `prompt` function is applied to the `text` column from the dataset without contextualizing it in a prompt. Instead, it uses the struct and struct\_descr parameter as follows:

- **`struct:={...}`**: Specifies the structure of the output, which includes:

  - `topic`: A string (VARCHAR) representing the main topic of the comment.
  - `sentiment`: An integer indicating the sentiment of the comment on a scale from 1 (negative) to 5 (positive).
  - `technologies`: An array of strings listing any technologies mentioned in the comment.
- **`struct_descr:={...}`**: While the model infers meaning from the struct field names above, struct\_descr can be used optionally to provide more detailed field descriptions and guide the model into the right direction.

The final result includes the comment's main topic, sentiment score (ranging from 1 to 5), and any mentioned technologies. The resulting column can subsequently be unfolded super easily into individual columns.

```sql
Copy code

SELECT by, text, timestamp, my_output.* FROM my_struct_hn_table
```

![query results](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_third_40993ce64a.png&w=3840&q=75)

For more advanced users that want to have full control over the JSON-Schema that is used to constrain the output, we provide the **json\_schema** parameter, which will result in JSON-typed results rather than STRUCT-typed results.

## Practical Considerations

Integrating LLMs with SQL using prompt() enables many possible use cases. However effective usage can require careful consideration of tradeoffs. Therefore we advise to test prompt-based use cases on small samples first.

Also cases like this should be considered: For extracting email addresses from a text, using [DuckDB’s regex\_extract](https://duckdb.org/docs/sql/functions/regular_expressions.html) method is faster, more cost-efficient, and more reliable than using an LLM or SLM.

We are actively involved in research on bridging the gap between the convenience of prompt-based data wrangling and the efficiency and reliability of SQL-based text operations, leveraging all the [amazing functionality](https://duckdb.org/docs/sql/functions/char) that DuckDB provides. If you want to learn more about this, take a look at our [SIGMOD publication](https://dl.acm.org/doi/10.1145/3650203.3663334) from June this year.

## Start Exploring Today

The **prompt()** function is now available in Preview for MotherDuck users on a Free Trial or the Standard Plan. To get started, check out our [documentation](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt/) to try it out.

Since running the **prompt()** function over a large table can incur higher compute costs than other analytical queries, we limit the usage to the following quotas by default:

- **Free Trial users:** 40 compute unit hrs per day (~ 40k prompts with gpt-4o-mini)
- **Standard Plan users:** Same as free trial, can be raised upon request

Please refer to our [Pricing Details Page](https://motherduck.com/docs/about-motherduck/billing/pricing/) for a full breakdown.

As you explore the possibilities, we invite you to share your experiences and feedback with us through our [Slack](https://join.slack.com/t/motherduckcommunity/shared_invite/zt-2hh1g7kec-Z9q8wLd_~alry9~VbMiVqA) channel. Let us know how you're utilizing this new functionality and [connect with us](mailto:quack@motherduck.com) to discuss your use cases.

Happy exploring!

### TABLE OF CONTENTS

[Prompt Function Overview](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/#prompt-function-overview)

[Practical Considerations](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/#practical-considerations)

[Start Exploring Today](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/#start-exploring-today)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Small Data is bigger (and hotter 🔥) than ever](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fblog_c71a983762.png&w=3840&q=75)](https://motherduck.com/blog/small-data-sf-recap/)

[2024/10/19 - Sheila Sitaram](https://motherduck.com/blog/small-data-sf-recap/)

### [Small Data is bigger (and hotter 🔥) than ever](https://motherduck.com/blog/small-data-sf-recap)

Catch up on the latest developments around simple, scalable workflows for Real data volumes from the first Small Data SF!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response