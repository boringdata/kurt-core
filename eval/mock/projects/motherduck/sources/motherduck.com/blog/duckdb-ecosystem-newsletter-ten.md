---
title: duckdb-ecosystem-newsletter-ten
content_type: info
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-ten
indexed_at: '2025-11-25T19:57:57.217515'
content_hash: d880a6aac5b18fcf
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: September 2023

2023/09/30 - 5 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Hey, friend 👋

It’s [Marcos](https://www.linkedin.com/in/mlortiz) again, aka “ _DuckDB News Reporter_” with another issue of “This Month in the DuckDB Ecosystem for September 2023.

I'm super excited that [DuckDB 0.9 has been released](https://duckdb.org/2023/09/26/announcing-duckdb-090.html), with significant performance improvements already being discussed on Twitter, plus support for Azure storage and Iceberg files.

It has been a busy month for all, not only for the DuckDB ecosystem but for the MotherDuck team as well, especially after the great news of the [new funding round led by Felicis](https://www.felicis.com/insight/motherduck-series-b), and of course the [opening of the platform to anyone who wants to try it](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/). It’s time to play with magic here, with 0.9 support in MotherDuck coming in a week or two.

This proves once again our point: the “Quack Stack” is thriving and organizations of all sizes (from small start-ups to big enterprises) are more and more interested in it.

As always we share here, this is a two-way conversation: if you have any feedback on this newsletter, feel free to send us an email to [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

## Featured Community Member

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1552564965456_8fbdb887cf.jpeg%3Fupdated_at%3D2023-10-01T14%3A01%3A03.977Z&w=3840&q=75)

### Niels Claeys

[Niels Claeys](https://www.linkedin.com/in/nielsclaeys/) is a lead data engineer at [Data Minded](https://www.dataminded.com/). From an early age he was passionate about large scale distributed systems. He has over 6 years of experience building batch and streaming data pipelines using Spark, kafka and SQL. He recently contributed to the [dbt adapter for DuckDB](https://github.com/duckdb/dbt-duckdb) and made some noise with his blog post “ [Use dbt and Duckdb instead of Spark in data pipelines](https://medium.com/datamindedbe/use-dbt-and-duckdb-instead-of-spark-in-data-pipelines-9063a31ea2b5)”.

## Top DuckDB Links this Month

* * *

### [MotherDuck + dbt: Better Together](https://motherduck.com/blog/motherduck-duckdb-dbt/)

![dbtmd](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2023_09_29_at_16_50_28_0b0e137945.png%3Fupdated_at%3D2023-10-01T14%3A01%3A04.480Z&w=3840&q=75)

dbt has become an indispensable tool for Data Engineers these days. [Sung Wong Chung](https://www.linkedin.com/in/sungwonchung1/) shares a simple but valuable way to combine it with the power of DuckDB and MotherDuck.

### [Vector similarity search with duckdb](https://medium.com/etoai/vector-similarity-search-with-duckdb-44dec043532a)

If you want to combine the power of PostgreSQL extension ecosystem with DuckDB, this is a primary example. Great work [Chang She](https://twitter.com/changhiskhan).

### [Duckdb – A Fascinating Comprehensive Guide](https://dotcommagazine.com/2023/08/duckdb-a-fascinating-comprehensive-guide-3/)

It’s always great to see simple guides like this one to understand why you need to learn DuckDB. One of people’s favorite features of DuckDB: is the [vectorized query execution engine](https://duckdb.org/why_duckdb.html). Let’s use Torry’s words on this one:

_Another groundbreaking feature of DuckDB is its vectorized query execution engine. This engine processes data in batches, applying operations to multiple data points simultaneously, thus leveraging the inherent parallelism of modern CPUs. This vectorized approach leads to significant performance gains, making DuckDB well-suited for complex analytical workloads. Furthermore, DuckDB employs a hybrid execution model that seamlessly integrates row-based and column-based processing techniques, optimizing performance for various query types._

### [Sentiment Analyze 2 GB JSON Data with Duckdb and Rust](https://levelup.gitconnected.com/sentiment-analyze-2-gb-json-data-with-duckdb-and-rust-ea7342e8c32a)

I’m a Pythonista, but I’ve learned to love the speed of Rust. So, I wanted an example to show how to work with both projects at the same time: DuckDB and Rust, and [Wei Huang](https://jayhuang75.medium.com/) provides precisely that: doing sentiment analysis with it. BTW, if you want to keep exploring this combination, I encourage you to read this insightful post from [Florian Tieben](https://twitter.com/FTieben) called [“The Future of Data Engineering: DuckDB + Rust + Arrow”](https://medium.com/@ftiebe/the-future-of-data-engineering-duckdb-rust-arrow-9422f136d54a), and read the [docs](https://duckdb.org/docs/api/rust.html) [about it](https://docs.rs/duckdb/latest/duckdb/).

### [Performance Explorations of GeoParquet (and DuckDB)](https://cloudnativegeo.org/blog/2023/08/performance-explorations-of-geoparquet-and-duckdb/)

This is a very interesting benchmark conducted by Chris Holmes about how GeoParquet works with DuckDB. It’s always great to read about how DuckDB unlocks new use cases every single day.

### [DuckDB: The Indispensable Geospatial Tool You Didn't Know You Were Missing](https://cloudnativegeo.org/blog/2023/09/duckdb-the-indispensable-geospatial-tool-you-didnt-know-you-were-missing/)

If you want to read another perspective about why DuckDB is making waves today, you should read this post from Chris Holmes (again, yes, he is awesome), and why you should consider DuckDB if you will develop geospatial apps.

### [DuckDB + Dbt + great expectations = Awesome Data pipelines](https://pran-kohli-1990.medium.com/duckdb-dbt-great-expectations-awesome-data-pipelines-8b459ccd7afc)

Data quality is a topic in everybody’s mouth today in the Data Engineering world, and Great Expectations provides an Open Source Python-based powerful framework for it. And if you have DuckDB on one side and dbt on the other side, you could build incredibly simple and reliable data pipelines. This post gives you a quick overview of how to combine these tools.

### [DuckDB: Bringing analytical SQL directly to your Python shell](https://www.youtube.com/watch?v=dVzfNZN9NKI)

In this talk, Pedro Holanda presented DuckDB. DuckDB is a novel data management system that executes analytical SQL queries without requiring a server. DuckDB has a unique, in-depth integration with the existing PyData ecosystem. This integration allows DuckDB to query and output data from and to other Python libraries without copying it. This makes DuckDB an essential tool for the data scientist. In a live demo, we will showcase how DuckDB performs and integrates with the most used Python data-wrangling tool, Pandas.

### [Even Friendlier SQL with DuckDB](https://duckdb.org/2023/08/23/even-friendlier-sql.html)

The one and only [Alex Monahan](https://twitter.com/__AlexMonahan__) shared this insightful post about how to take advantage of the last innovation in the SQL language made by DuckDB. Believe me: you must read [the entire series](https://duckdb.org/2022/05/04/friendlier-sql.html).

### [Harlequin: The DuckDB IDE for the Terminal](https://harlequin.sh/)

![harlequin](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2023_09_29_at_17_00_06_1e069d022d.png%3Fupdated_at%3D2023-10-01T14%3A01%3A04.691Z&w=3840&q=75)

What is Harlequin? It’s a very cool project developed by [Ted Conbeer](https://www.linkedin.com/in/tedconbeer/).  As its name indicates, is an IDE for DuckDB in the console, with very interesting features like you can interact with the data catalog, it has a query editor, a result viewer, and even: it has support for MotherDuck in local or SaaS mode. Is not that cool? Try and let us know what you think!

## Upcoming events

### Coalesce by dbt labs 16-19th October 2023

[Coalesce by dbt labs](https://coalesce.getdbt.com/) is happening in multiple locations. MotherDuck will have a booth in the "activation hall" in San Diego. The MotherDuck team invites you to come say hi if you're around.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-ten/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-ten/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-ten/#top-duckdb-links-this-month)

[Upcoming events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-ten/#upcoming-events)

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

[![Duck and Roll: MotherDuck is Open for All With $100M in the Nest](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fseries_b_social_card_18b85cfa6f.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/)

[2023/09/20 - Ryan Boyd](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/)

### [Duck and Roll: MotherDuck is Open for All With $100M in the Nest](https://motherduck.com/blog/motherduck-open-for-all-with-series-b)

MotherDuck Now Open for All and closes Series B

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response