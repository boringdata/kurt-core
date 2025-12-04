---
title: duckdb-ecosystem-newsletter-january-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025
indexed_at: '2025-11-25T19:58:00.479248'
content_hash: 646fc913f415d9cb
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: January 2025

2025/01/10 - 7 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

Hello. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB delivered straight to your inbox. But first, I wish you a happy new year and the best start to 2025.

In this January issue, I gathered ten exciting links, ranging from PyIceberg and SQLite Catalog to 0$ data distribution and using AWS Lambda+DuckDB as a simplified pipeline. We also examine Arrow Flight and gRPC as a middle layer in front of DuckDB, LLM-driven dbt models, and much more. Please enjoy.If you have feedback, news, or any insights, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1726257025286.jpeg&w=3840&q=75)

### Julien Hurault

[Julien](https://www.linkedin.com/in/julienhuraultanalytics/), based in Geneva, is a experienced data engineering consultant specializing in the development of modern data platforms for organizations aiming to become AI-ready. He is no stranger to this newsletter, as we have previously featured several insightful DuckDB posts from his [blog](https://juhache.substack.com/). Notably, one of his articles has also been included in this edition. A big thank you to Julien for consistently contributing great technical content to the community!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [PyIceberg: Trying out the SQLite Catalog](https://medium.com/learning-the-computers/pyiceberg-trying-out-the-sqlite-catalog-d7ace2a4ca5f)

Tyler showcases a local catalog, loads the Star Wars dataset, creates an Iceberg table, populates it, and then queries it with the PyIceberg API. He uses both Ibis and PyIceberg. Nifty features include table operations like deleting rows and exploring snapshots using PyIceberg's API.

### [0$ Data Distribution](https://juhache.substack.com/p/0-data-distribution)

In this article, Julien explores the "0$ Data Distribution" using Apache Iceberg and DuckDB, leveraging Cloudflare R2 buckets as they don’t charge for egress (data going out, meaning access by users). He demonstrates how, once uploaded to R2, you can freely read the data with`ATTACH 'https://catalog.boringdata.io/catalog' as boringdata;```(if you want to do the same with Bluesky data, check: [How to Extract Analytics from Bluesky](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/)). Julien discusses the potential applications of this approach, such as direct data integration from services like Stripe, LinkedIn, and Notion, using a single command. With the key innovation where data providers pay for storage, and consumers pay only for compute.

### [Learning SQLFlow Using the Bluesky Firehose](https://www.linkedin.com/pulse/learning-sqlflow-using-bluesky-firehose-turbolytics-io4je/?trackingId=L%2FADasfEH6n1O6zQkFVtLA%3D%3D)

[SQLFlow](https://github.com/turbolytics/sql-flow) is a new stream processing engine powered by DuckDB. SQLFlow brings DuckDB to streaming data using a lightweight Python-powered service. SQLFlow executes SQL against streaming data, such as Kafka or webhooks. Think of SQLFlow as a way to run SQL against a continuous data stream. The data outputs can be shipped to sinks, such as Kafka. The article shows examples such as directly streaming data from Bluesky Firehose to Kafka, transforming streams, and writing to stdout. A key feature, SQLFlow, supports rolling window aggregations, which can reduce thousands of events into summarized time-based buckets (e.g., 5-minute windows), making it efficient for processing high-volume data streams.

### [AWS Lambda + DuckDB (and Delta Lake)](https://dataengineeringcentral.substack.com/p/aws-lambda-duckdb-and-delta-lake)

Daniel checks out DuckDB once more, this time with Lambda functions, and asks, "Is it the Ultimate Data Pipeline?". He uses CSV files from S3 into Delta Lake with minimal infrastructure complexity thanks to DuckDB. He sets up a Docker image, an AWS ECR repository, configures a Lambda function, and demonstrates how data can be processed in real-time when files are uploaded to an S3 bucket. The example uses hard drive test [data from Backblaze](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data#downloadingTheRawTestData) to showcase the pipeline's capabilities. All code is available on [GitHub](https://github.com/danielbeach/DuckDBwithAWSLambda).

### [Databases in 2024: A Year in Review](https://www.cs.cmu.edu/~pavlo/blog/2025/01/2024-databases-retrospective.html)

Andy reviews the whole year with all the various databases in mind. In his discussion of DuckDB, he notes that according to the [Fivetran article](https://www.fivetran.com/blog/how-do-people-use-snowflake-and-redshift), the median amount of data scanned by queries is only 100 MB—a volume that a single DuckDB instance can easily handle. Beyond this, Andy goes into the Redis and Elasticsearch license changes, examines the ongoing rivalry between Snowflake and Databricks, and shares fascinating backstories about Oracle's legendary creator, Larry Ellison.

### [Unlocking DuckDB from Anywhere: A Guide to Remote Access with Apache Arrow and Flight RPC (gRPC)](https://medium.com/@mikekenneth77/unlocking-duckdb-from-anywhere-a-guide-to-remote-access-with-apache-arrow-and-flight-rpc-grpc-de9335c7aaec)

Mike demonstrates remote access to DuckDB using Apache Arrow and [Flight RPC](https://arrow.apache.org/docs/format/Flight.html) (built on top of gRPC) and sharing it as a web app with Streamlit. The flight protocol acts as an intermediate layer between different clients and the DuckDB Server instead of directly accessing DuckDB. The code is shared on a [git repo](https://github.com/mikekenneth/duckdb_streamlit_arrow_flight).

### [Should You Ditch Spark for DuckDB or Polars?](https://milescole.dev/data-engineering/2024/12/12/Should-You-Ditch-Spark-DuckDB-Polars.html)

Miles investigates single-machine compute engines like DuckDB and Polars and compares them to Spark. He wants to determine which single compute engine is better based on his benchmark (testing at both 10GB and 100GB scales). His research reveals that Spark remains competitive, especially on larger scales. He tests beyond just performance, evaluating development cost, engine maturity, and compatibility. The takeaway seems not to abandon Spark completely but to strategically integrate these engines based on specific use cases. Polars and DuckDB for interactive queries, embedded database operation, and other specialized capabilities.

### [LLM-driven data pipelines with prompt() in MotherDuck and dbt](https://motherduck.com/blog/llm-data-pipelines-prompt-motherduck-dbt/)

The new prompt() function enables the transformation of unstructured data sitting in a data warehouse into structured data that can be easily analyzed. It applies LLM-based operations to each row in a dataset while automatically handling parallel model requests, batching, and data type conversions in the background. Adithya demonstrates this capability by transforming single customer product reviews into multiple extracted attributes using dbt and MotherDuck. This approach is particularly valuable for processing thousands of free text reviews with varying attributes—a task that would be difficult to automate without LLMs.

### [DuckDB Node Neo Client](https://duckdb.org/2024/12/18/duckdb-node-neo-client.html)

The new DuckDB Node client, Neo, provides a powerful and friendly way to use your favorite database. It is an API for using DuckDB in [Node.js](https://nodejs.org/). Replaces the [old callback-based Node.js API](https://duckdb.org/docs/api/nodejs/overview.html), offering native TypeScript support and intuitive methods for data handling. It allows developers to access column names and types easily and read data in column-major and row-major formats, making it more developer-friendly than its predecessor. While currently in alpha status, Neo's roadmap includes completing several features for the upcoming DuckDB 1.2 release.

### [owl: Web-based SQL query editor](https://github.com/owlapp-org/owl)

A simple, open-source, web-based SQL query editor for your files, databases (e.g. Postgres & DuckDB), and cloud storage data.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Webinar \| Shifting Left and Moving Forward with MotherDuck and Dagster](https://lp.dagster.io/deep-dive-shift-left-motherduck)

**14 January, Online - 9 AM PT**

Explore how MotherDuck and Dagster streamline data workflows, empower teams, and enable seamless transitions from local development to cloud analytics. Perfect for optimizing your processes and accelerating insights.

### [Compete for a $10,000 prize pool with the Airbyte + MotherDuck Hackathon!](https://airbyte.com/hackathon-airbytemotherduck)

**21 January, Online**

We're thrilled to announce our hackathon to bring together the power of Airbyte and MotherDuck to solve the needs of delivering modern data integration, AI, and analytics solutions.

### [Webinar \| Getting Started with MotherDuck](https://lu.ma/ap3g3ung)

**23 January, Online - 9AM PT**

​Looking to get started with MotherDuck and DuckDB? Join us for a live session to learn how MotherDuck makes analytics fun, frictionless, and ducking awesome!

### [Supercharge DuckDB with MotherDuck: Scale, Share, and Simplify Analytics](https://lu.ma/xjkc4bh9)

**31 January, Amsterdam NL - 9 AM CET**

Level up your DuckDB experience with a MotherDuck Workshop.

### [DuckCon \#6: Amsterdam](https://duckdb.org/2025/01/31/duckcon6.html)

**31 January, Amsterdam NL - 3 PM CET**

DuckCon #6, DuckDB's next user group meeting in Amsterdam, the Netherlands. The event will be in person + streamed online on the DuckDB YouTube channel. Talks will be announced in late October / early November.

### [Post-DuckCon Drinks: Quack & Cheers](https://lu.ma/b95qayhg)

**31 January, Amsterdam NL - 7:30 PM CET**

Join us for a relaxed and casual gathering with the data community, just a 10-minute walk from DuckCon!

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/#upcoming-events)

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

[![We made a fake duck game: compete to win!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffake_duck_game_thumb_064ec74176.png&w=3840&q=75)](https://motherduck.com/blog/fake-duck-game/)

[2024/12/20 - Mehdi Ouazza](https://motherduck.com/blog/fake-duck-game/)

### [We made a fake duck game: compete to win!](https://motherduck.com/blog/fake-duck-game)

Spot the fake (AI generated) duck to win!

[![What’s New: Streamlined User Management, Metadata, and UI Enhancements](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMother_Duck_Feature_Roundup_2_47f5d902c0.png&w=3840&q=75)](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/)

[2024/12/21 - Sheila Sitaram](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/)

### [What’s New: Streamlined User Management, Metadata, and UI Enhancements](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024)

December’s feature roundup is focused on improving the user experience on multiple fronts. Introducing the User Management REST API, the Table Summary, and a read-only MD\_INFORMATION\_SCHEMA for metadata.

[View all](https://motherduck.com/blog/)

Authorization Response