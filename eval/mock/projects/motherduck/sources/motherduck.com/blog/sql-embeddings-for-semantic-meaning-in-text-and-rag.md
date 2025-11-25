---
title: sql-embeddings-for-semantic-meaning-in-text-and-rag
content_type: blog
source_url: https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag
indexed_at: '2025-11-25T19:58:46.769019'
content_hash: f6ebed4aca1f8762
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Introducing the embedding() function: Semantic search made easy with SQL!

2024/08/14 - 6 min read

BY

[Till Döhmen](https://motherduck.com/authors/till-d%C3%B6hmen/)

While vectors and vector databases are gaining adoption, they require time-consuming, upfront prep work to "bring your own embeddings" to the database. Embeddings are numeric representations of the semantic meaning between words. To operationalize embeddings, you usually need to call another API to translate your data into an opaque vector before you can even put it into a vector database.

Today, we're taking the first step to make it **_a lot easier_** to do [semantic search](https://motherduck.com/blog/search-using-duckdb-part-1/) and [Retrieval-Augmented Generation (RAG](https://motherduck.com/blog/search-using-duckdb-part-2/)) with your data in MotherDuck. We are excited to announce that the `embedding()` function is now available in Preview on MotherDuck.

In this blog, we’ll walk through an example of how to use this new function - it’s as easy as:

```sql
Copy code

SELECT embedding('Ducks are known for their distinctive quacking sound
and webbed feet, which make them excellent swimmers.');
```

By enabling the creation of embeddings with SQL, we open a new set of possibilities for simplifying how we build RAG applications. Using LLMs in your database is now possible without building extensive AI infrastructure to bring them in during any ETL process. You can even create embeddings in your dbt models!

Making it easier to do vector search follows MotherDuck and DuckDB’s philosophy and commitment to making databases easier to use. Finally, data engineers don’t need to leave the context of the database or familiar SQL to translate data into a vector to prep it for vector search.

## What are Text Embeddings?

Text embeddings are [a way of representing words in a numerical format](https://motherduck.com/blog/search-using-duckdb-part-1/) to capture their semantic meaning. These embeddings can be used for various applications, including similarity search, clustering, classification, and more. By converting text into a high-dimensional vector, embeddings allow you to perform complex NLP tasks with greater efficiency and accuracy.

## Semantic Search vs Full-Text Search (FTS)

Full text search scans the entire text for specific word matches. While this is computationally efficient and a great way to ensure that search terms actually appear in the result, FTS can only identify exact textual matches, which means it is unable to parse the semantic meaning of words.

On the other hand, semantic search based on Text Embeddings allows for more flexible search results where related concepts are recognized, even when the exact words used differ. For example, a search for “robots” may return a relatively high similarity score for the term “AI.”

In a previous blog post, we talked about how to [combine Full-Text Search with Semantic Search](https://motherduck.com/blog/search-using-duckdb-part-3/) to get the best of both worlds.

## Embedding Function Overview

The `embedding()` function is designed to work seamlessly within your existing SQL workflows. There is no need for external tools or libraries or setting up your own infrastructure: Simply use the function within your SQL queries to compute embeddings on the fly, and incorporate them into any ETL process, including your dbt models.

We use [OpenAI’s](https://openai.com/index/new-embedding-models-and-api-updates/)`text-embedding-3-small` model with 512 embedding dimensions because it provides the best value for performance, balancing high throughput with high quality embeddings, and are considering adding support for additional models in the future.

_Note: This model outperforms OpenAI’s previous ada v2 model on the [MTEB benchmark](https://huggingface.co/spaces/mteb/leaderboard) with scores of 62.3 versus 61.0._

## How to Use the Embedding Function

Using the `embedding()` function is straightforward. Let’s take a look at a simple example:

```sql
Copy code

SELECT embedding('Ducks are known for their distinctive quacking sound
and webbed feet, which make them excellent swimmers.') AS text_embedding;
```

The above query computes an embedding for the given text and returns the resulting vector. You can also use the function in more complex queries, such as filtering results based on embedding similarity.

_Note: Since the `embedding()` function is relatively compute intensive, using CTAS or UPDATE operations is recommended so that you do not need to recompute embeddings for every comparison operation._

```sql
Copy code

ALTER TABLE my_table ADD COLUMN my_embedding FLOAT[512];
UPDATE my_table SET my_embedding = embedding(my_text);
```

## Example Use Case

Let’s dive into an example using embeddings for similarity search, a common and powerful application of text embeddings.

In the following example, we're performing a similarity search to find movies which titles are most similar to a given piece of text, "artificial intelligence." This query uses embeddings to measure the similarity between given search terms and the movies' titles.

```sql
Copy code

SELECT title, overview, array_cosine_similarity(
    embedding('artificial intelligence'), title_embeddings) as similarity
FROM kaggle.movies
ORDER BY similarity DESC
LIMIT 3
```

### Here's a breakdown of what's happening in our query:

- **Embedding Generation**: The `kaggle.movies` sample dataset contains a `'title_embeddings'`column with embeddings of each movie title. This column was populated in advance, using the embedding function (see [example code](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/embedding/#example-compute-embeddings) in our docs). In order to find the most similar movies to our search terms `"`artificial intelligence`"`, we generate an embedding for it on the fly, using the `embedding("`artificial intelligence`")` expression.
- **Similarity Calculation**: Using the `array_cosine_similarity` function, we then compare our embedding to each movie’s `'title_embedding'`. Cosine similarity measures the cosine of the angle between two vectors (in this case, our embeddings), which effectively provides a measure of how similar the documents are in terms of their contents. Finally, we order the results by their cosine similarity and limit the output to the top 3 movies.
- **Results**: The query returns the top 3 movies with the highest similarity to the given search terms . In this case, the results might look something like:

  - **A.I. Artificial Intelligence** with a similarity score of approximately 0.80
  - **I, Robot** with a similarity score of approximately 0.46
  - **Almost Human** with a similarity score of approximately 0.45

This type of similarity search is a powerful tool for applications like recommendations, search engines, and retrieval-augmented generation (RAG) because it is able to capture semantic meaning. In a Full Text Search of our dataset, the movies “ **I, Robot**” and “ **Almost Human**” would not have appeared in the results at all due to their textual differences from our search terms.

## Start Building

The `embedding()` function is now available in Preview for MotherDuck users on a Free Trial or the Standard Plan. To get started, check out our [documentation](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/embedding/) to try it out.

Running the `embedding()` function over a large table may use large amounts of compute, which is why we have decided to set the following plan limits - refer to our [pricing page](https://motherduck.com/docs/about-motherduck/billing/pricing/) in the docs for a full breakdown:

- **Free Trial users:** Up to 25K embedding rows per day
- **Standard Plan users:** Up to 1M embedding rows per day _(though this can be raised upon request)_

We believe the `embedding()` function will be an enabler for many of our users by providing access to advanced NLP functionality directly within SQL.

Let us know how you’re using the `embedding()` function and share your success stories and feedback with us on [Slack](https://join.slack.com/t/motherduckcommunity/shared_invite/zt-2hh1g7kec-Z9q8wLd_~alry9~VbMiVqA). If you’d like to discuss your use case in more detail, please [connect with us](mailto:quack@motherduck.com) \- we’d love to learn more about what you’re building, and are curious to know which embedding models you’d like us to support in the future.

Happy querying!

### TABLE OF CONTENTS

[What are Text Embeddings?](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/#what-are-text-embeddings)

[Semantic Search vs Full-Text Search](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/#semantic-search-vs-full-text-search)

[Embedding Function Overview](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/#embedding-function-overview)

[How to Use the Embedding Function](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/#how-to-use-the-embedding-function)

[Example Use Case](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/#example-use-case)

[Start Building](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/#start-building)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Redshift Files: The Hunt for Big Data](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fredshift_files_6c29de1430.png&w=3840&q=75)](https://motherduck.com/blog/redshift-files-hunt-for-big-data/)

[2024/08/07 - Jordan Tigani](https://motherduck.com/blog/redshift-files-hunt-for-big-data/)

### [Redshift Files: The Hunt for Big Data](https://motherduck.com/blog/redshift-files-hunt-for-big-data)

Jordan Tigani revisits his popular Big Data is Dead blog post with analysis of the data from the Redshift TPC is Not Enough paper.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response