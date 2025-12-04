---
title: duckdb-ecosystem-newsletter-six
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-six
indexed_at: '2025-11-25T19:57:28.264223'
content_hash: f07b16b3183e723c
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: May 2023

2023/05/24 - 5 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Hey, friend 👋

It’s [Marcos](https://www.linkedin.com/in/mlortiz) again, aka “ _DuckDB News Reporter_” with another issue of “This Month in the DuckDB Ecosystem for May 2023.

This has been an exciting month for DuckDB and the whole ecosystem: [DuckDB 0.8.0 is out](https://duckdb.org/2023/05/17/announcing-duckdb-080.html), the project reaches [10k stars on GitHub](https://duckdb.org/2023/05/12/github-10k-stars.html) (well [10,200 stars](https://github.com/duckdb/duckdb/stargazers) at the time of writing this), DuckDB now has a [Spatial extension](https://duckdb.org/2023/04/28/spatial.html), a native [Swift API](https://duckdb.org/2023/04/21/swift.html) (this is huge) and more.

This simply proves that DuckDB is more alive than ever before, and its stratospheric adoption growth curve keeps looking like a hockey stick.

As always we share here, this is a two-way conversation: if you have any feedback on this newsletter, feel free to send us an email to [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)

-Marcos

## Featured Community Member

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdownload_f770703cad.jpeg%3Fupdated_at%3D2023-05-24T09%3A03%3A56.856Z&w=3840&q=75)

### Fenjin Wang

[Fenjin Wang](https://www.linkedin.com/in/wangfenjin/) is an experienced software engineer working as a tech lead at TikTok.
He’s the creator and maintainer of [duckdb-rs](https://github.com/wangfenjin/duckdb-rs), an ergonomic bindings to duckdb for Rust. With an interface similar to rusqlite, it aims to provide a seamless experience for Rust developers working with DuckDB.

Kudos to him and all the contributors for making DuckDB quacking Rust!

## Top DuckDB Links this Month

### [DuckDB 0.8.0 is out codename “Fulvigula”](https://duckdb.org/2023/05/17/announcing-duckdb-080.html)

This new release is pretty exciting because contains a lot of new cool and useful features like the [Pivot/Unpivot](https://github.com/duckdb/duckdb/pull/6387), improvements to [parallel data](https://github.com/duckdb/duckdb/pull/6977) [import/export](https://github.com/duckdb/duckdb/pull/7375), [time series joins](https://github.com/duckdb/duckdb/pull/6719), User-defined functions for Python, the [new Swift API](https://duckdb.org/2023/04/21/swift.html), and much more.

[![image2.jpg](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_840dff064a.jpg&w=3840&q=75)](https://duckdb.org/2023/05/17/announcing-duckdb-080.html)

### [DuckDB Internals (CMU Advanced Databases / Spring 2023)](https://www.youtube.com/watch?v=bZOvAKGkzpQ)

[Mark Raasveldt](https://twitter.com/mraasveldt) (CTO at DuckDB Labs) gave an eye-opening lecture about DuckDB. Topics? Why DuckDB uses Vectors, how the Query Execution works inside DuckDB, Table storage, WASM, pluggable catalog, pausable pipelines, etc. Definitely, a video you should check out.

### [Throwing 107 GB and 5 billion fake rows of order data at DuckDB and Athena](https://fet.dev/posts/throwing-lots-of-data-on-duckdb)

[Simon Pantzare](https://www.linkedin.com/in/simon-pantzare-0a491522/) dives deep in a technical post comparing data ordering in DuckDB and Amazon Athena.

### [Commercializing Open-source Projects by MotherDuck’s Jordan Tigani and DuckDB’s Hannes Mühleisen](https://www.madrona.com/motherduck-jordan-tigani-duckdbs-hannes-muhleisen-partnerships-commercializing-open-source-projects/)

An insightful conversation among [Jon Turow](https://twitter.com/jturow) (Partner at Madrona), [Jordan Tigani](https://twitter.com/jrdntgn) (CEO at MotherDuck), and [Hannes Mühleisen](https://twitter.com/hfmuehleisen) (one of the co-creators of DuckDB).

### [Scalable Data Science with Ponder on DuckDB](https://ponder.io/ponder-on-duckdb/)

[Bala Atur](https://www.linkedin.com/in/bala-atur-732875/) from Ponder shares how to make Data Science scalable with the help of Ponder and DuckDB. Ponder now transparently uses DuckDB as a backend for both pandas and Numpy operations, making them significantly faster.

### [DuckDB vs Polars for Data Engineering](https://www.confessionsofadataguy.com/duckdb-vs-polars-for-data-engineering/)

[Daniel Beach](https://www.linkedin.com/in/daniel-beach-6ab8b4132/) shares an exciting perspective about using DuckDB and Polars for Data Engineering in this post.

### [Why We Built Rill with DuckDB](https://www.rilldata.com/blog/why-we-built-rill-with-duckdb)

[Michael Driscoll](https://twitter.com/medriscoll) (CEO of Rill Data) explains why they rely on DuckDB to build Rill’s product in his own words, and why it is perfect for its use case.

### [Efficient DuckDB](https://hussainsultan.com/posts/efficient-duckdb/)

[Hussain Sultan](https://www.linkedin.com/in/hussainsultan/) writes about a data-backed deep dive into DuckDB using TPC-H Benchmarks. He uses the 0.7.1 version of DuckDB for these tests.

[![image6.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage6_b34602ea67.png&w=3840&q=75)](https://hussainsultan.com/posts/efficient-duckdb/)

### [How we evolved our query architecture with DuckDB](https://blog.count.co/how-we-evolved-our-query-architecture-with-duckdb/)

[Jason Cole](https://www.linkedin.com/in/jasmcole/) from Count explains why they selected DuckDB for its _browser-first query model_.

### [Discovering Chess Openings in Grandmasters’ Games using Python and DuckDB](https://medium.com/@octavianzarzu/discovering-chess-openings-in-grandmasters-games-using-python-and-duckdb-e564d503665e)

[Octavian Zarzu](https://www.linkedin.com/in/octavianz/) takes an interesting approach to analyze the top 10 openings in chess using Python and DuckDB.

### [Building a Streamlit app on a Lakehouse using Apache Iceberg & DuckDB](https://dipankar-tnt.medium.com/building-a-streamlit-app-on-a-lakehouse-using-apache-iceberg-duckdb-b7bb1752445e)

[Dipankar Mazumdar](https://www.linkedin.com/in/dipankar-mazumdar/) writes about how to use the combination of Streamlit, DuckDB, and Apache Iceberg to build a Lakehouse.

### [Ibis 5.1: Faster file reading with DuckDB, Arrow-Native Workflows for Snowflake, and more](https://voltrondata.com/resources/ibis-5-1-faster-file-reading-duckdb-arrow-native-workflows-snowflake)

[Kae Suarez](https://www.linkedin.com/in/kae-suarez/) and [Anja Boskovic](https://www.linkedin.com/in/anja-boskovic/) from Voltron Data discuss the great things coming to the 5.1 release of the Ibis Project, including faster file reading with DuckDB.

### [Automate Data Analysis With Kestra and DuckDB](https://kestra.io/blogs/2023-04-25-automate-data-analysis-with-kestra-and-duckdb)

[Martin-Pierre Roset](https://www.linkedin.com/in/martin-pierre-roset) explains how to use the power of DuckDB and [Kestra](https://github.com/kestra-io/kestra) (a declarative data orchestration platform) to make the automation of Data Analysis simpler.

[![image3.jpg](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage3_82ddd19970.jpg&w=3840&q=75)](https://kestra.io/blogs/2023-04-25-automate-data-analysis-with-kestra-and-duckdb)

### [Delta-RS and DuckDB — Read and Write Delta Without Spark](https://betterprogramming.pub/delta-rs-duckdb-read-and-write-delta-without-spark-c4d3db580b25)

[Alexander Volok](https://www.linkedin.com/in/alexandrvolok/) shares why you should consider a new approach to faster analytics using Delta-RS and DuckDB.

## Upcoming events

### DuckCon in San Francisco - 29th June

“DuckCon,” the DuckDB user group, will be held for the first time outside of Europe in [San Francisco Museum of Modern Art (SFMOMA)](https://www.sfmoma.org/), in the Phyllis Wattis Theater. In this edition, there will be talks from DuckDB creators [Hannes Mühleisen](https://hannes.muehleisen.org/) and [Mark Raasveldt](https://mytherin.github.io/) about the current state of DuckDB and future plans. It will also talks from data industry notables [Lloyd Tabb](https://twitter.com/lloydtabb) (of Looker and Malloy fame) and [Josh Wills](https://github.com/jwills) (creator of dbt-duckdb). The full agenda is available [here](https://duckdb.org/2023/04/28/duckcon3.html).

### MotherDuck Party in San Francisco - 29th June

Following DuckCon, MotherDuck will host a party celebrating ducks at 111 Minna (located very close to SFMOMA). DuckCon attendees are cordially invited to attend to eat, drink, listen to music and play games (skeeball!). MotherDuck’s Chief Duck Herder will also demo the latest work bringing DuckDB to the cloud.

[Register now](https://www.eventbrite.com/e/motherducking-party-after-duckcon-and-dataai-summit-san-francisco-tickets-586172165727) before they run out of space!

### Data + AI Summit - 28th and 29th June

DuckDB co-creator Hannes will be giving a [keynote](https://register.dataaisummit.com/flow/db/dais2023/sessioncatalog23/page/sessioncatalog?search=%22Hannes%20M%C3%BChleisen%22) at this 10-track data conference hosted by Databricks. Additionally, Ryan Boyd (co-founder at MotherDuck) will be delivering a technical session: [If A Duck Quacks In The Forest And Everyone Hears, Should You Care?](https://register.dataaisummit.com/flow/db/dais2023/sessioncatalog23/page/sessioncatalog?search=Boyd)

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-six/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-six/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-six/#top-duckdb-links-this-month)

[Upcoming events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-six/#upcoming-events)

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

[![The Simple Joys of Scaling Up](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsimple_joys_scaling_up_v2_efb09ad02e.png&w=3840&q=75)](https://motherduck.com/blog/the-simple-joys-of-scaling-up/)

[2023/05/11 - Jordan Tigani](https://motherduck.com/blog/the-simple-joys-of-scaling-up/)

### [The Simple Joys of Scaling Up](https://motherduck.com/blog/the-simple-joys-of-scaling-up)

Explores why scale-out became so dominant, whether those rationales still hold, and some joyful advantages of scale-up architecture.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response