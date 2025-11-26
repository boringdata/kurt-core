---
title: duckdb-ecosystem-newsletter-two
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-two
indexed_at: '2025-11-25T19:58:03.665188'
content_hash: d606f7f5d77b3a26
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: January 2023

2023/01/12 - 4 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Happy new year, friend 👋

Hi, I'm [Marcos](https://marcosortiz.carrd.co/)! I'm a data engineer by day at X-Team, working for Riot Games. By night, I create newsletters for a few topics I'm passionate about: helping folks [find data gigs](http://interestingdatagigs.substack.com/) and AWS graviton. After getting involved in the DuckDB community, I saw a great opportunity to partner with the MotherDuck team to share all the amazing things happening in the DuckDB ecosystem.

In this first issue of the year 2023, we wanted to share some of the incredible stuff coming out of the global DuckDB community.

-Marcos
Feedback: [duckdbnews@motherduck.com](email:duckdbnews@motherduck.com)

## Featured Community Members

### Jacob Matson

![Jacob Matson](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fjacob_small_jpg_8e677b0787.jpg&w=3840&q=75)

Jacob is the writer of the [Modern Data Stack in a Box with DuckDB](https://duckdb.org/2022/10/12/modern-data-stack-in-a-box.html). A fast, free, and open-source [Modern Data Stack (MDS)](https://github.com/matsonj/nba-monte-carlo) can now be fully deployed on your laptop or to a single machine using the combination of DuckDB, Meltano, dbt, and Apache Superset.

He is working today as the VP of Finance & Operations at Simetric, bringing IoT connectivity data into a single pane-of-glass. He also does SMB analytics consulting via his agency, Elliot Point LLC.

You can find him on Twitter [@matsonj](http://www.twitter.com/matsonj)

[Learn more about Jacob](https://www.linkedin.com/in/jacobmatson/)

### Mark Needham

![Mark Needham](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmark_small_jpg_590959104d.jpg&w=3840&q=75)

Mark is a Developer Advocate at [StarTree](https://startree.ai/), talking about real-time analytics with Apache Pinot. If you are searching for content about DuckDB, it’s highly likely you have found his amazing [blog](https://www.markhneedham.com/blog/) and [YouTube channel](https://www.youtube.com/@learndatawithmark).

[Learn more about Mark](https://twitter.com/markhneedham)

## Top 10 DuckDB Links this Month

### 1\. DuckDB big milestone: 1 million downloads per month reached on PyPi

Prof Peter Boncz shared [this tweet](https://twitter.com/peterabcz/status/1610684170350596110), highlighting a chart with some incredible news: the duckdb Python package just reached 1M downloads per month in December 2022.

### 2\. Lightning fast aggregations by distributing DuckDB across AWS Lambda functions

In [this article](https://boilingdata.medium.com/lightning-fast-aggregations-by-distributing-duckdb-across-aws-lambda-functions-e4775931ab04?utm_campaign=DuckDB%20Ecosystem%20Newsletter&utm_source=hs_email&utm_medium=email&_hsenc=p2ANqtz-_AZXHJBw76R5fwm6b0OUHVORjz13kfD3zbQDlBlo1BMnaIWYGh_bSybZCbdLyJ5J-oYMkn), BoilingData’s team explained how to use the power of AWS Lambda as a distributed system in order to scale DuckDB querying operations using a serverless approach.

### 3\. DuckDB in Julia vs pure Julia DataFrames.jl

In this [very insightful post](https://bkamins.github.io/julialang/2022/12/23/duckdb.html), Bogumił Kamiński presented an interesting comparison between native Julia and DuckDB in Julia doing some common operations in exploratory data analysis: accessing data, writing data, performing JOINs, and doing basic computational statistics. Worth a read.

### 4\. A complete DuckDB tutorial for beginners

In this [video tutorial](https://www.youtube.com/watch?v=AjsB6lM2-zw) of just 26 minutes, Marc Lamberti (the Head of Customer Education at Astronomer) explains with great detail how to start working with DuckDB from scratch, how to do the most common operations with it (GROUP BY, DESCRIBE), data cleansing and more.

The video is coupled with a [Notion page](https://robust-dinosaur-2ef.notion.site/DuckDB-Tutorial-Getting-started-for-beginners-b80bf0de8d6142d6979e78e59ffbbefe) with the code from the tutorial.

### 5\. How to build a CDC pipeline with Redpanda that streams operational data from PostgreSQL to DuckDB

Need to load data from an operational database into a data lake for analytical workloads? The Redpanda team wrote this [insightful post](https://redpanda.com/blog/kafka-streaming-data-pipeline-from-postgres-to-duckdb) about how to build a CDC pipeline with Redpanda that streams operational data from PostgreSQL to DuckDB for OLAP analytics.

### 6\. DuckDB: Bringing analytical SQL directly to your Python shell

In this very [interesting technical talk](https://www.youtube.com/watch?v=2i2nyodhGkk) in the PyData Eindhoven 2023, [Pedro Holanda](https://www.linkedin.com/in/pedro-holanda-5447335a/) talks about how DuckDB is integrated with the rich Python ecosystem, the Pandas API, and more.

Pedro Holanda - DuckDB: Bringing analytical SQL directly to your Python shell - YouTube

[Photo image of PyData](https://www.youtube.com/channel/UCOjD18EJYcsBog4IozkF_7w?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

PyData

170K subscribers

[Pedro Holanda - DuckDB: Bringing analytical SQL directly to your Python shell](https://www.youtube.com/watch?v=2i2nyodhGkk)

PyData

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

[Watch on](https://www.youtube.com/watch?v=2i2nyodhGkk&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 29:31

•Live

•

He talks about 5 key characteristics of DuckDB:

- Vectorized Execution Engine
- End-to-end Query Optimization
- Automatic Parallelism
- Beyond Memory Execution
- and Data Compression

### 7\. Boost Your Cloud Data Applications with DuckDB and Iceberg API

Alon Agmon explained how to use the Apache Iceberg API with DuckDB to optimize analytics queries on massive Iceberg tables in your cloud storage.

### 8\. Learn Data with Mark: CSV to Parquet with Pandas, Polars, DuckDB

Another short but outstanding [video tutorial](https://www.youtube.com/watch?v=aexszHMKdy8) from the one and only Mark Needham where he talked about how to combine the power of Parquet files with Pandas, Polars and DuckDB. Or if you prefer the text version, you can [read the post](https://www.markhneedham.com/blog/2023/01/06/export-csv-parquet-pandas-polars-duckdb/) in Mark’s blog.

Our recommendation? You must [subscribe](https://www.youtube.com/@learndatawithmark?sub_confirmation=1) to Mark’s channel. You will find a lot of great gems there.

### 9\. lakeFS ❤️ DuckDB: Embedding an OLAP database in the lakeFS UI

Oz Katz (co-founder and CTO at Treeverse) [shared some insights](https://lakefs.io/blog/lakefs-duckdb-embedding-an-olap-database-in-the-lakefs-ui/) about how they embedded DuckDB inside the lakeFS UI.

### 10\. DuckDB vs. Porto Buses — A Small Case for a New OLAP Engine

Jose Cabeda [explains how to use DuckDB](https://betterprogramming.pub/duckdb-vs-porto-buses-a-small-case-for-a-new-olap-engine-1c04b898d293) for local analysis with only some knowledge of SQL.

## Upcoming Events

### Online

**[State Of Data 2023](https://www.eventbrite.com/e/state-of-data-2023-tickets-468776622497)** (January, 18th, 2023): Benjamin Rogojan aka Seattle Data Guy will answer some questions about the current state of Data Engineering. One of those questions: Is everyone switching to DuckDB?

### In-Person

**[Data Day Texas 2023](https://datadaytexas.com/2023/sessions)** (January, 28th, 2023): "Your laptop is faster than your data warehouse," by Ryan Boyd (MotherDuck co-founder). [20% discount available](http://www.eventbrite.com/e/444753408417/?discount=DUCKDB) to newsletter subscribers.

**[DuckCon at FOSDEM](https://duckdb.org/2022/11/25/duckcon.html)** (February 3, 2023): the DuckDB team has organized this second DuckCon – gathering in Brussels right before FOSDEM. Hear from the creators and contributors to DuckDB as well as the MotherDuck team. [Register on meetup](https://www.meetup.com/duckdb/events/289021740/).

![sticker-stop-quacking-transparent.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsticker_stop_quacking_transparent_22c497f543.png&w=3840&q=75)

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

[![This Month in the DuckDB Ecosystem](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFrame_8538_1_19a9e51746.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-one/)

[2022/12/15 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-one/)

### [This Month in the DuckDB Ecosystem](https://motherduck.com/blog/duckdb-ecosystem-newsletter-one)

DuckDB community member Marcos Ortiz shares his favorite links and upcoming events across the community. Includes featured community member Mark Raasveldt, DuckDB video series, data lakes with DuckDB, using Polars and Arrow in rust, SQL and more.

[![How We're Making Analytics Ducking Awesome](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFrame_8539_3c342bd81f.png&w=3840&q=75)](https://motherduck.com/blog/in-the-news-podcasts-conferences/)

[2023/01/02 - Ryan Boyd](https://motherduck.com/blog/in-the-news-podcasts-conferences/)

### [How We're Making Analytics Ducking Awesome](https://motherduck.com/blog/in-the-news-podcasts-conferences)

MotherDuck on Podcasts, in the News and at conferences.

[View all](https://motherduck.com/blog/)

Authorization Response