---
title: duckdb-ecosystem-newsletter-november-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025
indexed_at: '2025-11-25T19:57:17.884473'
content_hash: cf7145e62503ac18
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: November 2025

2025/11/12 - 9 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

I hope you're doing well. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this November issue, I compiled eight updates and news highlights (the usual 10 links) from DuckDB's ecosystem. This month, we've got updates including block-based caching for remote files, DuckLake's simplified lakehouse architecture, and powerful new extensions for DNS lookups and ML inference. In addition to a comprehensive analysis of the extension ecosystem, there is a fascinating experiment that stores an entire movie as relational data.

If you have feedback, news, or any insights, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fandreaskretz_4f53bd7eda.jpeg&w=3840&q=75)

### Andreas Kretz

**[Andreas Kretz](https://www.linkedin.com/in/andreas-kretz/)** is a data engineering educator and the founder of **Learn Data Engineering Academy**. Before transitioning to education, he spent over 10 years at Bosch as a Data Engineering and Data Labs Team Lead. He's the creator of **[The Data Engineering Cookbook](https://github.com/andkret/Cookbook)**, an open-source GitHub resource that has become a widely used reference for data platform architecture fundamentals.

Andreas just released **[DuckDB for Data Engineers: From Local to Cloud with MotherDuck](https://learndataengineering.com/p/duckdb-for-data-engineers-from-local-to-cloud-with-motherduck)**, a hands-on course teaching hybrid data workflows using DuckDB locally and MotherDuck in the cloud. The course covers everything from local setup to building production analytics with Duck Lake's lakehouse format.

Thanks, Andreas, for making data engineering education accessible and for bringing DuckDB and MotherDuck to your community!

You can find more of Andreas's work at **[andreaskretz.com](https://www.andreaskretz.com/)**.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [DuckDB QuackStore Extension](https://github.com/coginiti-dev/QuackStore)

**TL;DR**: The QuackStore DuckDB extension introduces block-based caching for remote files, enhancing performance for recurring data queries by localizing frequently accessed data.

The extension implements persistent, block-based caching (1MB blocks) with LRU eviction, meaning only actively used file segments are stored, making it highly efficient for large remote files. This approach supports automatic corruption detection, re-fetching corrupt blocks as needed. Setup involves installing the extension followed by `SET GLOBAL quackstore_cache_path = '/path/to/cache.bin';` and `SET GLOBAL quackstore_cache_enabled = true;`.

I could speed up reading 25 million rows over a mobile phone without cache `select count(*) FROM read_csv('https://noaa-ghcn-pds.s3.amazonaws.com/csv.gz/by_year/2025.csv.gz');` from **49.366** seconds to **3.304** seconds after the first cache with `select count(*) FROM read_csv('quackstore://https://noaa-ghcn-pds.s3.amazonaws.com/csv.gz/by_year/2025.csv.gz');`. Even the heavy command `SUMMARIZE` with the cached query took only **4.1** seconds without additional caching on the first try. I can imagine this being hugely powerful for apps that need fast query-responses. Remember: building cache is one of the hardest challenges out there, as it's constantly outdated and needs to foresee potential future queries.

📝 Striim implemented a similar solution with DuckDB as an OLAP Cache with PostgreSQL Extension as part of their streaming solution. Read more on [Beyond Materialized Views](https://medium.com/striim/beyond-materialized-views-using-duckdb-for-in-process-columnar-caching-98b8387b8568) by John Kutay.

### [duckdb-dns: DNS (Reverse) Lookup Extension for DuckDB](https://github.com/tobilg/duckdb-dns)

**TL;DR**: The DNS extension, a pure Rust implementation, integrates powerful DNS lookup and reverse DNS capabilities into DuckDB, featuring dynamic configuration for resolvers, caching, and concurrency.

You can simply run `SELECT dns_lookup('motherduck.com');` after installing the extension to get the IP. Tobias's extension leverages the DuckDB C Extension API to provide scalar functions like `dns_lookup()` and `dns_lookup_all()` for various record types (A, AAAA, CNAME, MX, TXT, etc.), alongside `reverse_dns_lookup()`. It includes DNS configs for switching DNS providers (e.g., 'google', 'cloudflare'), setting concurrency limits (default 50), and cache size and more. This extension offers efficient, in-database network data resolution.

Tobias, a very active community member, also created another extension called [**sql-workbench-embedded**](https://github.com/tobilg/sql-workbench-embedded) for embedding DuckDB queries directly as part of your website, such as HTML-based sites, or React or Vue applications. I tested it immediately as part of my static Hugo second brain, and it [works great](https://www.ssp.sh/brain/run-duckdb-in-your-website).

### [Why Python Developers Need DuckDB (And Not Just Another DataFrame Library)](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries/)

**TL;DR**: Explaining DuckDB's full database capabilities over standalone DataFrame libraries for Python developers.

Mehdi emphasizes the in-process nature and comprehensive database features, ensuring native ACID transactions, data integrity with automatic rollbacks, and robust persistence. And perhaps the biggest advantage, DuckDB's language agnosticism, which supports JavaScript (WebAssembly), Java, and Rust, enables consistent access across diverse environments. Its "friendly SQL" syntax (e.g., `SELECT * EXCLUDE (password, ssn)`) is another plus.

For Python users, zero-copy integration with Pandas and Polars through Apache Arrow allows querying Dataframes directly with SQL, facilitating incremental adoption. DuckDB provides an integrated solution, blending database power with DataFrame simplicity.

### [Infera: A DuckDB extension for in-database inference](https://github.com/CogitatorTech/infera)

**TL;DR**: Infera is a new DuckDB extension, developed in Rust, that integrates machine learning inference directly into SQL queries using ONNX models via the Tract inference engine.

This capability allows data practitioners to perform predictions without moving data out of the database, streamlining ML workflows. For example, after installing and loading the extension, models can be loaded using `select infera_load_model('model_name', 'model_url');` and predictions executed via `select infera_predict('model_name', ...);`.

Hassan notes that this approach adds ML inference as a first-class citizen in SQL, supporting both local and remote models, and handling single or multi-value outputs efficiently on table columns or raw tensor data. Check out the [short terminal video](https://asciinema.org/a/745806).

### [DuckDB Extensions Analysis](https://mjboothaus.github.io/duckdb-extensions-analysis/)

**TL;DR**: DuckDB's extension ecosystem is rapidly expanding, with 127 extensions providing diverse functionalities from core data format support to advanced community-driven integrations, which might be hard to keep up with.

To manage all extensions discussed in this newsletter too, this automated analysis report helps you stay up to date with the latest activities per extension and the most important properties. It's still work in progress, but the latest analysis reveals already the extension landscape, comprising 24 core and 103 community extensions, with significant recent activity (19 very active, 66 recently active). It's impressive to see the range of implementation languages, including C++, Rust, Python, and even Shell scripts, demonstrating a flexible and extensible architecture.

Michael, the creator, also shares a little more in his blog post about [Navigating DuckDB Extension Updates: Lessons from the Field](https://www.databooth.com.au/posts/duckdb-extensions-upgrade/). The code is available on [GitHub](https://github.com/Mjboothaus/duckdb-extensions-analysis).

### [DuckLake: Learning from Cloud Data Warehouses to Build a Robust “Lakehouse” (Jordan Tigani)](https://www.youtube.com/watch?v=z2GhznqtIz0&t=1s)

**TL;DR**: In this video, Jordan presented how DuckLake solves lakehouse challenges by storing metadata in a database rather than chained files, enabling ACID transactions while simplifying deployment. DuckLake is an open source implementation of an architectural pattern proven at scale inside both BigQuery and Snowflake.

Jordan discussed the convergent evolution of lakehouses toward cloud data warehouse architectures, arguing that "tables are a better interface than files" and "databases are a better place to store metadata than object stores." He contrasted Iceberg's multi-layered approach (REST catalog → metadata.json → manifest lists → manifest files) with DuckLake's direct SQL storage. File pruning becomes a simple query following a similar approach to BigQuery's internal Spanner queries.

For writes, DuckLake buffers small writes in catalog tables for immediate querying, avoiding Iceberg's tiny file problem. DuckLake is an open standard that can be implemented by other analytical engines. As one example, a minimal Spark connector requires just 34 lines (proof of concept).

### [Relational Charades: Turning Movies into Tables](https://duckdb.org/2025/10/27/movies-in-databases)

**TL;DR**: DuckDB can store and process video data by representing frames as relational tables.

In this experiment, Hannes explored turning the 1963 film "Charade" into a DuckDB table. The full movie, at 720x392 resolution, resulted in a table of 47 billion rows, stored in approximately 200 GB using DuckDB's native format and lightweight compression. The article shows two new features of DuckDB with its transformation leveraging [replacement scans](https://duckdb.org/docs/stable/clients/c/replacement_scans) to directly query NumPy arrays (for R, G, B components) and [`POSITIONAL JOIN`](https://duckdb.org/docs/stable/sql/query_syntax/from#positional-joins) for efficient bulk INSERT operations per frame. Hannes demonstrated that `SUMMARIZE` on this massive table completes in around 20 minutes on a MacBook, and a `DISTINCT r, g, b` query, benefiting from DuckDB's [larger-than-memory aggregate hash table](https://duckdb.org/2024/03/29/external-aggregation), finishes in about 2 minutes.

This illustrates DuckDB's capability to manage and analyze extremely large, non-traditional datasets efficiently on local hardware in an entertaining and unusual way 🙂.

### [Free Tutorial - Data Engineering with DuckDB & MotherDuck](https://www.udemy.com/course/data-engineering-with-duckdb-and-motherduck/)

**TL;DR**: The free course introduces data engineers and analysts to building versatile data workflows using DuckDB for local processing and MotherDuck for scalable cloud analytics, emphasizing hybrid execution and the new DuckLake format.

This course, by Andreas, gets you started with the fundamentals about DuckDB and MotherDuck. Andreas explains how to set up DuckDB locally, demonstrating querying CSV/Parquet files and building persistent databases via CLI or UI. The course then transitions to MotherDuck, detailing connection methods like `ATTACH` for cloud query execution and exploring performance differences between local and cloud compute for analytical queries.

Andreas shows how to scale by connecting Python to MotherDuck for remote execution, or the ability to combine local and cloud datasets in a single "dual execution" or "hybrid workflow" query. Find the course on [YouTube](https://www.youtube.com/watch?v=0uVJ2scvML0&list=PLYUMVUCNosJc3MJtgb7LOqPO85wXd9pxb&index=1) and follow the playlist, or go to [Udemy](https://www.udemy.com/course/data-engineering-with-duckdb-and-motherduck/). The code examples can be found on [GitHub](https://github.com/andkret/MotherDuck-DuckDB-Course).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Empowering Data Teams: Smarter AI Workflows with Hex + MotherDuck](https://luma.com/lwymnw2t?utm_source=newsletter)

**November 13 - Online : 9:00 AM PT**

​​AI isn’t here to take over data work, it’s here to make it better. Join Hex + Motherduck for a practical look at how modern data teams are designing AI workflows that prioritize context, iteration, and real-world impact.

### [Data-based: Going Beyond the Dataframe](https://luma.com/zdk664pd?utm_source=newsletter)

**November 20 - Online : 9:30 AM PT**

​​Learn how to go from local data exploration to scalable cloud analytics without changing your workflow. In this live demo, we’ll show how MotherDuck builds on DuckDB to give data scientists a fast, flexible, and Python-friendly way to analyze data—no infrastructure setup, no petabyte-scale headaches.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/#upcoming-events)

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

[![Faster Ducks](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Ffaster_ducks_2_f329150ba7.png&w=3840&q=75)](https://motherduck.com/blog/faster-ducks/)

[2025/10/28 - Jordan Tigani](https://motherduck.com/blog/faster-ducks/)

### [Faster Ducks](https://motherduck.com/blog/faster-ducks)

Benchmarks, efficiency, and how MotherDuck just got nearly 20% faster.

[![4 Senior Data Engineers Answer 10 Top Reddit Questions](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Foct_25_simon_blog_455f822c25.png&w=3840&q=75)](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions/)

[2025/10/30 - Simon Späti](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions/)

### [4 Senior Data Engineers Answer 10 Top Reddit Questions](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions)

A great panel answering the most voted/commented data questions on Reddit

[View all](https://motherduck.com/blog/)

Authorization Response