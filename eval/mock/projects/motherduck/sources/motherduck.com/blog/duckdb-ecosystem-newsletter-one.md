---
title: duckdb-ecosystem-newsletter-one
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-one
indexed_at: '2025-11-25T19:58:07.392866'
content_hash: 7a69c75ee015fb23
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem

2022/12/15 - 4 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Hey, friend 👋

Hi, I'm [Marcos](https://marcosortiz.carrd.co/)! I'm a data engineer by day at X-Team, working for Riot Games. By night, I create newsletters for a few topics I'm passionate about: helping folks [find data gigs](http://interestingdatagigs.substack.com/) and AWS graviton. After getting involved in the DuckDB community, I saw a great opportunity to partner with the MotherDuck team to share all the amazing things happening in the DuckDB ecosystem.

Marcos

_Feedback: [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)_

## Featured Community Members

### Mark Raasveldt

![Mark Raasveldt](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmark_raasveldt_35b11c739d.jpeg&w=3840&q=75)

If we're going to feature members of the community, it makes sense to start off with Mark as one of the [co-creators of DuckDB](https://mytherin.github.io/papers/2019-duckdbdemo.pdf). Mark is now the CTO and Co-Founder of DuckDB Labs as well as a Postdoc in the [Database Architectures](https://www.cwi.nl/en/groups/database-architectures/) group within CWI. Oh, and he's still the [top committer on DuckDB](https://github.com/Mytherin).

[Learn more about Mark](https://mytherin.github.io/)

### Alex Monahan

![Alex Monahan](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Falex_monahan_8ae7cef344.jpeg&w=3840&q=75)

If you've spent any time on [Twitter](https://twitter.com/__alexmonahan__) or on the [DuckDB Discord](https://discord.com/invite/tcvwpjfnZx), you likely already have seen one of Alex's many helpful responses to questions big and small. Alex is a force that keeps the community quacking. He's a data scientist at Intel, but also works on documentation, tutorials and training at DuckDB Labs.

[Learn more about Alex](https://www.linkedin.com/in/alex-monahan-64814292/)

## Top 10 DuckDB Links this Month

### 1\. DuckDB Video Series with Mark Needham

In this [video series](https://www.youtube.com/watch?v=fZj6kTwXN1U&list=PLw2SS5iImhEThtiGNPiNenOr2tVvLj6H7), Mark Needham does incredible work explaining in just 5 minutes how to do some common data engineering tasks with DuckDB like access parquet files in s3, how to diff parquet schemas, joining csv files on the fly, and how to use DuckDB to analyze the data quality of parquet files. Highly recommended series for anyone starting with DuckDB.

### 2\. Build a Poor Man's Data Lake from Scratch

In [this article](https://dagster.io/blog/duckdb-data-lake), [Pete Hunt](https://twitter.com/floydophone) and [Sandy Ryza](https://twitter.com/s_ryz) from Dagster built a data lake using:

- DuckDB for SQL transformations
- Dagster for orchestration
- Parquet files on AWS S3 for storage

This is a very interesting resource because it is explained the power of DuckDB with a real use case. If you prefer watching over reading, catch their [video on YouTube](https://www.youtube.com/watch?v=33sxkrt6eYk).

### 3\. Common Crawl on Laptop - Extracting Subset of Data

In [this article](https://avilpage.com/2022/11/common-crawl-laptop-extract-subset.html), [Chillar Anand](https://twitter.com/chillaranand) analyzed 250 GB of a very popular web crawl dataset locally using DuckDB. He demonstrates the DuckDB feature which allows you to query remote files [using HTTPFS](https://duckdb.org/docs/extensions/httpfs.html).

### 4\. Using Polars on results from DuckDB's Arrow interface in Rust

Rust is increasing in popularity these days, and [this article](https://vikramoberoi.com/using-polars-on-results-from-duckdbs-arrow-interface-in-rust/) from [Vikram Oberoi](https://twitter.com/voberoi) is a very interesting exploration of the topic of DuckDB + Rust.

### 5\. DuckDB: Getting Started for Beginners

"DuckDB is an in-process OLAP DBMS written in C++ blah blah blah, too complicated. Let’s start simple, shall we?." If you can see past the ads on [the blog](https://marclamberti.com/blog/duckdb-getting-started-for-beginners/), Mark Lambert did an amazing job explaining how to start with DuckDB from scratch.

### 6\. Query Dataset using DuckDB

Another [interesting tutorial](https://medium.com/geekculture/query-dataset-using-duckdb-4aa0842945c5) on how to use DuckDB, the DuckDB shell (WASM), and [Tad](https://www.tadviewer.com/) (tabular data viewer). The author, business analyst Sung Kim, has other interesting articles, including one on using [DuckDB with Jupyter Notebooks](https://medium.com/geekculture/sql-notebooks-for-data-analytics-a051f3693742).

### 7\. Tips to Design a Distributed Architecture for DuckDB \[Twitter thread\]

Ismael [provides great tips](https://twitter.com/ghalimi/status/1596482002877706241) on the topic of which runtime component to use: Lambdas, Fargates, or VMs.

### 8\. Observable Loves DuckDB

This [interactive notebook](https://observablehq.com/@observablehq/duckdb) demonstrates how to use the Observable DuckDB client, based on WASM.

### 9\. DuckDB Geo Extension

If you're interested in experimenting with geospatial data in DuckDB, you can use [this extension](https://github.com/handstuyennn/geo) which adds a new GEO type and functionality for basic GIS data analysis.

### 10\. SQL on Python, Part 1: The Simplicity of DuckDB

In [this tutorial](https://www.orchest.io/blog/sql-on-python-part-1-the-simplicity-of-duckdb), Juan Luis Cano explains how to get started with DuckDB in Python to analyze content from Reddit on climate change. He talks about interoperability between DuckDB and pandas DataFrames, Numpy arrays and more.

## DuckCon 2023 User Group

Although not until February 3rd, you should plan ahead if you want to join the DuckDB creators and contributors along with the MotherDuck team at this evening of talks, food and drinks. The event is in Brussels and collocated with FOSDEM.

[Learn more](https://duckdb.org/2022/11/25/duckcon.html)

## Subscribe

Find something interesting in this newsletter? Share with your friends and let them know they can [subscribe](https://motherduck.com/#stay-in-touch) to receive it via email.

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

[![Why Use DuckDB for Analytics?](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_for_analytics_1_c16a0acfc3.png&w=3840&q=75)](https://motherduck.com/blog/six-reasons-duckdb-slaps/)

[2022/11/11 - Tino Tereshko, Ryan Boyd](https://motherduck.com/blog/six-reasons-duckdb-slaps/)

### [Why Use DuckDB for Analytics?](https://motherduck.com/blog/six-reasons-duckdb-slaps)

Fast aggregations, excellent SQL support, runs anywhere, provides simplified data access: cloud and local, works with your tools and frameworks.

[![MotherDuck Raises $47.5 Million to Make Analytics Fun, Frictionless and Ducking Awesome](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fquacking-news.15fcb298.jpeg&w=3840&q=75)](https://motherduck.com/blog/announcing-series-seed-and-a/)

[2022/11/15 - MotherDuck team](https://motherduck.com/blog/announcing-series-seed-and-a/)

### [MotherDuck Raises $47.5 Million to Make Analytics Fun, Frictionless and Ducking Awesome](https://motherduck.com/blog/announcing-series-seed-and-a)

MotherDuck is a new serverless data warehouse and backend for data apps based on DuckDB. MotherDuck provides SQL analytics at scale.

[View all](https://motherduck.com/blog/)

Authorization Response