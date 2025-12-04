---
title: building-motherduck-partner-ecosystem
content_type: event
source_url: https://motherduck.com/blog/building-motherduck-partner-ecosystem
indexed_at: '2025-11-25T19:58:15.695852'
content_hash: 2f12adf55fb3d8f4
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Birds of a Feather MotherDuck Together

2023/07/06 - 4 min read

BY

[Tino Tereshko](https://motherduck.com/authors/tino-tereshko/)
,
[Nouras Haddad](https://motherduck.com/authors/nouras-haddad/)

## Building the MotherDuck Partner Ecosystem

At [MotherDuck](https://motherduck.com/), we are building a serverless data platform - one in which a plethora of user types collaborate on a multitude of use cases, all on securely shared data. Thus it’s simply imperative for MotherDuck users to be able to bring their own best-in-class tooling and use them with MotherDuck. Users win big when they can use their familiar choices of orchestration, integration, or visualization tool - and it allows them to start seeing value in our produck sooner.

Our combined experiences at Looker, Google BigQuery, and Firebolt told us that, as an upstart, getting third-party vendors to work with you can be challenging. Not only is it difficult to develop high-quality integrations; companies must bet that the effort will pay off and hence look for proof of immediate ROI. So as a pre-market company, we planned an optimistic goal of delivering a total of 5 partner integrations by the end of June 2023. Along the way, a funny thing happened and we ended up launching with [17 ecosystem partners](https://motherduck.com/#works-with)! How did that happen?

## Paddling in DuckDB’s wake

Naturally we love [DuckDB](https://duckdb.org/); it’s the most exciting analytics database in years! It’s fast, lightweight, highly portable, and free. DuckDB is rapidly growing in popularity, having recently eclipsed [ten thousand Github stars](https://star-history.com/#duckdb/duckdb&Date) and [one million Python downloads per month](https://pypistats.org/packages/duckdb). Perhaps most importantly, and rather uniquely, DuckDB enables developers to do with data what they naturally do with code - work locally on their laptops.

DuckDB buzz permeates the data industry: when we reached out to partners, folks routinely voiced that “they already have several DuckDB fans in their company”. Many actually already supported DuckDB, and [some](https://www.rilldata.com/blog/why-we-built-rill-with-duckdb) [even](https://learn.hex.tech/docs/explore-data/cells/sql-cells/sql-cells-introduction) [use](https://mode.com/blog/how-we-switched-in-memory-data-engine-to-duck-db-to-boost-visual-data-exploration-speed/) DuckDB in [their stack](https://www.exploreomni.com/blog/DuckDB-complements-BI) as a cache or a batch processing engine. Talk about paddling in DuckDB’s wake - partners are excited to work with us in large part thanks to the momentum of DuckDB.

## The magic of “.open md:”

DuckDB is incredible in its own right, and our primary goal at MotherDuck is to [supercharge](https://motherduck.com/docs/architecture-and-capabilities#summary-of-capabilities) **your** DuckDB with the power of cloud. So, with big help from the folks over at DuckDB Labs, we built an easy way for any DuckDB user to [connect to MotherDuck](https://motherduck.com/docs/key-tasks/authenticating-to-motherduck/#example-usage). You simply run `open md:`!

Some of the things you can do with MotherDuck are:

- [Share](https://motherduck.com/docs/key-tasks/sharing-data/sharing-overview/) your DuckDB databases with your friends and colleagues
- [Persist](https://motherduck.com/docs/key-tasks/loading-data-into-motherduck/) your data in the cloud
- [Query Amazon S3](https://motherduck.com/docs/key-tasks/cloud-storage/querying-s3-files/) easier, faster, and more securely
- Use “ [Hybrid Execution](https://motherduck.com/docs/architecture-and-capabilities#hybrid-execution)” to query data wherever it lives
- Use MotherDuck’s web UI to analyze your data

We asked partners who already supported DuckDB to try connecting to MotherDuck using `open md:`. Things. Just. Worked. With a single line of code (and an auth token), they were talking to the MotherDuck service!

## Expanding the duck pond

![The Modern Duck Stack Diagram](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmodern_duck_stack_diagram_v1_4_2db850000d.png&w=3840&q=75)

Here are some examples of the diverse things you can do with our ecosystem today:

### Data Integration and Transformation

- Load data from a variety of databases, file systems, SaaS services, and more into MotherDuck, using [CloudQuery](https://cloudquery.io/how-to-guides/moving-data-from-postgres-to-motherduck) or [Ascend](https://www.ascend.io/blog/ascending-with-motherduck/).
- Transform data in MotherDuck with [dbt Core](https://motherduck.com/blog/solving-advent-code-duckdb-dbt/).
- With [Census](https://www.getcensus.com/blog/census-motherduck-integration?utm=PkS6MYbxUa), sync customer data from MotherDuck to 160+ business tools and take action on it.
- Stream events into MotherDuck using [InfinyOn](https://www.prnewswire.com/news-releases/infinyon-and-motherduck-announce-strategic-partnership-to-drive-end-to-end-data-streaming-and-analytics-pipelines-301868236.html) / Fluvio.

### Business Intelligence, Data Science, and AI

- Analyze and visualize data using Tableau Desktop, [Omni](https://www.exploreomni.com/blog/announcing-support-for-motherduck), [Metabase](https://www.metabase.com/), [Rill](https://www.rilldata.com/), and [Preset](http://preset.io/) / Superset.
- Analyze your data using plain English with [LangChain](https://python.langchain.com/docs/integrations/providers/motherduck/) or [LlamaIndex](https://gpt-index.readthedocs.io/en/latest/examples/index_structs/struct_indices/duckdb_sql_query.html#basic-text-to-sql-with-our-nlsqltablequeryengine).
- With [Hex](https://hex.tech/product/integrations/motherduck), build interactive data apps using SQL or Python within a notebook.

### Orchestration

- Orchestrate data pipelines and workflows with [Dagster](https://dagster.io/blog/poor-mans-datalake-motherduck), [Astronomer](https://www.astronomer.io/blog/three-ways-to-use-airflow-with-motherduck-and-duckdb/), or Airflow.
- With [Bacalhau and Expanso](https://blog.bacalhau.org/p/expanso-and-motherduck-join-forces), deploy DuckDB everywhere and [query](https://www.youtube.com/watch?v=AHEn2ae07ME) data where it lives.

We also have a few consulting partners who can help you implement MotherDuck and DuckDB in your data stack. Please reach out to [DataRoots](https://dataroots.io/research/contributions/herding-the-flock-with-motherduck-your-next-data-warehouse), [Bytecode](http://bytecode.io/) and [Brooklyn Data](https://brooklyndata.co/).

## Quack into action

Whether you’re a potential user or partner, we’d love to hear from you:

- Join our [community Slack](https://slack.motherduck.com/), introduce yourself, and let us know if you need help!
- Request an invite for [MotherDuck Beta](https://motherduck.com/).
- Try MotherDuck with some of the third party tools and give us feedback.
- …and if you’re a partner and want to work with us, quack at us!

### TABLE OF CONTENTS

[Building the MotherDuck Partner Ecosystem](https://motherduck.com/blog/building-motherduck-partner-ecosystem/#building-the-motherduck-partner-ecosystem)

[Paddling in DuckDB’s wake](https://motherduck.com/blog/building-motherduck-partner-ecosystem/#paddling-in-duckdbs-wake)

[The magic of “.open md:”](https://motherduck.com/blog/building-motherduck-partner-ecosystem/#the-magic-of-open-md)

[Expanding the duck pond](https://motherduck.com/blog/building-motherduck-partner-ecosystem/#expanding-the-duck-pond)

[Quack into action](https://motherduck.com/blog/building-motherduck-partner-ecosystem/#quack-into-action)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Announcing MotherDuck: Hybrid Execution Scales DuckDB from your Laptop into the Cloud](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_blog_2b6d1d70a7.png&w=3840&q=75)](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/)

[2023/06/22 - MotherDuck team](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/)

### [Announcing MotherDuck: Hybrid Execution Scales DuckDB from your Laptop into the Cloud](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud)

Announcing MotherDuck: Hybrid Execution Scales DuckDB from your Laptop into the Cloud

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response