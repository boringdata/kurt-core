---
title: motherduck-data-warehouse
content_type: tutorial
source_url: https://motherduck.com/blog/motherduck-data-warehouse
indexed_at: '2025-11-25T19:58:35.819014'
content_hash: 48d20af5f4ebadc8
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# The Data Warehouse powered by DuckDB SQL

2024/11/01 - 4 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

## Introducktion

There are many reasons to use a data warehouse - but ultimately value comes out of solving business problems. Of course, this is non-trivial to do, because great analytical results are downstream of ingestion, transformation, analytical capabilities, and flexibility.

Thankfully, [DuckDB](https://www.duckdb.org/) offers a powerful language to solve business problems: good ole SQL. DuckDB by itself, being in-process, is not enough to bring this power to the Enterprise, so MotherDuck offers a cloud service to turn the local, in-process power of DuckDB into a Cloud Data Warehouse.

## Ingestion

There are [myriad tools available](https://mad.firstmark.com/) for replicating data from sources to targets. But each additional tool adds one more thing to manage, another set of primitives to learn. MotherDuck offers a [rich set of ingestion capabilities](https://motherduck.com/docs/key-tasks/loading-data-into-motherduck/), all in SQL.

It can natively ingest from CSV, Parquet, JSON, Iceberg, & Delta file formats. It can manage authentication to S3, GCS, Azure Blob Storage, and Cloudflare R2. And that's just the tip of the "Iceberg".

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFile_Formats_90dfed75b9.png&w=3840&q=75)

Of course, for sources that cannot be read directly from MotherDuck, we offer a diverse set of connectors for both Data Warehousing and Data Lake style ingestion.

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FEcosystem_cdeb50478d.png&w=3840&q=75)

## Transformation

Once data has been loaded into MotherDuck, [DuckDB SQL](https://duckdb.org/docs/sql/introduction.html) proves to be both incredibly performant and easy to use. It is easy to build fast [data transformations](https://en.wikipedia.org/wiki/Data_transformation_(computing)) with supported libraries from [dbt](https://getdbt.com/) & [sqlmesh](https://sqlmesh.com/). For scenarios where SQL is not enough, DuckDB offers native [Python Dataframe APIs](https://duckdb.org/docs/api/python/overview#dataframes) to allow even the most complex transformations to take place.

To learn more about transformation in the Duck Stack, watch the video of our talk at [dbt Coalesce 2024](https://coalesce.getdbt.com/) or take a look at a more [in-depth example in our blog](https://motherduck.com/blog/motherduck-dbt-pipelines/).

Coalesce 2024: Simplify your dbt data pipelines with serverless DuckDB - YouTube

[Photo image of dbt Labs](https://www.youtube.com/channel/UCVpBwKK-ecMEV75y1dYLE5w?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

dbt Labs

15.1K subscribers

[Coalesce 2024: Simplify your dbt data pipelines with serverless DuckDB](https://www.youtube.com/watch?v=oqwIHvSfOVQ)

dbt Labs

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

[Watch on](https://www.youtube.com/watch?v=oqwIHvSfOVQ&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 31:29

•Live

•

## Analysis

From an analytics perspective, MotherDuck offers a very nice set of SQL functions that handles everything from simple aggregations to classical Machine Learning algorithms, like [lin reg](https://duckdb.org/docs/sql/functions/aggregates.html#regr_intercepty-x) or [K-means](https://duckdbsnippets.com/snippets/182/kmeans-on-one-dimensional-data-with-recursive-cte). The MotherDuck AI team continues to extend in the LLM space with [Prompting](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt/), [Embedding](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/embedding/#embedding-function), and [similarity functions](https://duckdb.org/docs/sql/functions/array.html#array_cosine_similarityarray1-array2), again all in SQL, to make the deployment of AI in your data warehouse simple, fast and easy to maintain.

An example dashboard built with MotherDuck is shown here:

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdemo_dashboard_12_0ec579e713_ca2c7e9f00.gif&w=3840&q=75)

For further reading (with examples) around the advanced analytical capabilities of MotherDuck, check out the following posts:

- [LLM Prompts in SQL](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/)
- [Data App Generation](https://motherduck.com/blog/data-app-generator/)
- [Using Embeddings in SQL for semantic meaning lookup & RAG](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/)
- [Building a dashboard with a data pipeline end-to-end](https://motherduck.com/blog/duckdb-dashboard-e2e-data-engineering-project-part-3/)
- [Full Text Search in SQL](https://motherduck.com/blog/search-using-duckdb-part-3/)

## Flexibility

Many data teams are compartmentalized into three sets of roles: Business Users, Data Analysts & Scientists, and Data Engineers. The tools generally are made with these personas in mind. However, most complex business problems require working across multiple roles and thus multiple tools. Furthermore, the most valuable problems often require support from Software Engineers to close the gap on these problems. Thankfully, DuckDB SQL offers a toolkit that can be shared across these roles, and is [loved by software engineers too](https://duckdb.org/2024/10/04/duckdb-user-survey-analysis.html)! This type of flexibility means that collaboration is easier, and value can be delivered faster.

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_11_01_at_3_55_20_PM_15426bf168.png&w=3840&q=75)

In addition to powerful SQL, MotherDuck’s built in AI features, like [fix-up](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/sql-assistant/prompt-fixup/#fix-up-your-query), mean that business users can shift their work upstream and look a little bit more like analysts when writing SQL. We have also found that Data Scientists, who are more familiar with R or Python, find our AI assisted SQL helpful in translating their ideas And its developer focused tooling like [DuckDB-NSQL-7B](https://motherduck.com/blog/duckdb-text2sql-llm/) means that internal app developers can extend the power of LLMs to their users.

Lastly, when you really need fast analytics for users, MotherDuck offers a [WASM library](https://motherduck.com/docs/key-tasks/data-apps/wasm-client/) that includes DuckDB in the browser to build customer experiences that are not possible anywhere else.

## Summary

MotherDuck offers a unique take on Data Warehousing, powered by DuckDB. In addition to excellent integrations offered by its [ecosystem partners](https://motherduck.com/ecosystem/), MotherDuck contains native functionality for integration, transformation, and analysis that make it incredibly flexible for solving complex business problems. [Create your account](https://app.motherduck.com/?auth_flow=signup) and jump into the [getting started guide](https://motherduck.com/docs/getting-started/) today!

### TABLE OF CONTENTS

[Introducktion](https://motherduck.com/blog/motherduck-data-warehouse/#introducktion)

[Ingestion](https://motherduck.com/blog/motherduck-data-warehouse/#ingestion)

[Transformation](https://motherduck.com/blog/motherduck-data-warehouse/#transformation)

[Analysis](https://motherduck.com/blog/motherduck-data-warehouse/#analysis)

[Flexibility](https://motherduck.com/blog/motherduck-data-warehouse/#flexibility)

[Summary](https://motherduck.com/blog/motherduck-data-warehouse/#summary)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![pg_mooncake: Columnstore Tables with DuckDB Execution in Postgres](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpg_mooncake_a23d8f2192.png&w=3840&q=75)](https://motherduck.com/blog/pg-mooncake-columnstore/)

[2024/10/30 - Pranav Aurora](https://motherduck.com/blog/pg-mooncake-columnstore/)

### [pg\_mooncake: Columnstore Tables with DuckDB Execution in Postgres](https://motherduck.com/blog/pg-mooncake-columnstore)

New pg\_mooncake provides columnstore tables in Postgres to enable faster analytics

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response