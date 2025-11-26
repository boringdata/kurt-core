---
title: duckdb-ecosystem-newsletter-three
content_type: event
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-three
indexed_at: '2025-11-25T19:58:53.842176'
content_hash: 027143009b475429
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: February 2023

2023/02/22 - 5 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Hey, friend 👋

Hi, I'm [Marcos](https://marcosortiz.carrd.co/)! I'm a data engineer by day at Riot Games (via X-Team). By night, I create newsletters for a few topics I'm passionate about: helping folks [find data digs](http://interestingdatagigs.substack.com/) and [AWS graviton](https://awsgravitonweekly.com/). After getting involved in the DuckDB community, I saw a great opportunity to partner with the MotherDuck team to share all the amazing things happening in the DuckDB ecosystem.

In this issue, we wanted to share the incredible talks from the DuckCon 2023, and many articles that were out in the second half of January and the first days of February. As each month goes by, a lot more great content is being published in the DuckDB ecosystem, so we've had to make some difficult choices for the featured community member and top links.

We hope you enjoy!

-Marcos

Feedback: [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)

Tweet great links to us with #DuckDBMonthly

## Featured Community Member

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2FImported%2520sitepage%2520images%2F37849236ea9ab2feb2d2ee71f30a9351f15765e83a9792bcd7f8677dfbc9c460.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3D37849236ea9ab2feb2d2ee71f30a9351f15765e83a9792bcd7f8677dfbc9c460.jpg&w=3840&q=75)

### Pedro Holanda

Pedro is a Post-Doc based in Amsterdam and a member of the Database Architecture group at CWI and currently as working as Chief of Operations at DuckDB Labs.

