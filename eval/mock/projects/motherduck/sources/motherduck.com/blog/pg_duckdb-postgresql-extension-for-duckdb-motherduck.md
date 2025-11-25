---
title: pg_duckdb-postgresql-extension-for-duckdb-motherduck
content_type: blog
source_url: https://motherduck.com/blog/pg_duckdb-postgresql-extension-for-duckdb-motherduck
indexed_at: '2025-11-25T19:58:17.903641'
content_hash: 99dc85b7b6645cb9
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Splicing Duck and Elephant DNA

2024/08/15 - 8 min read

BY

[Jordan Tigani](https://motherduck.com/authors/jordan-tigani/)
,
[Brett Griffin](https://motherduck.com/authors/brett-griffin/)

## Introducing the DuckDB + Postgres Extension

**You can have your analytics and transact them too**

We're excited to announce [pg\_duckdb](https://github.com/duckdb/pg_duckdb), an open-source Postgres extension that embeds DuckDB's analytics engine into Postgres for fast analytical queries in your favorite transactional database.

Postgres is generating a lot of excitement, having been named [2023 DBMS of the Year](https://db-engines.com/en/blog_post/106) by DB-Engines and recognized as the most popular database in the [2024 Stack Overflow Developer Survey](https://survey.stackoverflow.co/2024/technology#1-databases) twice in a row. It is popular for good reasons; it is a robust way to be able to create, update, and store data about your application.

Postgres is great at a lot of things, but if you try to use it for analytics, you hit a wall pretty quickly. That is, it is great at creating, finding and locating individual rows, but if you want to understand what is going on in a data set, it can be painfully slow. For example, you might want to know how revenue is growing in the Netherlands, or how many of your customers have names that rhyme with “Duck.” These are analytical queries and often require separate ways of storing and processing the data to operate efficiently.

People have tried to add Band-Aids to improve Postgres analytical performance. but they haven’t been particularly successful because being good at analytics requires different techniques for running your queries, like being able to operate over batches of rows at once, and avoiding decompressing data until it is absolutely needed. And typically, that takes a purpose-built analytical engine, which takes a ton of effort.

This is where DuckDB comes in. DuckDB is an in-process OLAP database and uses a vectorized query engine to process chunks (vectors) of data at a time. This makes it valuable for answering analytical questions about what is going on in the data. DuckDB’s popularity has been soaring due to its speed, ease of use, and versatility.

Postgres has a rich extension model that lets you do things like search over vector embeddings and handle geospatial data. DuckDB is an embedded database so you can build it into other software. What happens if you put those two together? Can you make a terrific transactional database that can also do awesome analytics?

Today, we’re announcing our collaboration on `pg_duckdb`, a Postgres extension that combines Postgres and DuckDB. It is fully open source, with a permissive MIT license. What’s more, the IP is owned by the DuckDB foundation, which will ensure that it stays open source. It is hosted in the official DuckDB GitHub [repository](https://github.com/duckdb/pg_duckdb).

## The challenges ahead

In order to really make a DuckDB Postgres extension that looks and feels just like Postgres, it is going to take a lot of work to get right. It is going to need significant DuckDB experience, since it will need improvements to DuckDB. In addition, it will also require a lot of Postgres knowledge to figure out how to weave DuckDB seamlessly into how Postgres executes queries.

In order to gather the right experts, we helped put together a consortium of companies, each of whom can provide unique skills to make the project successful:

- **DuckDB Labs** are the creators and stewards of DuckDB. They are signed up to make DuckDB changes needed to make DuckDB execution look just like Postgres.
- **MotherDuck** has a lot of experience running DuckDB, and so we are helping make DuckDB run well inside Postgres.
- **Hydra** originally kicked off the effort and has lent their know-how building Postgres extensions and storage. They are key drivers and contributors to the project.
- **Neon** has been building serverless managed Postgres and is lending experience about what will run well in production and how to make DuckDB work with Postgres Storage
- **Microsoft** has a ton of Postgres know-how including several Postgres committers and are also participating in the project.

> “A lot of developers use Postgres as a general purpose database and analytics is a major use case that Postgres didn't address well until now. This will be a big win for our users and generally for the Postgres ecosystem to support columnstore data and run analytics well. We are excited to add this extension to our platform and also contribute to this project." -- Nikita Shamgunov, CEO and founder of Neon DB

We recognize that we aren’t the first people with this idea; in fact, there have been several other folks who have built DuckDB as a Postgres extension. Crunchy Data has a commercial version. ParadeDB built `pg_analytics` which has similar functionality, but has a somewhat more restrictive license. But we realized that those projects, on their own, are going to struggle to be successful without commitment to do the internal engine work in DuckDB. By building in the open and making sure that DuckDB can operate seamlessly in a Postgres environment, we believe that we will be helping these projects as well.

## Why, you might ask, does MotherDuck care about Postgres?

**After all, isn’t MotherDuck a cloud hosted DuckDB?**

First, we are committed to a thriving DuckDB ecosystem. If DuckDB becomes ubiquitous, then that is good for everyone. We want to see DuckDB in as many different places and applications as possible. And Postgres has millions of users; if a healthy proportion of those people starts becoming familiar with DuckDB, that is a win for duck fans everywhere.

Second, our motto at MotherDuck is, “If you can Duck, you can MotherDuck.” Our aim is to ensure that anywhere you can run DuckDB, running MotherDuck is as simple as opening a database with the `md:` prefix. MotherDuck allows any DuckDB user to scale into the cloud, collaborate with colleagues, and reliably manage their data.

The `pg_duckdb` extension will be fully capable of querying against data stored in the cloud in MotherDuck as if it were local. MotherDuck’s “dual execution” capabilities let us join local Postgres data against MotherDuck data seamlessly, and we will figure out the best place to run the query. As a user, you don’t really need to care where the computation runs, we’ll just figure out how to make it run fast.

Moreover, it is common in analytics to want to offload your data from your transactional database into an analytical store. The `pg_duckdb` extension along with MotherDuck can help; you can just run a query in Postgres that pulls recent data from your Postgres database and write it to MotherDuck. You don’t need to export and reimport data, or set up CDC.

Finally, there are some downsides to running analytics on the same database that runs your application. Analytics can be resource hungry in terms of the amount of memory and CPU needed to make it run well. Above a certain size, folks may not want to run this on their production transactional database. MotherDuck will help offload this to the cloud, in a way that people don’t even have to change the queries that they’re running; they just get faster.

## Building in the Open

We’re announcing early, with the intention of building in the open with a public roadmap. The `pg_duckdb` extension is fully usable to query over data in a data lake, to run analytical queries over Postgres, and to store data in a local DuckDB database.

Today at [DuckCon 5](https://duckdb.org/2024/08/15/duckcon5.html), Joe Sciarrino from [Hydra](https://hydra.so/) showed off the extension and some of its capabilities, and Frances Perry from MotherDuck demonstrated `pg_duckdb` running queries combining Postgres and MotherDuck. If you didn’t make it to that event, you’ll be able to check out the videos once they’re posted.

Key features in the roadmap include:

- Seamless MotherDuck support to be able to access your MotherDuck data in the cloud and your Postgres data at the same time.
- Postgres native storage that will write data into Postgres storage pages and write-ahead log, which will let `pg_duckdb` to integrate with existing backup and replication.
- Full type compatibility with Postgres. Postgres already supports a lot of data types, our goal is to support them all.
- Full function compatibility with Postgres; any Postgres function that you run should also work in DuckDB.
- Seamless semantic compatibility. There are subtle differences between how any two database engines compute results, even ones that support the same SQL operations. Things like how to handle rounding or decimals of certain precision, or how to deal with semi-structured JSON object can vary between engines. So to ensure compatibility, we will need to make sure DuckDB can work just like Postgres.
- High quality, seamless lakehouse integration. DuckDB is already pretty good at querying from data lakes and has Iceberg and Delta lake support, but you should expect this functionality to get much better over time.

Check out the [repository](https://github.com/duckdb/pg_duckdb) today. We are excited to build this in the open and embrace contributions, feedback, and suggestions from everybody. As they say, “if you want to go far, go together.” We recognize that there are a lot of technical challenges ahead, and we welcome help and guidance on the project.

Also, please share your feedback with us on the MotherDuck [Slack](https://slack.motherduck.com/)! If you’d like to discuss your use case in more detail, please connect with us - we’d love to learn more about what you’re building.

### TABLE OF CONTENTS

[Introducing the DuckDB + Postgres Extension](https://motherduck.com/blog/pg_duckdb-postgresql-extension-for-duckdb-motherduck/#introducing-the-duckdb-postgres-extension)

[The challenges ahead](https://motherduck.com/blog/pg_duckdb-postgresql-extension-for-duckdb-motherduck/#the-challenges-ahead)

[Why, you might ask, does MotherDuck care about Postgres?](https://motherduck.com/blog/pg_duckdb-postgresql-extension-for-duckdb-motherduck/#why-you-might-ask-does-motherduck-care-about-postgres)

[Building in the Open](https://motherduck.com/blog/pg_duckdb-postgresql-extension-for-duckdb-motherduck/#building-in-the-open)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Introducing the embedding() function: Semantic search made easy with SQL!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fducking_simple_embeddings_1983d78fb8.png&w=3840&q=75)](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/)

[2024/08/14 - Till Döhmen](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/)

### [Introducing the embedding() function: Semantic search made easy with SQL!](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag)

Doing RAG for LLMs or making semantic search results pop? MotherDuck and DuckDB make it easy!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response