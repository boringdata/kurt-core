---
title: duckdb-ecosystem-newsletter-july-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2024
indexed_at: '2025-11-25T19:58:11.857575'
content_hash: 70af1ff32e9f2185
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: July 2024

2024/07/01 - 10 min read

## Hey, friend 👋

Hello. I'm Simon, and I have the honor of writing this monthly newsletter and bringing the highlights and latest updates to your inbox. One line about me: I'm a data engineer and technical author of the [Data Engineering Blog](https://ssp.sh/), [DE Vault](https://vault.ssp.sh/), and a living book about [Data Engineering Design Patterns](https://www.dedp.online/). I'm a big fan of DuckDB and how MotherDuck simplifies distribution and adds features.

In this issue, you learn about integrating Warcraft Logs, utilizing native Delta Lake support, and embedding databases directly in web browsers. Discover practical guides on data testing, creating test data, using full-text and vector searches, and much more. Please enjoy 🙂.

If you have feedback, news, or any insight, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fgabor.jpeg&w=3840&q=75)

### Gábor Szárnyas

If I tell you he's the #1 contributor with over 2.5k commits on one of the most critical DuckDB repositories, can you guess what he does? Probably not, because he's the man behind the scenes maintaining the DuckDB documentation. [Gábor Szárnyas](https://www.linkedin.com/in/szarnyasg/) is a Developer Relations Advocate at DuckDB Labs. Besides his documentation responsibilities, you can catch him giving [talks](https://www.youtube.com/watch?v=q_SKaOeRiOI) at conferences, spreading the duck love.

Though he's been in DevRel for about a year, he's been part of the DuckDB Labs team longer, through his Postdoc at CWI.

Don't forget that the [DuckDB Documentation](https://duckdb.org/docs/) is [open-source](https://github.com/duckdb/duckdb-web). If you want to help out the DuckDB community without coding, contributing to the documentation is the best place to start!

Thank you, Gábor, for making our developer experience delightful with up-to-date documentation.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Personalizing Warcraft Logs and Building a Personal Project Stack](https://blog.devgenius.io/personalizing-warcraft-logs-and-building-a-personal-project-stack-e25e20e29a93)

Lior takes us on a ride with building his internal ranking system for my World of Warcraft based on his "personal project" stack, as he likes to call it, using DuckDB, Python, and dbt. The project extracts data from Warcraft Logs (GraphQL API), loads it into DuckDB, and transforms it into meaningful dimensions and facts. This is an excellent use-case as it's end-to-end, loading from an API, storing it, and processing data meaningfully for the presentation layer. He uses Streamlit to create visuals [hosted](https://sodwarcraftlogs.streamlit.app/) to be checked out and his [source code](https://github.com/LiorKaufman/sod_warcraft_logs_data_models).

### [Native Delta Lake Support in DuckDB](https://duckdb.org/2024/06/10/delta.html)

DuckDB now has native support for [Delta Lake](https://delta.io/), an open-source table format, with the Delta extension. If you haven't heard of [table formats](https://www.ssp.sh/brain/data-lake-table-format/) (Delta, Iceberg, Hudi), these allow **database-like features** on top of S3. With this announcement, DuckDB now supports two out of three major formats.

The article dives deep into how the implementation is done thoroughly by using an existing and powerful parquet reader and the **Delta Kernel** in Rust ( [delta-kernel-rs](https://github.com/delta-incubator/delta-kernel-rs)) instead of delta-rs, as delta-rs is essentially a fast parquet reader and DuckDB has its own excellent one, that supports a variety of filesystems and its credential management system.

Having native support for reading delta tables allows DuckDB to read simple files and every popular table format, in this case, delta lake. This allows for the building of first-class lakehouse architecture.

### [WASM: What Happens When You Put a Database in Your Browser?](https://motherduck.com/blog/olap-database-in-browser/)

Usually, databases are abstracted away and take longish roundtrips to 1. send the query, 2. fetch the data, and 3. send it back to the network. What if there's another way, directly in your application? This is where **WebAssembly**, an open standard that enables the execution of binary code, comes into play, and this blog is all about. As DuckDB is a single binary, we can now place the entire database and its data inside the browser. This eliminates any latency on the network or round trip. Plus, with DuckDB, we have super fast response times, especially for analytical data queries. Some potential use cases:

1. Ad-hoc queries on data lakes, such as schema exploration or previews.
2. Dynamic querying in dashboards by adjusting filters on the fly.
3. Educational tools for SQL learning or in-browser SQL IDEs.

Check the [source code](https://github.com/mehd-io/parquet-info-firefox-extension/tree/main), too, if this sparked your interest.

### [Hands-on dbt Testing with DuckDB](https://villoro.com/blog/dbt-testing-duckdb/)

Ensuring data quality and consistency of your data (and your SQL code) might be more critical than ever. Therefore, dbt tests are crucial and may become extensive due to that fact. In this article, Arnau showcases how you can implement these fast and lightweight with DuckDB. He runs through a step-by-step guide with plenty of example code so you can re-use that for your own needs. It covers setting up a SQL linter with Sqlfluff, automating testing with pre-commit hooks, and creating a streamlined continuous integration (CI) pipeline.

### [Generating Test Data is Hard](https://performancede.substack.com/p/generating-test-data-is-hard)

And another one related to testing. This time, it is not data quality but volume testing with automatically generating data to mimic the production workload before going into. It sounds easy, but it is a little. With the consistency of integers, GUIDs, floats, and dates in mind, it's much more challenging.

Matt shows how to generate test data of 12GB, written in about 12 seconds using DuckDB and SQL. Also, check out the [source code](https://github.com/mattmartin14/dream_machine/tree/main/substack/articles/test_data_part_1) for more details.

### [Full Text and Vector Embeddings-Based Text Search](https://motherduck.com/blog/search-using-duckdb-part-3/)

Search is a feature for most use cases we data engineers phase to make the curated and cleaned data discoverable for our end-users. But we have several options to search. For example, semantic understanding and similarities are crucial to ranking the documents in an **embedding-based search**.

However, there are situations where exact keyword matching is essential. Lexical searches like **Full Text Search** are very effective in achieving this.

Sometimes, when the text is long and contains many keywords, a hybrid of both is needed; this is what the article will explore, with a demo movie dataset and specifics such as Reciprocal Ranked Fusion and Convex Combination of the two standard metrics, their formulas, and their SQL implementation.

### [Using DuckDB for Embeddings and Vector Search](https://blog.brunk.io/posts/similarity-search-with-duckdb/)

This is another search-related blog where Sören explains why DuckDB is well suited for Embeddings and Vector Search. He explains that a vector representation of data like a text or an image is mapped into a vector space and that embeddings are a by-product of training neural networks because they are an internal representation of the data inside the mode.

In this example, he showcases how to store embeddings along with their documents in DuckDB, integrate with an embedding model running locally, and do vector searches with DuckDB in Python. He uses the HuggingFace Integration to query data with a single line: FROM 'hf://datasets/wikimedia/wikipedia/20231101⁠.de/\*.parquet'.

Then, he chooses the embedding model BGE-M3 due to its multi-lingual capabilities and the fact that it can produce dense and multi-vector term embeddings for late interaction, as popularized by ColBERT. Later, embeddings and the data will be stored directly in DuckDB, showcasing various possibilities for complex analysis and retrieval. He also plans to write a follow-up, so stay tuned.

### [DuckDB Isn’t Just Fast: Ergonomic Matters too.](https://csvbase.com/blog/6)

This article digs into the nuance of fast. Cal states that instead of "performance optimization" it should probably be called "performance satisfaction", and that  "usability improvements" should be called "optimizations". He is also exploring the usability benefits of DuckDB, which are hard to measure. Examples are good developer ergonomics, handling larger-than-memory ("out of core") datasets, and easy-to-install & run.

### [Load from Postgres to Postgres faster](https://dlthub.com/devel/examples/postgres_to_postgres)

This blog and [source code](https://github.com/dlt-hub/dlt/tree/devel/docs/examples/postgres_to_postgres) exemplify how DuckDB can speed up an otherwise slowish integration. The built-in dlt Postgres to Postgres didn’t sufficiently load on the initial load, as it operates a two-way step and persists insert\_statments on disk before it runs them on Postgres, potentially due to a lack of Apache Arrow support of Postgres.

Luckily, DuckDB helped speed up the normalization phase. Using the exported parquet files, DuckDB performed the normalization in-memory and immediately attached it to Postgres with the native Postgres extension without persisting anything in between, which was substantially faster.

Although this has been done by me, we still thought it would be beneficial to add it here :).

### [New Book: Getting Started with DuckDB](https://www.amazon.com/Getting-Started-DuckDB-practical-efficiently/dp/1803241004)

Co-written by [Simon Aubury](https://www.linkedin.com/in/simonaubury/) and [Ned Letcher](https://www.linkedin.com/in/nletcher/), this is a practical guide for accelerating your data science, data analytics, and data engineering workflows with DuckDB. It's tailored towards beginners. It contains practical use of DuckDB to handle efficiently, query, and transform data across various formats like CSV, JSON, and Parquet, utilizing the database's in-process, columnar, and analytical capabilities. Following hands-on examples in SQL, Python, and R, you learn to leverage DuckDB’s unique features, such as its extensions for geospatial analysis and text search, which can significantly optimize data workflows. Moreover, it provides insights into integrating DuckDB with other open-source tools and cloud services. It supercharges DuckDB-powered workflows and dedicated sections on modeling and extracting semi-structured data with Python and R.

### [Working With Tables When the Timestamps Don't Line Up](https://performancede.substack.com/p/working-with-tables-when-the-timestamps)

Matt showcases an order fulfillment system use case in this article with only four tables: Order Header, Order Detail, Order Event, and Order Exception Details. The system keeps track of order entries and their lifecycle as they travel through it. Theoretically, this is simple but harder, with exceptions like unreadable package labels or when a package falls off a conveyor.

Everything is implementing everything within the terminal and DuckDB. He built a so-called operational data store (ODS) that can deal with multiple entries for the same event. Matt shares what he learned from many of his days during his analytical work. Ultimately, he says **understanding the business process** has served him well over the years, which I highly agree with.

### [DuckDB Community extensions](https://github.com/duckdb/community-extensions)

In case you missed it with the latest Data & AI Summit announcements, DuckDB now has community extensions allowing you to easily extend your favorite database's capabilities. Once implemented, you can install and extension with:

INSTALL my\_extension FROM community;

LOAD my\_extension;

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [SciPy 2024: All the SQL a Pythonista needs to know](https://cfp.scipy.org/2024/talk/PNGX8L)

**9 July, Tacoma, WA, USA**

Learn how to use Structured Query Language (SQL) with DuckDB and your favorite Python tools. We’ll run SQL queries, learn how to share data, and teach it how to fly with Cloud providers like AWS and analytics data warehouses like MotherDuck!

**Location:** Tacoma, WA, USA 🇺🇸 - 8:00 AM America/Los\_Angeles

**Type:** In Person

### [Hack Night @ GitHub with MotherDuck, Weaviate, and Friends](https://lu.ma/x56sqs73)

**9 July, San Francisco, CA, USA**

​​Join us for an incredibly fun Hack Night at GitHub!

**Location:** San Francisco, CA, USA 🇺🇸 - 4:00 PM America/Los\_Angeles

**Type:** In Person

### [SciPy 2024: How to bootstrap a Data Warehouse with DuckDB](https://cfp.scipy.org/2024/talk/8NQY3N/)

**12 July, Tacoma, WA, USA**

Learn how to set up a Data Warehouse from scratch with DuckDB and other OSS tools. We’ll set up a data pipeline and a live data exploration dashboard, all running right on your laptop. Finally, we’ll also extend our workflows to the cloud with MotherDuck.

**Location:** Tacoma, WA, USA 🇺🇸 - 1:15 PM America/Los\_Angeles

**Type:** In Person

### [DuckCon \#5 in Seattle](https://duckdb.org/2024/08/15/duckcon5.html)

**15 August, Seattle, WA, USA**

DuckDB Labs is excited to hold the next “DuckCon” DuckDB user group meeting in Seattle, WA, sponsored by MotherDuck. The meeting will take place on August 15, 2024 (Thursday) in the SIFF Cinema Egyptian.

As is traditional in DuckCons, it will start with a talk from DuckDB’s creators [Hannes Mühleisen](https://hannes.muehleisen.org/) and [Mark Raasveldt](https://mytherin.github.io/) about the state of DuckDB. This will be followed by presentations by DuckDB users. In addition, they will have several lightning talks from the DuckDB community.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2024/#upcoming-events)

Subscribe to DuckDB Newsletter

E-mail

Subscribe to other MotherDuck news

Submit

Subscribe

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Pushing the Boundaries of Geo Data with MotherDuck and Geobase!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGeobase_1c7b4e233a.png&w=3840&q=75)](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/)

[2024/07/03 - Saqib Rasul](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/)

### [Pushing the Boundaries of Geo Data with MotherDuck and Geobase!](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase)

Learn how to integrate MotherDuck and Geobase to visualize and build applications that have never been possible before using spatial-temporal data.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response