You can find him on Twitter [@holanda\_pe](https://twitter.com/holanda_pe)

[Learn more about Pedro](https://pdet.github.io/)

## New DuckDB Release: 0.7.0

The DuckDB team [recently announced DuckDB 0.7.0](https://duckdb.org/2023/02/13/announcing-duckdb-070.html)! This new release introduces JSON ingestion through read\_json, partitioned Parquet and CSV export, attaching multiple DuckDB databases in the same instance, SQLite storage backend, UPSERTs, LATERAL and POSITIONAL joins, improved Python APIs, better compression and more. The DuckDB community has clearly been heads down coding!

[Download and Install 0.7.0](https://duckdb.org/docs/installation/index)

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2FImported%2520sitepage%2520images%2Flabrador_duck.png%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dlabrador_duck.png&w=3840&q=75)

## Top 10 DuckDB Links this Month

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2FImported%2520sitepage%2520images%2Fmaxresdefault.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dmaxresdefault.jpg&w=3840&q=75)](https://www.youtube.com/playlist?list=PLIYcNkSjh-0wxBKPBuL6W1njhI31LwIRZ)

### [DuckCon Brussels 2023: Talks by DuckDB Creators, MotherDuck, LakeFS, Hopsworks, Fluvio](https://www.youtube.com/playlist?list=PLIYcNkSjh-0wxBKPBuL6W1njhI31LwIRZ)

DuckCon this year had an exciting mix of talks from the core DuckDB team and the community. Catch them all on the playlist above.

Want to learn how to build DuckDB Extensions? In their talk, Pedro and Sam teased the audience about the power of DuckDB Extensions and what you can achieve with them easily by cloning their example project.

### [DuckDB: Bringing Analytical SQL directly to your Python shell](https://www.youtube.com/watch?v=-rCZQHXSunc&list=PLIYcNkSjh-0ztvwoAp3GeW8HNSUSk_q3K&index=15)

In this talk at FOSDEM 2023, Pedro talks about how DuckDB fits perfectly inside the Python ecosystem and makes a cool demo at the end of the talk using DuckDB, Pandas, and PySpark.

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage10.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage10.jpg&w=3840&q=75)](https://www.youtube.com/watch?v=-rCZQHXSunc&list=PLIYcNkSjh-0ztvwoAp3GeW8HNSUSk_q3K&index=15)

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage3.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage3.jpg&w=3840&q=75)](https://www.youtube.com/watch?v=rYbSu9wvQmk)

### [PyIceberg 0.2.1: Iceberg ❤️ PyArrow & DuckDB](https://www.youtube.com/watch?v=rYbSu9wvQmk)

In this video, Tabular’s team demonstrated the new features of [PyIceberg 0.2.1](https://py.iceberg.apache.org/). If you prefer the article, here is the [complete write-up](https://tabular.medium.com/pyiceberg-0-2-1-pyarrow-and-duckdb-79effbd1077f) on Medium.

### [Solving Advent Of Code With DuckDB And dbt](https://motherduck.com/blog/solving-advent-code-duckdb-dbt/)

A very interesting article from [Graham Wetzler](https://www.linkedin.com/in/grahamwetzler/) about he used DuckDB and Python to solve some of the Advent of Code challenges.

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage7.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage7.jpg&w=3840&q=75)](https://motherduck.com/blog/solving-advent-code-duckdb-dbt/)

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage4.png%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage4.png&w=3840&q=75)](https://www.vantage.sh/blog/querying-aws-cost-data-duckdb)

### [Querying 1 Billion Rows of AWS Cost Data 100X Faster with DuckDB](https://www.vantage.sh/blog/querying-aws-cost-data-duckdb)

According to the Vantage’s team: from simple reads to complex writes and data ingestion they found that DuckDB was between 4X and 200X faster than Postgres for this use case.

### [Command Line Data Visualization with DuckDB and YouPlot](https://www.youtube.com/watch?v=lT6JwbeuzCA)

In this video, Mark Needham teaches us how to create data visualizations on the command line using YouPlot, DuckDB, and a bit of Pandas.

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage5.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage5.jpg&w=3840&q=75)](https://www.youtube.com/watch?v=lT6JwbeuzCA)

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage1.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage1.jpg&w=3840&q=75)](https://pedram.substack.com/p/streaming-data-pipelines-with-striim)

### [Streaming Data Pipelines with Striim + DuckDB](https://pedram.substack.com/p/streaming-data-pipelines-with-striim)

In this interesting article, Pedram Navid explains how to set up a streaming Data pipeline with the help of Striim (an enterprise-grade CDC platform) and DuckDB.

### [Python Faker for DuckDB Fake Data Generation](https://motherduck.com/blog/python-faker-duckdb-exploration/)

In this article, Ryan develops a simple way how to generate fake data with Python and upload it to DuckDB.

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage2.jpg%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage2.jpg&w=3840&q=75)](https://motherduck.com/blog/python-faker-duckdb-exploration/)

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhub%2F22616816%2Fhubfs%2Fimage11.png%3Fwidth%3D320%26upscale%3Dtrue%26name%3Dimage11.png&w=3840&q=75)](https://datastackshow.com/podcast/pragmatism-about-data-stacks-with-pedram-navid-of-west-marin-data/)

### [Pragmatism About Data Stacks with Pedram Navid of West Marin Data](https://datastackshow.com/podcast/pragmatism-about-data-stacks-with-pedram-navid-of-west-marin-data/)

The Data Stack Show, Eric and Kostas chat with Pedram Navid, Owner of West Marin Data and frequent contributor to substack. During the episode, Pedram discusses the modern data stack and its complexities, modern tooling, early-stage startups, and more.

### [DuckDB now supports ON CONFLICT clause on upserts](https://duckdb.org/docs/sql/statements/insert\#on-conflict-clause)

Now available in the latest 0.7.0 release. Thanks to Alex Monahan for the [tip on Twitter](https://twitter.com/__AlexMonahan__/status/1620435900235939841).

## Upcoming Events

[Data Council Austin](https://www.datacouncil.ai/austin) at the end of March will feature three days of technical talks on
analytics, data engineering, data science and AI. Nicholas Ursa, co-founder and software engineer at MotherDuck, will speak about how ["Data Warehouses are Gilded Cages. What Comes Next?"](https://www.datacouncil.ai/talks/data-warehouses-are-gilded-cages-what-comes-next?hsLang=en)

[QCon London](https://qconlondon.com/), also at the end of March, is a software development conference featuring some of the brightest minds across software. Hannes Mühleisen, co-creator of DuckDB, will present on ["In-Process Analytical Data Management with DuckDB."](https://qconlondon.com/presentation/mar2023/process-analytical-data-management-duckdb)

[Modern Data Stack Conference](https://www.moderndatastackconference.com/) (MDS Con) by Fivetran at the beginning of April in San Francisco will feature leaders in the industry such as DJ Patil, George Fraser, Tristan Handy, Ali Ghodsi, renowned analyst Sanjeev Mohan and Data Council founder Pete Soderling. Ryan Boyd, co-founder at MotherDuck, will be on a [panel](https://www.moderndatastackconference.com/agenda) with Gabi Steele (CEO, Preql) and Chetan Sharma (CEO, Eppo).

## Subscribe to the Newsletter

You can [subscribe to the blog using RSS](https://motherduck.com/rss.xml), or elect to [join our mailing list](https://motherduck.com/#stay-in-touch) for either the DuckDB Ecosystem Newsletter, MotherDuck News or both!

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

[![Python Faker for DuckDB Fake Data Generation](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpython_faker_duckdb_social_aa828ffa63.jpg&w=3840&q=75)](https://motherduck.com/blog/python-faker-duckdb-exploration/)

[2023/01/31 - Ryan Boyd](https://motherduck.com/blog/python-faker-duckdb-exploration/)

### [Python Faker for DuckDB Fake Data Generation](https://motherduck.com/blog/python-faker-duckdb-exploration)

Using the Python Faker library to generate data for exploring DuckDB

[![Solving Advent of Code with DuckDB and dbt](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fadvent_of_code_ae2c8c7684.jpeg&w=3840&q=75)](https://motherduck.com/blog/solving-advent-code-duckdb-dbt/)

[2023/02/09 - Graham Wetzler](https://motherduck.com/blog/solving-advent-code-duckdb-dbt/)

### [Solving Advent of Code with DuckDB and dbt](https://motherduck.com/blog/solving-advent-code-duckdb-dbt)

Tackling 10 days of AOC with DuckDB and dbt-duckdb, a DuckDB adapter for dbt

[View all](https://motherduck.com/blog/)

Authorization Response